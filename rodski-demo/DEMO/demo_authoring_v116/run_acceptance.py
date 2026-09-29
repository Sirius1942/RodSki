#!/usr/bin/env python3
"""v11.6.0 AI 编写效率、断言可靠性与执行性能 —— rodski-demo 验收脚本。

设计文档: .pb/specs/v11.6.0-ai-authoring-and-performance-design.md（§9.1）
验收方案: .pb/iterations/iteration-64/ACCEPTANCE.md

用法:
    python3 rodski-demo/DEMO/demo_authoring_v116/run_acceptance.py          # 全部
    python3 rodski-demo/DEMO/demo_authoring_v116/run_acceptance.py V01 V04  # 指定编号

脚本会在 127.0.0.1:8766 以 fun/site 为根目录启动本地站点（登录态验收需要真实的
http origin，data: URL 没有 cookie/localStorage），再真实调用 rodski CLI 并断言。
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
MOD = HERE                                         # demo_authoring_v116
PIT = HERE.parent / "demo_authoring_v116_pitfalls"
NORETRY = HERE.parent / "demo_authoring_v116_no_retry"
REPO = HERE.parent.parent.parent
SITE_PORT = 8766


# ---------------------------------------------------------------- 基础设施
class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401 - 静默访问日志
        pass


def start_site() -> ThreadingHTTPServer:
    handler = partial(_QuietHandler, directory=str(MOD / "fun" / "site"))
    server = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Run:
    def __init__(self, proc: subprocess.CompletedProcess, run_dir: Optional[Path], seconds: float):
        self.code = proc.returncode
        self.out = (proc.stdout or "") + (proc.stderr or "")
        self.run_dir = run_dir
        self.seconds = seconds

    def results(self) -> List[dict]:
        if not self.run_dir or not (self.run_dir / "result.xml").is_file():
            return []
        root = ET.parse(self.run_dir / "result.xml").getroot()
        return [dict(r.attrib) for r in root.iter("result")]

    def by_key(self) -> Dict[Tuple[str, str], dict]:
        return {(r.get("case_file", ""), r.get("case_id", "")): r for r in self.results()}

    def log(self) -> str:
        p = self.run_dir / "execution.log" if self.run_dir else None
        return p.read_text(encoding="utf-8", errors="ignore") if p and p.is_file() else ""

    def evidence(self, key: Tuple[str, str]) -> str:
        """某用例的失败信息：result.xml 的 error_message + 日志 + 控制台。"""
        r = self.by_key().get(key, {})
        return " ".join([r.get("error_message", ""), self.log(), self.out])


def rodski(args: List[str], module: Path = MOD, headless: bool = True) -> Run:
    result_dir = module / "result"
    before = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    cmd = ["rodski", "run", *args] + (["--headless"] if headless else [])
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=str(module), capture_output=True, text=True, timeout=900)
    seconds = time.monotonic() - t0
    after = set(result_dir.iterdir()) if result_dir.is_dir() else set()
    new_dirs = sorted(p for p in after - before if p.is_dir())
    return Run(proc, new_dirs[-1] if new_dirs else None, seconds)


def rodski_cli(args: List[str], cwd: Path = MOD) -> subprocess.CompletedProcess:
    return subprocess.run(["rodski", *args], cwd=str(cwd), capture_output=True, text=True, timeout=300)


def expect(cond: bool, msg: str, ctx: str = "") -> None:
    if not cond:
        raise AssertionError(msg + (f"\n--- 上下文 ---\n{ctx[-2500:]}" if ctx else ""))


def all_pass(r: Run, keys: List[Tuple[str, str]]) -> bool:
    got = r.by_key()
    return all(got.get(k, {}).get("status") == "PASS" for k in keys)


def pngs(d: Path) -> List[Path]:
    return sorted(d.rglob("*.png")) if d.is_dir() else []


def step_count(case_file: Path) -> int:
    return len(re.findall(r"<test_step ", case_file.read_text(encoding="utf-8")))


# ---------------------------------------------------------------- 检查项
def v01_async_count_without_wait() -> None:
    """V01 A1+A2 异步表格 $count=10，用例里没有任何 wait，verify 自动重试到期望值。"""
    f = MOD / "case/ui/assert/async_table.xml"
    expect('action="wait"' not in f.read_text(encoding="utf-8"), "V01 用例不应包含 wait 步骤")
    r = rodski(["case/ui/assert/async_table.xml"])
    keys = [("ui/assert/async_table.xml", "TC001"), ("ui/assert/async_table.xml", "TC002")]
    expect(r.code == 0 and all_pass(r, keys), f"期望 2 个用例通过: {r.results()}", r.out)


def v02_silent_pass_guard() -> None:
    """V02 A1 防静默通过：改版后选择器匹配 0 行，$count 断言必须失败并报出期望 10 / 实际 0。"""
    r = rodski(["case/negative/silent_pass_guard.xml"])
    key = ("negative/silent_pass_guard.xml", "TC001")
    res = r.by_key().get(key, {})
    expect(res.get("status") == "PASS", f"expect_fail 用例应判定 PASS（即断言确实失败了）: {res}", r.out)
    ev = r.evidence(key)
    expect(re.search(r"10", ev) and re.search(r"(实际|actual)[^0-9]{0,12}0\b", ev, re.I),
           "失败信息应包含期望 10 与实际 0", ev)


def v03_page_path_title() -> None:
    """V03 A1 page 定位类型：重定向后 path=/login.html、title=登录。"""
    r = rodski(["case/ui/assert/page_info.xml"])
    expect(r.code == 0 and all_pass(r, [("ui/assert/page_info.xml", "TC001")]), f"{r.results()}", r.out)


def v04_dialog_accept_dismiss_prompt() -> None:
    """V04 C1 dialog 元素填 accept / dismiss / accept:文本，弹窗文本可 verify。"""
    r = rodski(["case/ui/dialog/dialog.xml"])
    keys = [("ui/dialog/dialog.xml", f"TC00{i}") for i in (1, 2, 3)]
    expect(r.code == 0 and all_pass(r, keys), f"{r.results()}", r.out)


def v05_unexpected_dialog_fails_fast() -> None:
    """V05 C1 未注册处理器的弹窗在 DialogPolicy=fail 下失败并报告弹窗文本，不卡住。"""
    r = rodski(["case/negative/silent_pass_guard.xml"])
    key = ("negative/silent_pass_guard.xml", "TC002")
    res = r.by_key().get(key, {})
    expect(res.get("status") == "PASS", f"expect_fail 用例应判定 PASS（即步骤确实失败了）: {res}", r.out)
    expect("确认删除订单 ORD1?" in r.evidence(key), "失败信息应包含弹窗文本", r.evidence(key))
    expect(r.seconds < 120, f"不应卡住等待弹窗（整次运行 {r.seconds:.0f}s）")


def v06_iframe() -> None:
    """V06 C2 location@frame 定位 iframe 内元素。"""
    r = rodski(["case/ui/iframe/pay_iframe.xml"])
    expect(r.code == 0 and all_pass(r, [("ui/iframe/pay_iframe.xml", "TC001")]), f"{r.results()}", r.out)


def v07_evaluate_file() -> None:
    """V07 C3 evaluate file:fun/js/check_rows.js（脚本内含 &&），无需 XML 转义。"""
    expect("&&" in (MOD / "fun/js/check_rows.js").read_text(encoding="utf-8"), "脚本应包含 && 以覆盖转义场景")
    r = rodski(["case/ui/evaluate/evaluate_file.xml"])
    expect(r.code == 0 and all_pass(r, [("ui/evaluate/evaluate_file.xml", "TC001")]), f"{r.results()}", r.out)


def v08_v09_db_contract() -> None:
    """V08/V09 B1+B2（11.5.2 已发布）：时间字面量不当参数、sql=BLANK 回落 query，不回退。"""
    r = rodski(["case/db/db_contract.xml"], headless=False)
    keys = [("db/db_contract.xml", "TC001"), ("db/db_contract.xml", "TC002")]
    expect(r.code == 0 and all_pass(r, keys), f"{r.results()}", r.out)


def v10_v11_auth_state_shared_browser() -> None:
    """V10 P3 save/use_auth_state 跳过重复登录；V11 P2 shared_browser 下未加载登录态的用例仍被隔离。"""
    r = rodski(["case/ui/auth/auth_state.xml", "--session-mode", "shared_browser"])
    keys = [("ui/auth/auth_state.xml", f"TC00{i}") for i in (1, 2, 3)]
    expect(r.code == 0 and all_pass(r, keys), f"{r.results()}", r.out)
    tc2 = (MOD / "case/ui/auth/auth_state.xml").read_text(encoding="utf-8").split('id="TC002"')[1].split("</case>")[0]
    expect('model="Login"' not in tc2, "TC002 不应再走 UI 登录")
    # shared_browser 复用浏览器进程：本次 run 内浏览器只启动一次
    launches = len(re.findall(r"(启动浏览器|launch(ing)? browser|browser launched)", r.log(), re.I))
    expect(launches <= 1, f"shared_browser 模式下浏览器应只启动 1 次，日志中出现 {launches} 次", r.log())


def v12_workers() -> None:
    """V12 P4 --workers 4：结果与顺序执行一致，结果目录镜像无冲突。"""
    seq = rodski(["case/", "--session-mode", "isolated"])
    par = rodski(["case/", "--workers", "4"])
    expect(seq.run_dir is not None and par.run_dir is not None, "顺序或并行运行未生成结果目录", seq.out + par.out)
    expect(par.code == seq.code, f"并行退出码 {par.code} 与顺序 {seq.code} 不一致", par.out)
    s, p = seq.by_key(), par.by_key()
    expect(set(s) == set(p) and len(p) >= 15, f"并行用例集合应与顺序一致（{len(p)} vs {len(s)}）", par.out)
    expect({k: v.get("status") for k, v in s.items()} == {k: v.get("status") for k, v in p.items()},
           "并行与顺序的用例状态应一致", par.out)
    for rel in ["ui/assert/async_table", "ui/dialog/dialog", "ui/iframe/pay_iframe"]:
        expect(pngs(par.run_dir / "case" / rel / "screenshots"), f"并行结果缺少镜像截图: {rel}")
    print(f"     顺序 {seq.seconds:.1f}s / --workers 4 {par.seconds:.1f}s")


def v13_junit() -> None:
    """V13 E1 --report junit 生成 junit.xml，testcase 数量与结果一致。"""
    r = rodski(["case/ui/dialog/dialog.xml", "--report", "junit"])
    j = r.run_dir / "junit.xml" if r.run_dir else None
    expect(j is not None and j.is_file(), "应生成 junit.xml", r.out)
    root = ET.parse(j).getroot()
    cases = list(root.iter("testcase"))
    expect(len(cases) == 3, f"junit.xml 应有 3 个 testcase，实际 {len(cases)}")
    expect(all(c.get("classname") == "ui/dialog/dialog.xml" for c in cases), "classname 应为 case_file")


def v14_lint_rules() -> None:
    """V14 C5 case lint 对踩坑夹具报出各规则；对正确写法的模块无 ERROR。"""
    bad = rodski_cli(["case", "lint", str(PIT)])
    out = bad.stdout + bad.stderr
    expect(bad.returncode != 0, "夹具存在 ERROR 级问题，lint 应非 0 退出", out)
    for token, why in [("querySelectorAll", "evaluate 行数断言"), ("location.pathname", "evaluate URL 断言"),
                       ("wait", "固定等待"), ("WaitTime", "WaitTime > 0"), ("window.confirm", "confirm 垫片"),
                       ("Q_BAD", "sql/query 均无效")]:
        expect(token in out, f"lint 未报出：{why}（{token}）", out)
    good = rodski_cli(["case", "lint", str(MOD)])
    expect("ERROR" not in good.stdout + good.stderr, "正确写法的模块不应有 ERROR", good.stdout + good.stderr)


def v15_data_set() -> None:
    """V15 E2 rodski data set 修改期望值后直接重跑，无需 import；结束后恢复。"""
    db = PIT / "data" / "data.sqlite"
    backup = db.with_suffix(".sqlite.bak")
    shutil.copy2(db, backup)
    try:
        sqlite3.connect(db).execute("INSERT INTO orders(status) VALUES ('paid')").connection.commit()
        stale = rodski(["case/db/"], module=PIT, headless=False)
        expect(stale.code != 0, "orders 变为 2 行后，旧期望 n=1 应失败", stale.out)
        cp = rodski_cli(["data", "set", str(PIT), "OrderDB_verify", "V_OK", "n=2"])
        expect(cp.returncode == 0, f"data set 应成功: {cp.stdout}{cp.stderr}")
        fixed = rodski(["case/db/"], module=PIT, headless=False)
        expect(fixed.code == 0, "修改期望值后应直接通过", fixed.out)
    finally:
        shutil.move(str(backup), str(db))


def v16_evidence_concise() -> None:
    """V16 P5 --evidence concise：通过的用例无逐步截图，失败用例有失败截图；录像不受影响。"""
    ok = rodski(["case/ui/iframe/pay_iframe.xml", "--evidence", "concise", "--record"])
    expect(ok.run_dir is not None, "--evidence concise 运行未生成结果目录（参数不被支持？）", ok.out)
    base = ok.run_dir / "case" / "ui/iframe/pay_iframe"
    expect(ok.code == 0 and not pngs(base / "screenshots"), f"简洁模式下通过的用例不应有截图: {pngs(base / 'screenshots')}", ok.out)
    expect(any((base / "recordings").glob("*")) if (base / "recordings").is_dir() else False,
           "简洁模式不应关闭录像（--record 时应有录像文件）", ok.out)
    bad = rodski(["case/negative/silent_pass_guard.xml", "--evidence", "concise"])
    shots = pngs(bad.run_dir / "case" / "negative/silent_pass_guard" / "screenshots")
    expect(shots and all("failure" in p.name for p in shots), f"简洁模式只应保留失败截图: {shots}", bad.out)
    expect("concise" in (bad.run_dir / "result.xml").read_text(encoding="utf-8"), "result.xml 应标注记录模式")
    full = rodski(["case/ui/iframe/pay_iframe.xml"])
    expect(pngs(full.run_dir / "case" / "ui/iframe/pay_iframe" / "screenshots"), "默认 full 模式仍应逐步截图")


def v17_waittime_units() -> None:
    """V17 P1 WaitTime 统一毫秒：旧值 1（≤30）按秒兼容并告警；新模块 WaitTime=0 无等待。"""
    legacy = rodski(["case/db/"], module=PIT, headless=False)
    text = legacy.out + legacy.log()
    expect(re.search(r"WaitTime.{0,40}(毫秒|ms|弃用|deprecat)", text, re.I), "旧 WaitTime 应打印单位弃用告警", text)
    steps = step_count(PIT / "case/db/db_ok.xml")
    expect(legacy.seconds >= steps * 1.0, f"旧值 1 应按秒兼容（{steps} 步，实际 {legacy.seconds:.1f}s）")
    doc = (REPO / "rodski/docs/TEST_CASE_WRITING_GUIDE.md").read_text(encoding="utf-8")
    sec = doc.split("### 6.4 WaitTime")[1].split("### 6.5")[0] if "### 6.4 WaitTime" in doc else ""
    expect("毫秒" in sec, "GUIDE §6.4 应说明 WaitTime 单位为毫秒")


def v18_contract_hints() -> None:
    """V18 C4/C6 契约提示：verify 缺字段提示 subset/BLANK；capabilities 输出 pitfalls。"""
    cap = rodski_cli(["capabilities"])
    expect(cap.returncode == 0, "capabilities 应可执行", cap.stderr)
    data = json.loads(cap.stdout)
    expect(isinstance(data.get("pitfalls"), list) and len(data["pitfalls"]) >= 6,
           f"capabilities 应包含 ≥6 条 pitfalls，实际 {len(data.get('pitfalls') or [])}")
    skill = (REPO / "rodski-skills/rodski-skill--rodski-case-writer/SKILL.md").read_text(encoding="utf-8")
    expect("契约速查" in skill, "case-writer skill 应包含「契约速查」一节")


def _exec_time(r: Run, key: Tuple[str, str]) -> float:
    try:
        return float(r.by_key().get(key, {}).get("execution_time", "nan"))
    except ValueError:
        return float("nan")


def v19_dynamic_wait_positive() -> None:
    """V19 动态等待正向：6 个异步场景均不写 wait，verify 自动重试到期望值，满足即结束。"""
    f = MOD / "case/ui/wait/dynamic_wait.xml"
    expect('action="wait"' not in f.read_text(encoding="utf-8"), "动态等待用例不应包含 wait 步骤")
    r = rodski(["case/ui/wait/dynamic_wait.xml"])
    scenarios = {
        "TC001": "1500ms 后出现的文本", "TC002": "处理中→已完成（须读到最新值）",
        "TC003": "逐条追加到 10 条", "TC004": "两字段须同时满足",
        "TC005": "加载遮罩消失（$exists=false）", "TC006": "隐藏按钮变为可见（$visible）",
    }
    got = r.by_key()
    failed = [f"{tc} {name}: {got.get(('ui/wait/dynamic_wait.xml', tc), {}).get('status')} "
              f"{got.get(('ui/wait/dynamic_wait.xml', tc), {}).get('error_message', '')[:120]}"
              for tc, name in scenarios.items()
              if got.get(("ui/wait/dynamic_wait.xml", tc), {}).get("status") != "PASS"]
    expect(r.code == 0 and not failed, "以下动态等待场景未通过:\n  " + "\n  ".join(failed), r.out)
    # 满足即结束：最晚的变化在 2.5s，若 verify 空等到 AutoWait(5000ms) 才返回，单用例会明显超过 5.5s
    slow = {tc: round(_exec_time(r, ("ui/wait/dynamic_wait.xml", tc)), 2) for tc in scenarios
            if not _exec_time(r, ("ui/wait/dynamic_wait.xml", tc)) < 5.5}
    expect(not slow, f"条件满足后应立即结束，以下用例耗时 ≥5.5s: {slow}")
    print("     耗时(s): " + ", ".join(f"{tc}={_exec_time(r, ('ui/wait/dynamic_wait.xml', tc)):.1f}" for tc in scenarios))


def v20_dynamic_wait_boundary() -> None:
    """V20 动态等待边界：超过 AutoWait 必须失败且不卡死；DB verify 不重试、立即失败。"""
    r = rodski(["case/negative/dynamic_wait_boundary.xml"])
    late, db = ("negative/dynamic_wait_boundary.xml", "TC001"), ("negative/dynamic_wait_boundary.xml", "TC002")
    got = r.by_key()
    expect(got.get(late, {}).get("status") == "PASS",
           f"超时场景应真的失败（expect_fail 判定 PASS）: {got.get(late)}", r.out)
    t = _exec_time(r, late)
    expect(4.0 <= t <= 15.0, f"超时场景耗时应在 AutoWait(5000ms) 附近（4~15s），实际 {t:.1f}s："
                             f"过短说明没有重试，过长说明被其他等待拖住")
    expect("超时才出现" in r.evidence(late), "失败信息应包含期望值「超时才出现」", r.evidence(late))
    expect(got.get(db, {}).get("status") == "PASS", f"DB verify 期望写错应失败: {got.get(db)}", r.out)
    td = _exec_time(r, db)
    expect(td < 3.0, f"DB verify 不应自动重试（应立即失败），实际耗时 {td:.1f}s")
    print(f"     超时场景 {t:.1f}s / DB 立即失败 {td:.1f}s")


def v21_verify_timeout_zero() -> None:
    """V21 AutoWait=0 关闭自动重试：1s 后出现的文本在单次比对下必须失败。"""
    r = rodski(["case/"], module=NORETRY)
    res = r.by_key().get(("no_retry.xml", "TC001"), {})
    expect(res.get("status") == "PASS",
           f"AutoWait=0 时 verify 应只比对一次并失败（expect_fail 判定 PASS）；"
           f"若仍重试，文本 1s 后出现会让断言成功、本用例判为不通过: {res}", r.out)


CHECKS: Dict[str, Callable[[], None]] = {
    "V01": v01_async_count_without_wait, "V02": v02_silent_pass_guard, "V03": v03_page_path_title,
    "V04": v04_dialog_accept_dismiss_prompt, "V05": v05_unexpected_dialog_fails_fast, "V06": v06_iframe,
    "V07": v07_evaluate_file, "V08": v08_v09_db_contract, "V10": v10_v11_auth_state_shared_browser,
    "V12": v12_workers, "V13": v13_junit, "V14": v14_lint_rules, "V15": v15_data_set,
    "V16": v16_evidence_concise, "V17": v17_waittime_units, "V18": v18_contract_hints,
    "V19": v19_dynamic_wait_positive, "V20": v20_dynamic_wait_boundary, "V21": v21_verify_timeout_zero,
}


def main(argv: List[str]) -> int:
    selected = argv or list(CHECKS)
    server = start_site()
    failed = []
    try:
        for key in selected:
            fn = CHECKS[key]
            title = fn.__doc__.splitlines()[0]
            try:
                fn()
                print(f"PASS {key} {title}")
            except AssertionError as e:
                failed.append(key)
                print(f"FAIL {key} {title}\n     {e}")
            except Exception as e:  # noqa: BLE001 - 未实现的能力可能抛出任意异常，按失败记录
                failed.append(key)
                print(f"FAIL {key} {title}\n     {type(e).__name__}: {e}")
    finally:
        server.shutdown()
        for m in (MOD, PIT, NORETRY):
            shutil.rmtree(m / "result", ignore_errors=True)
        subprocess.run(["git", "-C", str(REPO), "checkout", "--", "rodski-demo/demo.db",
                        "rodski-demo/img/tc031_actual.png", "rodski-demo/wait_test.png"],
                       capture_output=True)
    print(f"\n验收结果: {len(selected) - len(failed)}/{len(selected)} 通过" + (f"，失败: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
