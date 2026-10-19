#!/usr/bin/env python3
"""F072 DialogPolicy 验收编排脚本（dialog_accept / dialog_dismiss / dialog_default 共用）。

用法（仓库根目录）:
    python3 rodski-demo/local/dialog_accept/run_acceptance.py          # 全部 D01~D05
    python3 rodski-demo/local/dialog_accept/run_acceptance.py D03 D04  # 指定编号

文档依据:
    CORE_DESIGN_CONSTRAINTS.md §2.5.6 第 4 条、§7.4（DialogPolicy 表 + 非法取值约束）
    TEST_CASE_WRITING_GUIDE.md §4.3.4、§6.4.3

脚本在 127.0.0.1:18130 以 dialog_accept/fun/site 为根目录启动静态站点（三个模块共用），
开头调用 fun/build_data.py 重新生成三个模块的 data.sqlite，每一项真实调用
`python3 rodski/cli_main.py run <模块>/case --headless` 并按 result.xml / 退出码 / 输出断言。

输出：每项一行 `PASS|FAIL|KNOWN <编号> <说明>`，最后一行
`汇总: PASS=x FAIL=y KNOWN=z`。退出码：全部 PASS 为 0，否则 1（KNOWN 也算未达标）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
LOCAL = HERE.parent
ACCEPT, DISMISS, DEFAULT = LOCAL / "dialog_accept", LOCAL / "dialog_dismiss", LOCAL / "dialog_default"
REPO = LOCAL.parent.parent
CLI = REPO / "rodski" / "cli_main.py"
PY = os.environ.get("RODSKI_PY") or sys.executable
SITE_PORT = 18130

sys.path.insert(0, str(HERE / "fun"))
from build_data import build_all  # noqa: E402

# 已登记的框架缺陷：检查失败时记为 KNOWN（仍计入未达标）
KNOWN = {
}


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def start_site() -> ThreadingHTTPServer:
    ThreadingHTTPServer.allow_reuse_address = True
    srv = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), partial(_Quiet, directory=str(ACCEPT / "fun" / "site")))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class Run:
    def __init__(self, code: int, out: str, run_dir: Optional[Path]):
        self.code, self.out, self.run_dir = code, out, run_dir

    def results(self) -> Dict[str, dict]:
        p = self.run_dir / "result.xml" if self.run_dir else None
        if not p or not p.is_file():
            return {}
        return {r.get("case_id"): dict(r.attrib) for r in ET.parse(p).getroot().iter("result")}


def rodski_run(module: Path, *extra: str) -> Run:
    rd = module / "result"
    rd.mkdir(exist_ok=True)
    before = set(rd.iterdir())
    proc = subprocess.run([PY, str(CLI), "run", str(module / "case"), "--headless", *extra],
                          cwd=str(REPO), capture_output=True, text=True, timeout=900)
    new = sorted(p for p in set(rd.iterdir()) - before if p.is_dir())
    return Run(proc.returncode, (proc.stdout or "") + (proc.stderr or ""), new[-1] if new else None)


# ---------------------------------------------------------------- 检查项
Outcome = List[Tuple[str, bool, str]]  # (子编号, 是否通过, 说明)


def expect_cases(run: Run, expected: Dict[str, str], tag: str) -> Outcome:
    res = run.results()
    out: Outcome = []
    for cid, want in expected.items():
        r = res.get(cid, {})
        got = r.get("status", "MISSING")
        msg = f"{cid} 期望 {want} 实际 {got}"
        if got != want and r.get("error_message"):
            msg += f"：{r['error_message'].splitlines()[0][:160]}"
        out.append((f"{tag}:{cid}", got == want, msg))
    return out


def d01() -> Outcome:
    """dialog_accept：DialogPolicy=accept，alert/confirm/prompt 自动确认；一次性处理器优先且只生效一次。"""
    return expect_cases(rodski_run(ACCEPT), {f"TC00{i}": "PASS" for i in range(1, 6)}, "D01")


def d02() -> Outcome:
    """dialog_dismiss：DialogPolicy=dismiss，alert 关闭、confirm=false、prompt=null；一次性 accept 只生效一次。"""
    return expect_cases(rodski_run(DISMISS), {f"TC00{i}": "PASS" for i in range(1, 5)}, "D02")


def d03() -> Outcome:
    """dialog_default：不写 DialogPolicy = fail。弹窗步骤立即失败、错误含弹窗文本、不卡住；
    遗留的一次性处理器在用例结束时清除。"""
    run = rodski_run(DEFAULT)
    out = expect_cases(run, {f"TC00{i}": "PASS" for i in range(1, 6)}, "D03")
    res = run.results()
    for cid, text in (("TC001", "确认删除订单 ORD9?"), ("TC002", "保存成功"), ("TC005", "确认删除订单 ORD9?")):
        err = res.get(cid, {}).get("error_message", "")
        out.append((f"D03:{cid}:text", text in err and "DialogPolicy=fail" in err,
                    f"{cid} 失败信息含弹窗文本「{text}」与 DialogPolicy=fail：{err.splitlines()[0][:120] if err else '(空)'}"))
        try:
            secs = float(res.get(cid, {}).get("execution_time", "nan"))
        except ValueError:
            secs = float("nan")
        # AutoWait=5000：若弹窗导致卡住/等待元素，用例耗时会 ≥ 5s
        out.append((f"D03:{cid}:fast", secs < 5.0, f"{cid} 用例耗时 {secs:.2f}s < 5s（未卡住等待）"))
    return out


def _temp_module(src: Path, gv_edit: Callable[[str], str]) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="rodski-dialog-"))
    dst = tmp / src.name
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("result", "__pycache__"))
    (dst / "result").mkdir()
    gv = dst / "data" / "globalvalue.xml"
    gv.write_text(gv_edit(gv.read_text(encoding="utf-8")), encoding="utf-8")
    return dst


def d04() -> Outcome:
    """非法取值 DialogPolicy=yes：执行开始（启动驱动）前报错，列出合法取值，不静默回落默认值（CORE §7.4）。"""
    mod = _temp_module(ACCEPT, lambda s: s.replace('name="DialogPolicy" value="accept"',
                                                   'name="DialogPolicy" value="yes"'))
    try:
        run = rodski_run(mod)
        out = run.out
        listed = all(v in out for v in ("accept", "dismiss", "fail"))
        no_exec = not run.results()
        return [
            ("D04:exit", run.code != 0, f"退出码非 0（实际 {run.code}）"),
            ("D04:msg", "DialogPolicy" in out and "yes" in out and listed,
             "错误信息含 DialogPolicy、非法值 yes 与合法取值 accept/dismiss/fail"),
            ("D04:noexec", no_exec and "启动浏览器" not in out, "未执行任何用例、未启动浏览器"),
        ]
    finally:
        shutil.rmtree(mod.parent, ignore_errors=True)


def d05() -> Outcome:
    """CLI 覆盖：文档只为 SessionMode / EvidenceMode 声明了 CLI 参数（CORE §7.4 表），
    DialogPolicy 没有 CLI 参数；这里确认 run --help 中不存在 --dialog-policy，避免文档与实现脱节。"""
    proc = subprocess.run([PY, str(CLI), "run", "--help"], capture_output=True, text=True, cwd=str(REPO))
    text = proc.stdout + proc.stderr
    return [("D05:no_cli", "--dialog-policy" not in text,
             "run --help 不含 --dialog-policy（文档未声明该参数，二者一致）")]


CHECKS: Dict[str, Callable[[], Outcome]] = {
    "D01": d01, "D02": d02, "D03": d03, "D04": d04, "D05": d05,
}


def main(argv: List[str]) -> int:
    selected = [a.upper() for a in argv] or list(CHECKS)
    build_all(quiet=True)
    srv = start_site()
    counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}
    try:
        for key in selected:
            print(f"== {key} {CHECKS[key].__doc__.strip().splitlines()[0]}")
            try:
                items = CHECKS[key]()
            except Exception as e:  # noqa: BLE001
                items = [(key, False, f"执行异常: {type(e).__name__}: {e}")]
            for sub, ok, msg in items:
                if ok:
                    status = "PASS"
                else:
                    status = "KNOWN" if sub in KNOWN else "FAIL"
                counts[status] += 1
                extra = f"  [已登记: {KNOWN[sub]}]" if status == "KNOWN" else ""
                print(f"{status}\t{sub}\t{msg}{extra}")
    finally:
        srv.shutdown()
        srv.server_close()
    print(f"汇总: PASS={counts['PASS']} FAIL={counts['FAIL']} KNOWN={counts['KNOWN']}")
    return 0 if counts["FAIL"] == 0 and counts["KNOWN"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
