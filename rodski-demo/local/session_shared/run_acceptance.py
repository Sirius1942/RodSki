#!/usr/bin/env python3
"""F073 SessionMode 验收编排脚本（session_shared 模块）。

用法（仓库根目录）:
    python3 rodski-demo/local/session_shared/run_acceptance.py          # 全部 S01~S05
    python3 rodski-demo/local/session_shared/run_acceptance.py S02      # 指定编号

文档依据:
    CORE_DESIGN_CONSTRAINTS.md §7.4（SessionMode 表、非法取值、优先级 CLI > globalvalue > 默认）、
    §23.1（三种模式语义；shared_browser 一次 run 只启动一次浏览器）、§23.4（result.xml summary@session_mode）
    TEST_CASE_WRITING_GUIDE.md §6.4.4

模块 globalvalue 配置 SessionMode=shared_session。脚本在 127.0.0.1:18131 以 fun/site 为根目录起静态站，
开头调用 fun/build_data.py 生成 data.sqlite，然后真实执行 `rodski run case/ --headless [--session-mode X]`：
  TC001 写入 localStorage + cookie 标记后 close；TC002 重新打开页面读取标记。
  - shared_session（globalvalue）：TC002 读到标记 → PASS；浏览器只启动 1 次
  - --session-mode isolated：TC002 读不到 → FAIL；浏览器启动 2 次
  - --session-mode shared_browser：TC002 读不到（每用例新 context）→ FAIL；浏览器只启动 1 次
输出与退出码约定同 dialog_accept/run_acceptance.py。
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
REPO = HERE.parent.parent.parent
CLI = REPO / "rodski" / "cli_main.py"
PY = os.environ.get("RODSKI_PY") or sys.executable
SITE_PORT = 18131
MODES = ("isolated", "shared_browser", "shared_session")

sys.path.insert(0, str(HERE / "fun"))
from build_data import build  # noqa: E402

KNOWN: Dict[str, str] = {}


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def start_site() -> ThreadingHTTPServer:
    ThreadingHTTPServer.allow_reuse_address = True
    srv = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), partial(_Quiet, directory=str(HERE / "fun" / "site")))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class Run:
    def __init__(self, code: int, out: str, run_dir: Optional[Path]):
        self.code, self.out, self.run_dir = code, out, run_dir

    def _root(self):
        p = self.run_dir / "result.xml" if self.run_dir else None
        return ET.parse(p).getroot() if p and p.is_file() else None

    def results(self) -> Dict[str, dict]:
        root = self._root()
        return {} if root is None else {r.get("case_id"): dict(r.attrib) for r in root.iter("result")}

    def summary_mode(self) -> Optional[str]:
        root = self._root()
        s = root.find("summary") if root is not None else None
        return s.get("session_mode") if s is not None else None

    def browser_launches(self) -> int:
        log = self.run_dir / "execution.log" if self.run_dir else None
        if not log or not log.is_file():
            return -1
        return sum(1 for ln in log.read_text(encoding="utf-8", errors="ignore").splitlines() if "启动浏览器:" in ln)


def rodski_run(module: Path, *extra: str) -> Run:
    rd = module / "result"
    rd.mkdir(exist_ok=True)
    before = set(rd.iterdir())
    proc = subprocess.run([PY, str(CLI), "run", str(module / "case"), "--headless", *extra],
                          cwd=str(REPO), capture_output=True, text=True, timeout=900)
    new = sorted(p for p in set(rd.iterdir()) - before if p.is_dir())
    return Run(proc.returncode, (proc.stdout or "") + (proc.stderr or ""), new[-1] if new else None)


Outcome = List[Tuple[str, bool, str]]


def _mode_check(tag: str, run: Run, mode: str, tc2: str, launches: int) -> Outcome:
    res = run.results()
    out: Outcome = []
    for cid, want in (("TC001", "PASS"), ("TC002", tc2)):
        r = res.get(cid, {})
        got = r.get("status", "MISSING")
        msg = f"{cid} 期望 {want} 实际 {got}"
        if r.get("error_message"):
            msg += f"：{r['error_message'].splitlines()[0][:140]}"
        out.append((f"{tag}:{cid}", got == want, msg))
    if tc2 == "FAIL":
        err = res.get("TC002", {}).get("error_message", "")
        out.append((f"{tag}:TC002:reason", "实际='none'" in err,
                    "TC002 失败原因是读不到标记（实际='none'），不是其他错误"))
    out.append((f"{tag}:summary", run.summary_mode() == mode,
                f"result.xml summary@session_mode 期望 {mode} 实际 {run.summary_mode()}"))
    got_l = run.browser_launches()
    out.append((f"{tag}:launch", got_l == launches, f"execution.log 浏览器启动次数 期望 {launches} 实际 {got_l}"))
    return out


def s01() -> Outcome:
    """globalvalue SessionMode=shared_session：跨用例共享 localStorage/cookie，close 不关闭会话，浏览器只启动一次。"""
    return _mode_check("S01", rodski_run(HERE), "shared_session", "PASS", 1)


def s02() -> Outcome:
    """CLI --session-mode isolated 覆盖 globalvalue：每用例启动浏览器，完全隔离。"""
    return _mode_check("S02", rodski_run(HERE, "--session-mode", "isolated"), "isolated", "FAIL", 2)


def s03() -> Outcome:
    """CLI --session-mode shared_browser 覆盖 globalvalue：浏览器只启动一次，但每用例新 context（不继承 storage/cookie）。"""
    return _mode_check("S03", rodski_run(HERE, "--session-mode", "shared_browser"), "shared_browser", "FAIL", 1)


def s04() -> Outcome:
    """globalvalue 非法取值 SessionMode=bogus：启动驱动前报错并列出合法取值（CORE §7.4）。"""
    tmp = Path(tempfile.mkdtemp(prefix="rodski-session-"))
    mod = tmp / HERE.name
    shutil.copytree(HERE, mod, ignore=shutil.ignore_patterns("result", "__pycache__"))
    (mod / "result").mkdir()
    gv = mod / "data" / "globalvalue.xml"
    gv.write_text(gv.read_text(encoding="utf-8").replace('value="shared_session"', 'value="bogus"'), encoding="utf-8")
    try:
        run = rodski_run(mod)
        return [
            ("S04:exit", run.code != 0, f"退出码非 0（实际 {run.code}）"),
            ("S04:msg", "SessionMode" in run.out and "bogus" in run.out and all(m in run.out for m in MODES),
             "错误信息含 SessionMode、非法值 bogus 与全部合法取值"),
            ("S04:noexec", not run.results(), "未执行任何用例"),
        ]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def s05() -> Outcome:
    """CLI 非法取值 --session-mode bogus：参数解析阶段报错并列出合法取值。"""
    proc = subprocess.run([PY, str(CLI), "run", str(HERE / "case"), "--headless", "--session-mode", "bogus"],
                          cwd=str(REPO), capture_output=True, text=True, timeout=120)
    out = proc.stdout + proc.stderr
    return [
        ("S05:exit", proc.returncode != 0, f"退出码非 0（实际 {proc.returncode}）"),
        ("S05:msg", all(m in out for m in MODES), "错误信息列出 isolated / shared_browser / shared_session"),
    ]


CHECKS: Dict[str, Callable[[], Outcome]] = {"S01": s01, "S02": s02, "S03": s03, "S04": s04, "S05": s05}


def main(argv: List[str]) -> int:
    selected = [a.upper() for a in argv] or list(CHECKS)
    build(quiet=True)
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
                status = "PASS" if ok else ("KNOWN" if sub in KNOWN else "FAIL")
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
