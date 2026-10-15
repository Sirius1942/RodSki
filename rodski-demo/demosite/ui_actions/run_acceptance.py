#!/usr/bin/env python3
"""demosite/ui_actions 验收脚本：UI 原子动作、控制值、定位器、verify 操作符、launch、assert 图片、
Return 跨源比对、数据生成函数。

用法（仓库根目录）:
    /usr/local/bin/python3 rodski-demo/demosite/ui_actions/run_acceptance.py            # 全部
    /usr/local/bin/python3 rodski-demo/demosite/ui_actions/run_acceptance.py F023 F040  # 按功能编号
    /usr/local/bin/python3 rodski-demo/demosite/ui_actions/run_acceptance.py KP_ENTER   # 按用例 ID

前置:
    - 共享站点 http://localhost:8000（_sites/demosite）。未运行时脚本自行启动，结束时只停自己启动的进程。
    - 本模块静态页面 fun/site/ 由脚本在 127.0.0.1:18140 启动（globalvalue.xml Site.URL）。
    - 每次执行前重建 data/data.sqlite（data/init_data.py）与 assert 参考图（fun/make_assert_refs.py）。

判定:
    每项都真实执行 `rodski run <用例文件> --case-id <ID> --headless`（包入口 rodski.rodski_cli），读取本次新生成的
    result/<run>/result.xml 与 execution.log。
    - 正向：result.xml 中该用例 status=PASS。
    - 负向（expect_fail="是"）：status=PASS（= 步骤确实失败），且失败原因包含指定关键字——防止因无关错误
      （如参数错误、依赖缺失、空校验）而"假通过"。
    - 未通过且登记在 KNOWN 表中的项输出 KNOWN（框架与文档不符，保留用例不改框架）；未登记的输出 FAIL。
    - KNOWN 项若已通过，输出 PASS 并提示可移出登记。
退出码: FAIL=0 时为 0，否则为 1。最后一行: 汇总: PASS=x FAIL=y KNOWN=z
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Sequence

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CASE_DIR = HERE / "case"
RESULT_DIR = HERE / "result"
SITE_DIR = HERE / "fun" / "site"
SITE_PORT = 18140
DEMOSITE_URL = "http://localhost:8000/"
DEMOSITE_APP = REPO / "rodski-demo" / "_sites" / "demosite" / "app.py"
RUN_SNIPPET = ("import sys; from rodski.rodski_cli import main; "
               "sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())")


# ------------------------------------------------------------------ 检查项与 KNOWN 登记
@dataclass
class Check:
    feature: str
    case_file: str
    case_id: str
    desc: str
    negative: bool = False
    # 负向：失败原因必须包含全部 must 关键字，且不包含任何 must_not 关键字
    must: Sequence[str] = ()
    must_not: Sequence[str] = ()


@dataclass
class Known:
    symptom: str
    doc: str
    suspect: str
    advice: str


CHECKS: List[Check] = [
    # F023 key_press
    Check("F023", "key_press.xml", "KP_ENTER", "key_press【Enter】作用于刚输入的输入框"),
    Check("F023", "key_press.xml", "KP_TAB", "key_press【Tab】切换焦点"),
    Check("F023", "key_press.xml", "KP_COMBO", "key_press【Control+A】组合键（macOS 上应等同 Command）"),
    Check("F023", "key_press.xml", "KP_TARGET", "key_press 作用于字段对应的目标元素"),
    # F024 drag
    Check("F024", "drag.xml", "DRAG_DEMOSITE", "demosite 首页 drag【#dropZone】"),
    Check("F024", "drag.xml", "DRAG_TARGET_B", "drag【#dropB】只落到 B 区"),
    Check("F024", "drag.xml", "DRAG_TARGET_A", "drag【#dropA】只落到 A 区"),
    # F025 scroll
    Check("F025", "scroll.xml", "SCROLL_DEFAULT", "scroll 默认向下 300px"),
    Check("F025", "scroll.xml", "SCROLL_XY", "scroll【0,500】"),
    Check("F025", "scroll.xml", "SCROLL_CHAIN", "连续滚动 / 远处元素进入视口 / 水平 / 负值"),
    # F026 BLANK / NULL / NONE
    Check("F026", "control_values.xml", "CTRL_TYPE_SKIP", "type 中 BLANK/NULL/NONE 跳过（原值保留、未聚焦）"),
    Check("F026", "control_values.xml", "CTRL_TYPE_GHOST_NULL", "type 中不存在元素填 NULL 不查找"),
    Check("F026", "control_values.xml", "CTRL_TYPE_GHOST_NONE", "type 中不存在元素填 NONE 不查找"),
    Check("F026", "control_values.xml", "CTRL_VERIFY_NONE", "verify 中 NONE 跳过验证"),
    Check("F026", "control_values.xml", "CTRL_VERIFY_NULL", "verify 中 NULL 期望 null（负向）",
          negative=True, must=("noise",)),
    # F031 class / tag / text
    Check("F031", "locators.xml", "LOC_CLASS_TYPE", "class 单类名用于 type"),
    Check("F031", "locators.xml", "LOC_MULTI_TYPE", "class 多类名用于 type"),
    Check("F031", "locators.xml", "LOC_TAG_TYPE", "tag 用于 type"),
    Check("F031", "locators.xml", "LOC_TEXT_TYPE", "text 用于 type"),
    Check("F031", "locators.xml", "LOC_CLASS_VERIFY", "class 单类名用于 verify"),
    Check("F031", "locators.xml", "LOC_MULTI_VERIFY", "class 多类名用于 verify"),
    Check("F031", "locators.xml", "LOC_TAG_VERIFY", "tag 用于 verify"),
    Check("F031", "locators.xml", "LOC_TEXT_VERIFY", "text 用于 verify"),
    # F040 元素级操作符
    Check("F040", "element_ops.xml", "OPS_ELEM_OK", "$count/$count_gte/$exists/$visible 正向"),
    Check("F040", "element_ops.xml", "OPS_ELEM_BOUND", "$count_lte/$count_gte 边界、$visible:false（不存在）"),
    Check("F040", "element_ops.xml", "OPS_ELEM_N_COUNT", "$count 6（负向）", True, ("items", "$count 断言失败", "实际 5")),
    Check("F040", "element_ops.xml", "OPS_ELEM_N_GTE", "$count_gte 6（负向）", True, ("items", "$count_gte 断言失败")),
    Check("F040", "element_ops.xml", "OPS_ELEM_N_LTE", "$count_lte 4（负向）", True, ("items", "$count_lte 断言失败")),
    Check("F040", "element_ops.xml", "OPS_ELEM_N_EXISTS", "不存在元素 $exists:true（负向）", True,
          ("absent", "$exists 断言失败", "0")),
    Check("F040", "element_ops.xml", "OPS_ELEM_N_NOTEXISTS", "存在元素 $exists:false（负向）", True,
          ("present", "$exists 断言失败")),
    Check("F040", "element_ops.xml", "OPS_ELEM_N_VISFALSE", "可见元素 $visible:false（负向）", True,
          ("shown", "$visible 断言失败")),
    Check("F040", "element_ops.xml", "OPS_ELEM_N_VISTRUE", "隐藏元素 $visible:true（负向）", True,
          ("hiddenEl", "$visible 断言失败")),
    Check("F040", "element_ops.xml", "OPS_ELEM_N_VISABSENT", "不存在元素 $visible:true（负向）", True,
          ("absent", "$visible 断言失败")),
    # F041 数值 / 包含操作符
    Check("F041", "compare_ops.xml", "OPS_CMP_OK", "$gt/$gte/$lt/$lte/$contains 正向（含等值边界）"),
    Check("F041", "compare_ops.xml", "OPS_CMP_N_GT", "128.50 $gt 128.5（负向）", True, ("pGt", "$gt 断言失败")),
    Check("F041", "compare_ops.xml", "OPS_CMP_N_GTE", "128.50 $gte 128.51（负向）", True, ("pGte", "$gte 断言失败")),
    Check("F041", "compare_ops.xml", "OPS_CMP_N_LT", "128.50 $lt 128.5（负向）", True, ("pLt", "$lt 断言失败")),
    Check("F041", "compare_ops.xml", "OPS_CMP_N_LTE", "128.50 $lte 128.49（负向）", True, ("pLte", "$lte 断言失败")),
    Check("F041", "compare_ops.xml", "OPS_CMP_N_CONTAINS", "$contains ORD-2027（负向）", True,
          ("msg", "$contains 断言失败")),
    # F017 launch
    Check("F017", "launch.xml", "LAUNCH_BAD_APP", "launch 不存在的应用应报错（负向）", True, ("launch",)),
    Check("F017", "launch.xml", "LAUNCH_BAD_SCHEME", "launch 非 http 目标 ftp:// 应报错（负向）", True, ("launch",)),
    Check("F017", "launch.xml", "LAUNCH_EMPTY", "launch 缺少目标应报错（负向）", True, ("launch", "缺少")),
    Check("F017", "launch_multi.xml", "LAUNCH_MULTI", "launch id= 多浏览器对象 + target= 定向操作"),
    # F011 assert 图片
    Check("F011", "assert_image.xml", "ASSERT_IMG_POS", "assert type=image 与参考图匹配"),
    Check("F011", "assert_image.xml", "ASSERT_IMG_NEG", "assert 参考图不在页面中（负向）", True,
          ("pattern_other.png",), ("is not defined", "不存在", "No module")),
    # F055 Return
    Check("F055", "return_ref.xml", "RET_MINUS2", "UI verify 期望值 ${Return[-2].orderNo}"),
    Check("F055", "return_ref.xml", "RET_MINUS1", "UI verify 期望值 ${Return[-1].orderNo}"),
    Check("F055", "return_ref.xml", "RET_NEG", "引用另一随机单号必须失败（负向）", True,
          ("copied", "OTH-", "ORD-"), ("${Return",)),
    # F059 random / date
    Check("F059", "generated_values.xml", "GEN_FORMAT", "random/date/timestamp36 生成值格式"),
    Check("F059", "generated_values.xml", "GEN_REEVAL", "两次求值 uuid 不同"),
    Check("F059", "generated_values.xml", "GEN_NEG", "不合规字面值被格式断言拦下（负向）", True,
          ("ok_gUser", "BAD:user_abcd")),
]

KNOWN: Dict[str, Known] = {
    "CTRL_VERIFY_NULL": Known(
        symptom="UI verify 字段填 NULL 时被跳过，页面文本 'random-noise' 与 null 不一致却通过（[预期失败但实际成功]）",
        doc="rodski/docs/CORE_DESIGN_CONSTRAINTS.md:638（§4.1 NULL 的验证行为=期望 null，未区分 UI/接口；"
            "BLANK 行 :637 则明确区分了 UI/DB 与接口）",
        suspect="rodski/core/keyword_engine.py:2767-2770（UI 模型 NULL/NONE 一律跳过）",
        advice="改文档（CORE §4.1 NULL 验证行为补充「UI 模型：跳过」）或修框架按 null 比对"),
    "LAUNCH_MULTI": Known(
        symptom="SKI204 XML 不符合 Schema 约束 (case.xsd)：'id' / 'target' attribute not allowed for element test_step，用例未执行",
        doc=".pb/specs/SPEC-012-debugging-design-constraints.md:46-84（test_step 新增 target / id，launch id= 创建命名对象）、"
            ":557「target 和 id 属性已添加到 case.xsd」；rodski/docs 下无对应条款",
        suspect="rodski/schemas/case.xsd:173-178 StepType 只有 action/model/data/match_mode；"
                "运行时 rodski/core/keyword_engine.py:_kw_launch(2165) 也不读取 id，多浏览器对象只存在于 "
                "rodski-demo/local/debug_partial_execution/fun/dbg_harness.py（demo 侧）",
        advice="修框架（扩展 case.xsd + 执行器对象池）后同步 rodski/docs；或在 SPEC-012 标注未实现"),
}


# ------------------------------------------------------------------ 基础设施
class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def _http_ok(url: str) -> Optional[bytes]:
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return resp.read() if resp.status == 200 else None
    except Exception:
        return None


def start_site() -> Optional[ThreadingHTTPServer]:
    """在 18140 启动 fun/site 静态服务；端口已被占用且内容与本模块一致时复用。"""
    try:
        ThreadingHTTPServer.allow_reuse_address = True
        server = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), partial(_QuietHandler, directory=str(SITE_DIR)))
    except OSError:
        body = _http_ok(f"http://127.0.0.1:{SITE_PORT}/keys.html")
        if body is not None and body == (SITE_DIR / "keys.html").read_bytes():
            print(f"[INFO] 端口 {SITE_PORT} 已有本模块静态服务，复用")
            return None
        raise SystemExit(f"[ENV] 端口 {SITE_PORT} 被其他服务占用，无法启动 fun/site 静态服务")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def ensure_demosite() -> Optional[subprocess.Popen]:
    if _http_ok(DEMOSITE_URL) is not None:
        print("[INFO] 共享站点 :8000 已在运行，复用")
        return None
    print("[INFO] 启动共享站点 _sites/demosite/app.py")
    proc = subprocess.Popen([sys.executable, str(DEMOSITE_APP)], cwd=str(DEMOSITE_APP.parent),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if _http_ok(DEMOSITE_URL) is not None:
            return proc
        time.sleep(0.5)
    proc.terminate()
    raise SystemExit("[ENV] 共享站点 :8000 启动失败")


def prepare_assets() -> None:
    for script in (HERE / "data" / "init_data.py", HERE / "fun" / "make_assert_refs.py"):
        subprocess.run([sys.executable, str(script)], check=True, capture_output=True, text=True)


@dataclass
class Run:
    rc: int
    out: str
    run_dir: Optional[Path]
    result: Dict[str, str] = field(default_factory=dict)

    def error_text(self) -> str:
        parts = [self.result.get("error_message", "")]
        log = self.run_dir / "execution.log" if self.run_dir else None
        if log and log.is_file():
            parts += [ln for ln in log.read_text(encoding="utf-8", errors="ignore").splitlines()
                      if "[ERROR]" in ln or "[WARNING]" in ln]
        parts += [ln for ln in self.out.splitlines() if "失败" in ln or "rror" in ln or "SKI" in ln]
        return " | ".join(p for p in parts if p)


def rodski_run(check: Check) -> Run:
    before = set(RESULT_DIR.iterdir()) if RESULT_DIR.is_dir() else set()
    cmd = [sys.executable, "-c", RUN_SNIPPET, "run", str(CASE_DIR / check.case_file),
           "--case-id", check.case_id, "--headless"]
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=300)
    after = set(RESULT_DIR.iterdir()) if RESULT_DIR.is_dir() else set()
    new_dirs = sorted(p for p in after - before if p.is_dir())
    run = Run(proc.returncode, (proc.stdout or "") + (proc.stderr or ""), new_dirs[-1] if new_dirs else None)
    xml_path = run.run_dir / "result.xml" if run.run_dir else None
    if xml_path and xml_path.is_file():
        for r in ET.parse(xml_path).getroot().iter("result"):
            if r.get("case_id") == check.case_id:
                run.result = dict(r.attrib)
    return run


def evaluate(check: Check, run: Run) -> Optional[str]:
    """返回 None 表示通过，否则返回未通过原因。"""
    if not run.result:
        tail = " / ".join(ln for ln in run.out.strip().splitlines()[-3:])
        return f"未生成 {check.case_file}::{check.case_id} 的结果（rc={run.rc}）：{tail[:300]}"
    status = run.result.get("status")
    if status != "PASS":
        return f"status={status}：{run.result.get('error_message', '')[:300]}"
    if check.negative:
        err = run.error_text()
        missing = [k for k in check.must if k not in err]
        forbidden = [k for k in check.must_not if k in err]
        if missing or forbidden:
            return (f"用例按预期失败，但失败原因不符（缺少 {missing}，出现 {forbidden}）：{err[:300]}")
    return None


def main(argv: List[str]) -> int:
    selected = [c for c in CHECKS if not argv or c.feature in argv or c.case_id in argv]
    if not selected:
        print(f"没有匹配的检查项: {argv}")
        return 2
    prepare_assets()
    server = start_site()
    demosite = ensure_demosite() if any(c.case_file == "drag.xml" for c in selected) else None
    counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}
    try:
        for c in selected:
            run = rodski_run(c)
            reason = evaluate(c, run)
            label = f"{c.feature} {c.case_file}::{c.case_id} {c.desc}"
            if reason is None:
                counts["PASS"] += 1
                note = "（KNOWN 已修复，可移出登记）" if c.case_id in KNOWN else ""
                print(f"PASS  {label}{note}")
            elif c.case_id in KNOWN:
                counts["KNOWN"] += 1
                k = KNOWN[c.case_id]
                print(f"KNOWN {label}\n      实际: {reason}\n      现象: {k.symptom}\n      文档: {k.doc}\n"
                      f"      怀疑: {k.suspect}\n      建议: {k.advice}")
            else:
                counts["FAIL"] += 1
                print(f"FAIL  {label}\n      原因: {reason}\n      结果目录: {run.run_dir}")
            sys.stdout.flush()
    finally:
        if server is not None:
            server.shutdown()
        if demosite is not None:
            demosite.terminate()
        # 负向 assert 会写失败截图到 images/assert/failures/，属于运行产物
        shutil.rmtree(HERE / "images" / "assert" / "failures", ignore_errors=True)
    print(f"汇总: PASS={counts['PASS']} FAIL={counts['FAIL']} KNOWN={counts['KNOWN']}")
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
