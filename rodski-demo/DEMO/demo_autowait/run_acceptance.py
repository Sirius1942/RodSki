#!/usr/bin/env python3
"""v11.7.0 自动等待（AutoWait）统一接管元素查找 —— rodski-demo 验收脚本。

设计文档: .pb/specs/v11.7.0-autowait-unified-design.md（§4.1 / §4.2）
基线记录: .pb/iterations/iteration-65/baseline.md

用法:
    python3 rodski-demo/DEMO/demo_autowait/run_acceptance.py            # 全部 W01~W30
    python3 rodski-demo/DEMO/demo_autowait/run_acceptance.py W11 W17    # 指定编号

覆盖三个模块:
    demo_autowait        AutoWait=5000（W01~W24）
    demo_autowait_zero   不设置 AutoWait = 不自动等待（W25~W27，v11.7.1）
    demo_autowait_long   AutoWait=12000（W28~W30）

脚本在 127.0.0.1:8767 以 demo_autowait/fun/site 为根目录启动静态站点（三个模块共用），
每一项都真实调用 `rodski run <用例文件> --case-id <ID> --headless --trace` 并断言：
  - 用例结果（负向用例带 expect_fail="是"，result.xml 中 PASS 表示"步骤确实失败了"）
  - 耗时窗口：取 **步骤级** 耗时，扣除浏览器启动与 navigate。
      result.xml 的 <step execution_time> 在 v11.6.0 为空，因此从 --trace 导出的 trace.json
      中读取该用例下对应关键字 span（keyword.type / keyword.get / keyword.clear ...）的起止时间。
      若 trace.json 缺失或找不到 span，才退回用例级 execution_time 并在输出中标注"(用例级)"，
      此时窗口判断不可信，按失败处理。
  - 负向用例的错误信息包含 "AutoWait=<ms>" 与元素名（来源：result.xml error_message +
    execution.log 的 [ERROR] 行 + 控制台失败行，见 Run.error_text）
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
MOD = HERE                                   # demo_autowait（AutoWait=5000）
ZERO = HERE.parent / "demo_autowait_zero"    # 不设置 AutoWait（= 0，不自动等待）
LONG = HERE.parent / "demo_autowait_long"    # AutoWait=12000
REPO = HERE.parent.parent.parent
SITE_PORT = 8767

# 负向默认窗口（spec §4.1）：失败耗时 ∈ [4.5, 7.5]s，不是 10s / 30s
NEG_WINDOW = (4.5, 7.5)
LONG_NEG_WINDOW = (11.5, 14.5)
ZERO_MAX = 1.5


# ---------------------------------------------------------------- 基础设施
class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401 - 静默访问日志
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def start_site() -> ThreadingHTTPServer:
    handler = partial(_QuietHandler, directory=str(MOD / "fun" / "site"))
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Run:
    def __init__(self, proc: subprocess.CompletedProcess, run_dir: Optional[Path], seconds: float):
        self.code = proc.returncode
        self.out = (proc.stdout or "") + (proc.stderr or "")
        self.run_dir = run_dir
        self.seconds = seconds

    def _root(self):
        p = self.run_dir / "result.xml" if self.run_dir else None
        return ET.parse(p).getroot() if p and p.is_file() else None

    def result(self, case_id: str) -> dict:
        root = self._root()
        if root is None:
            return {}
        for r in root.iter("result"):
            if r.get("case_id") == case_id:
                d = dict(r.attrib)
                d["_steps"] = [dict(s.attrib) for s in r.iter("step")]
                return d
        return {}

    def error_text(self, case_id: str) -> str:
        """该用例的失败信息。

        expect_fail 用例判 PASS 后，v11.6.0 的 result.xml 中 error_message 为空，失败原因只出现在
        execution.log 的 [ERROR] 行与控制台的失败行；因此取三者之和，但**只取 ERROR / 失败行**，
        不取整段日志（避免 [DEBUG] 行里的元素名造成误命中）。每次只跑一个 --case-id，不会混入其他用例。
        """
        r = self.result(case_id)
        parts = [r.get("error_message", "")] + [s.get("error_message", "") for s in r.get("_steps", [])]
        log = self.run_dir / "execution.log" if self.run_dir else None
        if log and log.is_file():
            parts += [ln for ln in log.read_text(encoding="utf-8", errors="ignore").splitlines() if "[ERROR]" in ln]
        parts += [ln for ln in self.out.splitlines() if "失败" in ln or "Error" in ln]
        return " | ".join(p for p in parts if p)

    def keyword_seconds(self, case_id: str, keyword: str) -> Optional[float]:
        """从 trace.json 读取该用例下第一个 keyword.<keyword> span 的耗时（秒）。"""
        p = self.run_dir / "trace.json" if self.run_dir else None
        if not p or not p.is_file():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        spans = [s for rs in data.get("trace", {}).get("resourceSpans", [])
                 for ss in rs.get("scopeSpans", []) for s in ss.get("spans", [])]

        def attr(s, k):
            for a in s.get("attributes", []):
                if a.get("key") == k:
                    return next(iter(a.get("value", {}).values()), None)
            return None

        case_span = next((s for s in spans if s.get("name") == "case" and attr(s, "case_id") == case_id), None)
        if not case_span:
            return None
        for s in spans:
            if s.get("parentSpanId") == case_span.get("spanId") and s.get("name") == f"keyword.{keyword}":
                return (int(s["endTimeUnixNano"]) - int(s["startTimeUnixNano"])) / 1e9
        return None

    def case_seconds(self, case_id: str) -> Optional[float]:
        try:
            return float(self.result(case_id).get("execution_time", ""))
        except ValueError:
            return None


def rodski_run(module: Path, case_file: str, case_id: str) -> Run:
    result_dir = module / "result"
    before = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    cmd = ["rodski", "run", case_file, "--case-id", case_id, "--headless", "--trace"]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=str(module), capture_output=True, text=True, timeout=600)
    seconds = time.monotonic() - t0
    after = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    new_dirs = sorted(p for p in after - before if p.is_dir())
    return Run(proc, new_dirs[-1] if new_dirs else None, seconds)


def expect(cond: bool, msg: str, ctx: str = "") -> None:
    if not cond:
        raise AssertionError(msg + (f"\n--- 上下文 ---\n{ctx[-2000:]}" if ctx else ""))


# ---------------------------------------------------------------- 检查项定义
@dataclass
class Check:
    title: str
    module: Path
    case_file: str
    case_id: str
    keyword: str                                   # 计时的关键字（trace span 名 keyword.<keyword>）
    negative: bool = False                         # True: expect_fail 用例，步骤必须真的失败
    window: Optional[Tuple[float, float]] = None   # 步骤耗时窗口 [lo, hi]（秒）
    auto_wait_ms: Optional[int] = None             # 负向：错误信息须含 AutoWait=<ms>
    element: str = ""                              # 负向：错误信息须含的元素名
    extra: Optional[Callable[[Run], None]] = None


def run_check(c: Check) -> str:
    """执行一项检查；所有断言都会评估，失败原因一次性全部列出（便于基线记录）。"""
    r = rodski_run(c.module, c.case_file, c.case_id)
    res = r.result(c.case_id)
    expect(r.run_dir is not None and res, f"未生成 {c.case_file}::{c.case_id} 的结果（rc={r.code}）", r.out)
    problems: List[str] = []
    status = res.get("status")
    if c.negative and status != "PASS":
        problems.append(f"[结果] 负向用例应判定 PASS（expect_fail：步骤确实失败），实际 {status}："
                        f"步骤被判成功（等到了 / 降级成功 / 静默返回）")
    if not c.negative and status != "PASS":
        problems.append(f"[结果] 正向用例应通过，实际 {status}: {r.error_text(c.case_id)[:300]}")

    secs = r.keyword_seconds(c.case_id, c.keyword)
    src = "步骤级"
    if secs is None:
        secs, src = r.case_seconds(c.case_id), "用例级"
    note = f"{c.keyword} {src}耗时 {secs:.2f}s" if secs is not None else f"{c.keyword} 耗时未知"
    if c.window:
        lo, hi = c.window
        if src != "步骤级" or secs is None:
            problems.append(f"[耗时] 无法从 trace.json 取得步骤级耗时（{note}），窗口不可判定")
        elif not lo <= secs <= hi:
            problems.append(f"[耗时] {note} 不在窗口 [{lo}, {hi}]s 内")

    if c.negative and c.auto_wait_ms is not None:
        err = r.error_text(c.case_id)
        token = f"AutoWait={c.auto_wait_ms}"
        if token not in err:
            problems.append(f"[错误信息] 应包含 '{token}ms'")
        if c.element not in err:
            problems.append(f"[错误信息] 应包含元素名 '{c.element}'")
        if token not in err or c.element not in err:
            problems.append(f"           实际: {err[:300] or '(无失败信息)'}")
    if c.extra:
        try:
            c.extra(r)
        except AssertionError as e:
            problems.append(f"[附加] {e}")
    if problems:
        raise AssertionError(f"{note}\n     " + "\n     ".join(problems))
    return note


def _no_wait_in_cases(r: Run) -> None:
    for f in (MOD / "case").rglob("*.xml"):
        expect('action="wait"' not in f.read_text(encoding="utf-8"), f"{f.name} 不应包含 wait 步骤")


P = "positive/"
N = "negative/"
# 正向：d=2000 的元素，步骤耗时上限 4.5s（≈ d + 余量；命中即走，不应等满 AutoWait）
POS_WIN = (0.0, 4.5)

CHECKS: Dict[str, Check] = {
    # ---------------- 正向（demo_autowait，AutoWait=5000）
    "W01": Check("输入框 2s 后插入：type 输入 → verify 回显", MOD, f"case/{P}late_elements.xml", "TC001", "type",
                 window=POS_WIN, extra=_no_wait_in_cases),
    "W02": Check("按钮 2s 后插入：click → 计数=1（只点一次）", MOD, f"case/{P}late_elements.xml", "TC002", "type",
                 window=POS_WIN),
    "W03": Check("disabled 2s 后 enabled：click → 已提交", MOD, f"case/{P}late_elements.xml", "TC003", "type",
                 window=POS_WIN),
    "W04": Check("遮罩 2s 后移除：click 真实命中按钮（遮罩拦截=0）", MOD, f"case/{P}late_elements.xml", "TC004", "type",
                 window=POS_WIN),
    "W05": Check("按钮 display:none 2s 后显示：click", MOD, f"case/{P}late_elements.xml", "TC005", "type",
                 window=POS_WIN),
    "W06": Check("select 选项 2s 后异步填充：select【华东】", MOD, f"case/{P}late_elements.xml", "TC006", "type",
                 window=POS_WIN),
    "W07": Check("悬停目标 2s 后出现：hover → 菜单已展开", MOD, f"case/{P}late_elements.xml", "TC007", "type",
                 window=POS_WIN),
    "W08": Check("双击目标 2s 后出现：double_click", MOD, f"case/{P}late_elements.xml", "TC008", "type",
                 window=POS_WIN),
    "W09": Check("右键目标 2s 后出现：right_click", MOD, f"case/{P}late_elements.xml", "TC009", "type",
                 window=POS_WIN),
    "W10": Check("iframe 2s 后插入：frame 定位 type → verify", MOD, f"case/{P}late_elements.xml", "TC010", "type",
                 window=POS_WIN),
    # 3 个字段各等 3s：总 >9s 证明串行逐字段；若整个 type 步骤共享一个 5s 预算则会失败
    "W11": Check("chain_form 一行 type A/B/C：逐字段独立计时（总 >7s 仍通过）", MOD, f"case/{P}chain_form.xml",
                 # 下限 7.0s 而非 9.0s：A 的 3s 计时从页面加载开始，与 navigate 重叠（约 1~1.5s），
                 # 步骤级计时从 type 开始；B、C 各在上一动作后 3s 出现，故 type 步骤 ≥ 6s + A 剩余。
                 # 7.0s 已明显大于单个 AutoWait(5s)，足以证明逐字段独立计时。
                 "TC001", "type", window=(7.0, 13.5)),
    # 共享预算：耗时 ≈ d(2s)，不是 AutoWait + d（≥7s）
    "W12": Check("多定位器：第 1 个永不命中、第 2 个 2s 后命中，耗时 ≈ d", MOD, f"case/{P}multi_locator.xml",
                 "TC001", "type", window=(1.5, 4.0)),
    "W13": Check("get 读取 2s 后出现的文本 → verify ${Return[-1]} 比对", MOD, f"case/{P}read_keywords.xml",
                 "TC001", "get", window=POS_WIN),
    "W14": Check("clear 2s 后出现的预填输入框 → verify 空", MOD, f"case/{P}read_keywords.xml", "TC002", "clear",
                 window=POS_WIN),
    "W15": Check("upload_file 到 2s 后出现的 file input → verify 文件名", MOD, f"case/{P}read_keywords.xml",
                 "TC003", "upload_file", window=POS_WIN),
    # G4：10 字段全部就绪，type 步骤不应产生任何等待
    "W16": Check("ready.html 10 字段 type 无额外等待（G4）", MOD, f"case/{P}ready.xml", "TC001", "type",
                 window=(0.0, 2.5)),
    # ---------------- 负向（demo_autowait，AutoWait=5000）
    "W17": Check("按钮 20s 才出现：click 在 ≈5s 失败", MOD, f"case/{N}late_20s.xml", "TC001", "type",
                 negative=True, window=NEG_WINDOW, auto_wait_ms=5000, element="submitBtn"),
    "W18": Check("输入框 20s 才出现：输入在 ≈5s 失败", MOD, f"case/{N}late_20s.xml", "TC002", "type",
                 negative=True, window=NEG_WINDOW, auto_wait_ms=5000, element="nameInput"),
    "W19": Check("select 20s 才出现：select 在 ≈5s 失败", MOD, f"case/{N}late_20s.xml", "TC003", "type",
                 negative=True, window=NEG_WINDOW, auto_wait_ms=5000, element="regionSelect"),
    "W20": Check("悬停目标 20s 才出现：hover 在 ≈5s 失败", MOD, f"case/{N}late_20s.xml", "TC004", "type",
                 negative=True, window=NEG_WINDOW, auto_wait_ms=5000, element="menuTrigger"),
    "W21": Check("文本 20s 才出现：get 在 ≈5s 失败（不再静默 None）", MOD, f"case/{N}late_20s.xml", "TC005", "get",
                 negative=True, window=NEG_WINDOW, auto_wait_ms=5000, element="lateValue"),
    "W22": Check("输入框 20s 才出现：clear 在 ≈5s 失败", MOD, f"case/{N}late_20s.xml", "TC006", "clear",
                 negative=True, window=NEG_WINDOW, auto_wait_ms=5000, element="#prefilled"),
    "W23": Check("遮罩永不移除：click 必须失败（无 force/JS 降级）", MOD, f"case/{N}overlay_never.xml", "TC001", "type",
                 negative=True, window=NEG_WINDOW, auto_wait_ms=5000, element="coveredBtn"),
    "W24": Check("多定位器全不命中：失败耗时 ≈ 1 × AutoWait", MOD, f"case/{N}multi_locator_miss.xml", "TC001", "type",
                 negative=True, window=NEG_WINDOW, auto_wait_ms=5000, element="ghostBtn"),
    # ---------------- 边界：不设置 AutoWait = 不自动等待（报错里显示 AutoWait=0ms）
    "W25": Check("未设置 AutoWait：1.5s 后出现的按钮 click 立即失败（<1.5s）", ZERO, "case/autowait_zero.xml", "TC001", "type",
                 negative=True, window=(0.0, ZERO_MAX), auto_wait_ms=0, element="submitBtn"),
    "W26": Check("未设置 AutoWait：1.5s 后出现的输入框立即失败（<1.5s）", ZERO, "case/autowait_zero.xml", "TC002", "type",
                 negative=True, window=(0.0, ZERO_MAX), auto_wait_ms=0, element="nameInput"),
    "W27": Check("未设置 AutoWait：就绪元素正常通过", ZERO, "case/autowait_zero.xml", "TC003", "type",
                 window=(0.0, 2.5)),
    # ---------------- 边界：AutoWait=12000
    # 下限 6.0s 而非 7.5s：8s 计时从页面加载开始，与 navigate 重叠（约 0.3~1s），步骤级计时从 type 开始，
    # 实测 7.4~7.6s，7.5s 恰在抖动边界上。本项要证明的是"等待超过 5000ms 仍能等到"，6.0s 足够。
    "W28": Check("AutoWait=12000：8s 后出现的按钮 click 通过", LONG, "case/autowait_long.xml", "TC001", "type",
                 window=(6.0, 10.5)),
    "W29": Check("AutoWait=12000：8s 后出现的输入框输入通过", LONG, "case/autowait_long.xml", "TC002", "type",
                 window=(6.0, 10.5)),
    "W30": Check("AutoWait=12000：20s 的按钮 click 在 ≈12s 失败", LONG, "case/autowait_long.xml", "TC003", "type",
                 negative=True, window=LONG_NEG_WINDOW, auto_wait_ms=12000, element="submitBtn"),
}

# 运行会改写的受跟踪产物（只恢复这些明确文件，绝不整体 checkout rodski-demo/）
_TRACKED_ARTIFACTS = ["rodski-demo/demo.db", "rodski-demo/img/tc031_actual.png", "rodski-demo/wait_test.png"]


def main(argv: List[str]) -> int:
    selected = [a.upper() for a in argv] or list(CHECKS)
    unknown = [k for k in selected if k not in CHECKS]
    if unknown:
        print(f"未知编号: {', '.join(unknown)}；可选 {', '.join(CHECKS)}")
        return 2
    server = start_site()
    failed: List[str] = []
    t_all = time.monotonic()
    try:
        for key in selected:
            c = CHECKS[key]
            t0 = time.monotonic()
            try:
                note = run_check(c)
                print(f"PASS {key} {c.title}  [{note}; 整次 {time.monotonic() - t0:.1f}s]", flush=True)
            except AssertionError as e:
                failed.append(key)
                print(f"FAIL {key} {c.title}  [整次 {time.monotonic() - t0:.1f}s]\n     {e}", flush=True)
            except Exception as e:  # noqa: BLE001 - 未实现能力可能抛任意异常，按失败记录
                failed.append(key)
                print(f"FAIL {key} {c.title}\n     {type(e).__name__}: {e}", flush=True)
    finally:
        server.shutdown()
        for m in (MOD, ZERO, LONG):
            shutil.rmtree(m / "result", ignore_errors=True)
        existing = [p for p in _TRACKED_ARTIFACTS if (REPO / p).exists()]
        if existing:
            subprocess.run(["git", "-C", str(REPO), "checkout", "--", *existing], capture_output=True)
    passed = len(selected) - len(failed)
    print(f"\n验收结果: {passed}/{len(selected)} 通过（总耗时 {time.monotonic() - t_all:.0f}s）"
          + (f"，失败: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
