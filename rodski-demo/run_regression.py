#!/usr/bin/env python3
"""rodski-demo 全量回归：按运行环境分批执行每个模块的规定入口。

用法（仓库根目录）:
    python3 rodski-demo/run_regression.py                 # 全部环境
    python3 rodski-demo/run_regression.py local demosite  # 只跑指定环境
    python3 rodski-demo/run_regression.py --desktop       # 额外执行会操作鼠标键盘的桌面用例

每个入口输出一行 `<状态>\\t<入口>\\t<说明>`，状态：
    PASS         达到期望
    FAIL         未达到期望（回归）
    KNOWN        已登记的存量失败 / 未实现能力，记录实际数字
    ENV_BLOCKED  缺少环境（模拟器、视觉服务、外部仓库、桌面会话等），未执行

结果写入 rodski-demo/.regression/<时间戳>/：summary.tsv、raw/*.log、cases.json
（cases.json 为 `<模块>::<case_file>::<case_id>` → 状态列表，取自本轮新生成的 result.xml）。
运行改写的 demo.db / data.sqlite / 截图等被跟踪产物会在结束时恢复。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

DEMO = Path(__file__).resolve().parent
REPO = DEMO.parent
PY = os.environ.get("RODSKI_PY") or shutil.which("python3") or sys.executable
ENVS = ["local", "demosite", "mock_api", "mobile", "desktop_vision", "plugins"]


# 与用户使用的 `rodski` 命令同一入口（包导入）。注意不要用 rodski/cli_main.py：它以顶层名导入
# core.*，与 rodski.core.* 形成两份模块，移动端会话复用会失效（mobile/app login.xml 1/3）。
RODSKI_MAIN = "import sys; from rodski.rodski_cli import main; sys.argv = ['rodski'] + sys.argv[1:]; sys.exit(main())"


def rodski(*args: str) -> List[str]:
    return [PY, "-c", RODSKI_MAIN, *args]


# ── 服务 ────────────────────────────────────────────────

def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception as e:  # 4xx 也说明服务在
        return hasattr(e, "code")


def wait_http(url: str, seconds: int = 30) -> bool:
    for _ in range(seconds * 2):
        if http_ok(url):
            return True
        time.sleep(0.5)
    return False


class Service:
    """以独立进程组启动的后台服务；已有服务在跑时不重复启动，也不负责停止。"""

    def __init__(self, name: str, cmd: List[str], cwd: Path, url: str):
        self.name, self.cmd, self.cwd, self.url = name, cmd, cwd, url
        self.proc: Optional[subprocess.Popen] = None

    def __enter__(self):
        if not http_ok(self.url):
            log = open(f"/tmp/rodski_regression_{self.name}.log", "w")
            self.proc = subprocess.Popen(self.cmd, cwd=self.cwd, stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True)
            if not wait_http(self.url):
                raise RuntimeError(f"{self.name} 未能在 {self.url} 启动，见 /tmp/rodski_regression_{self.name}.log")
        return self

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGTERM)
            self.proc.wait(timeout=10)


def demosite() -> Service:
    return Service("demosite", [PY, "app.py"], DEMO / "_sites" / "demosite", "http://127.0.0.1:8000/")


# ── 入口 ────────────────────────────────────────────────

@dataclass
class Entry:
    env: str
    name: str
    cmd: List[str] = field(default_factory=list)
    cwd: Path = REPO
    expect: Optional[str] = None      # rodski run 期望 "N/M"；None 表示按退出码判定
    known: Optional[str] = None       # 存量失败/未实现能力说明 → 状态记为 KNOWN
    blocked: Optional[Callable[[], Optional[str]]] = None  # 返回阻塞原因则跳过
    service: Optional[Callable[[], Service]] = None
    desktop: bool = False             # 会操作真实鼠标键盘，需 --desktop


def adb_ready() -> bool:
    try:
        out = subprocess.run(["adb", "-s", "emulator-5554", "shell", "getprop", "sys.boot_completed"],
                             capture_output=True, text=True, timeout=10).stdout
        return out.strip() == "1"
    except Exception:
        return False


def need_android() -> Optional[str]:
    if not adb_ready():
        return "emulator-5554 未就绪（sys.boot_completed != 1）"
    if not http_ok("http://127.0.0.1:4723/status"):
        return "Appium :4723 未启动（appium --port 4723）"
    return None


def entries() -> List[Entry]:
    L, D, M, P = DEMO / "local", DEMO / "demosite", DEMO / "mobile", DEMO / "plugins"
    E: List[Entry] = []
    # local：模块脚本自起静态站或纯本地
    E += [
        Entry("local", "local/expressions", rodski("run", str(L / "expressions/case"), "--headless"), expect="4/4"),
        Entry("local", "local/control_flow", [PY, str(L / "control_flow/run_v7_demo.py")]),
        Entry("local", "local/hooks", [PY, str(L / "hooks/run_demo.py")]),
        Entry("local", "local/runtime_control", [PY, str(L / "runtime_control/run_demo.py")]),
        Entry("local", "local/roaming", [PY, str(L / "roaming/run_demo.py")]),
        Entry("local", "local/autowait（含 _zero/_long）", [PY, str(L / "autowait/run_acceptance.py")]),
        Entry("local", "local/authoring（含 _no_retry/_pitfalls）", [PY, str(L / "authoring/run_acceptance.py")]),
        Entry("local", "local/nested_case（含 _single/_dup_id）", [PY, str(L / "nested_case/run_acceptance.py")]),
        Entry("local", "local/control_flow 分支/循环/等待", [PY, str(L / "control_flow/run_acceptance.py")]),
        Entry("local", "local/plan_selector", [PY, str(L / "plan_selector/run_acceptance.py")]),
        Entry("local", "local/data_rules", [PY, str(L / "data_rules/run_acceptance.py")]),
        Entry("local", "local/dialog_*（accept/dismiss/default）", [PY, str(L / "dialog_accept/run_acceptance.py")]),
        Entry("local", "local/session_shared", [PY, str(L / "session_shared/run_acceptance.py")]),
        Entry("local", "local/hooks 扩展事件", [PY, str(L / "hooks/run_acceptance_extra.py")]),
        Entry("local", "local/runtime_control 终止", [PY, str(L / "runtime_control/run_acceptance_extra.py")]),
        Entry("local", "local/roaming 扩展", [PY, str(L / "roaming/run_acceptance_extra.py")]),
        Entry("local", "local/debug_partial_execution", rodski("run", str(L / "debug_partial_execution/case")),
              known="REQ-012 调试交互能力未实现，仅 AC-018 通过"),
    ]
    # debug_partial_execution_targets 逐文件执行（含按设计失败与待 case.xsd 扩展的文件）
    E.append(Entry("local", "local/debug_partial_execution_targets", [PY, "-c", _TARGETS_SNIPPET],
                   expect=None))
    # demosite：共享站点 :8000
    E += [
        Entry("demosite", "demosite/full", rodski("run", str(D / "full/case"), "--headless"),
              expect="56/56", service=demosite),
        Entry("demosite", "demosite/pause_takeover", [PY, str(D / "pause_takeover/run_demo.py")], service=demosite),
        Entry("demosite", "demosite/load @api_load_basic", rodski("run", "@api_load_basic"), cwd=D / "load",
              service=demosite),
        Entry("demosite", "demosite/load 扩展（summary/CLI）", [PY, str(D / "load/run_acceptance_extra.py")], service=demosite),
        Entry("demosite", "demosite/ui_actions", [PY, str(D / "ui_actions/run_acceptance.py")], service=demosite),
        Entry("demosite", "demosite/network", [PY, str(D / "network/run_acceptance.py")], service=demosite),
        Entry("demosite", "demosite/load case/", rodski("run", str(D / "load/case"), "--headless"),
              expect="5/5", known="TC-LOAD-001/002 verify 行缺 _method 字段（strict，见 bug A21），3/5", service=demosite),
        Entry("demosite", "demosite/core_keywords", rodski("run", str(D / "core_keywords/case"), "--headless"),
              expect="12/12", known="TC020~022 期望值与数据不符、TC025/029 verify 缺字段、TC031 assert 图片 cv2 未导入（框架 Bug），存量 6/12",
              service=demosite),
    ]
    # mock_api：自带 mock，回归时改用 18001 避免与 demosite :8000 冲突
    E.append(Entry("mock_api", "mock_api/http_verify", [PY, str(DEMO / "mock_api/http_verify/run_acceptance.py")]))
    E.append(Entry("mock_api", "mock_api/business_model (login_flows)", [PY, "-c", _BUSINESS_SNIPPET], expect="3/3"))
    # mobile
    E += [
        Entry("mobile", "mobile/app autowait", [PY, str(M / "app/scripts/run_autowait_acceptance.py")],
              blocked=need_android),
        Entry("mobile", "mobile/app login.xml", [PY, "-c", _MOBILE_LOGIN_SNIPPET], expect="3/3", blocked=need_android),
        Entry("mobile", "mobile/qq_music", blocked=lambda: "需 com.tencent.qqmusic APK，模拟器未安装"),
    ]
    # desktop_vision
    E += [
        Entry("desktop_vision", "desktop_vision/perception",
              blocked=lambda: None if (DEMO / "desktop_vision/perception/test_app").exists()
              else "缺 test_app 与 qwen3-vl:2b 视觉模型"),
        Entry("desktop_vision", "desktop_vision/desktop", rodski("run", str(DEMO / "desktop_vision/desktop/case")),
              expect="1/1", desktop=True),
    ]
    # plugins
    E += [
        Entry("plugins", "plugins/browser_plugin_baidu", rodski("run", str(P / "browser_plugin_baidu/case"), "--headless"),
              expect="5/5"),
        Entry("plugins", "plugins/browser_plugin", rodski("run", str(P / "browser_plugin/case"), "--headless"),
              expect="24/24",
              service=lambda: Service("web", [PY, "src/app.py"], REPO / "web", "http://localhost:5002/health")),
        Entry("plugins", "plugins/vscode_plugin", rodski("run", str(P / "vscode_plugin/case/tc_vscode_plugin.xml"),
                                                          "--headless"),
              expect="5/5", known="TC_PLUGIN_005 缺已安装扩展文件，存量 4/5"),
        Entry("plugins", "plugins/vscode_plugin 打开表格视图",
              rodski("run", str(P / "vscode_plugin/case/tc_vscode_open_table.xml")), expect="1/1", desktop=True),
        Entry("plugins", "plugins/website",
              blocked=lambda: None if (REPO / "rodski-website").exists() else "本机无 rodski-website 仓库（:3001）"),
    ]
    return E


_TARGETS_SNIPPET = r"""
MAIN = "import sys; from rodski.rodski_cli import main; sys.argv = ['rodski'] + sys.argv[1:]; sys.exit(main())"
import subprocess, sys, pathlib, re, os, signal, time
mod = pathlib.Path('rodski-demo/local/debug_partial_execution_targets').resolve()
srv = subprocess.Popen([sys.executable, 'fun/serve_pages.py'], cwd=mod, start_new_session=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
# 期望：DBG_DRIVER_FAIL 按设计失败；biz_from/to/range、multi 待 case.xsd 扩展
expect_fail = {'dbg_driver_fail.xml', 'dbg_biz_from.xml', 'dbg_biz_to.xml', 'dbg_biz_range.xml', 'dbg_multi.xml'}
bad = []
try:
    for f in sorted((mod / 'case').glob('*.xml')):
        out = subprocess.run([sys.executable, '-c', MAIN, 'run', str(f), '--headless'],
                             capture_output=True, text=True).stdout
        ok = bool(re.search(r'执行完成: (\d+)/\1 通过', out))
        print(f.name, 'PASS' if ok else 'FAIL')
        if ok == (f.name in expect_fail):
            bad.append(f.name)
finally:
    os.killpg(srv.pid, signal.SIGTERM)
print('不符合预期:', bad or '无')
sys.exit(1 if bad else 0)
"""

_BUSINESS_SNIPPET = r"""
MAIN = "import sys; from rodski.rodski_cli import main; sys.argv = ['rodski'] + sys.argv[1:]; sys.exit(main())"
import subprocess, sys, shutil, pathlib, os, signal, time, urllib.request
src = pathlib.Path('rodski-demo/mock_api/business_model').resolve()
tmp = pathlib.Path('/tmp/rodski_regression_bm'); shutil.rmtree(tmp, ignore_errors=True); shutil.copytree(src, tmp)
m = tmp / 'model/model.xml'; m.write_text(m.read_text(encoding='utf-8').replace('localhost:8000', 'localhost:18001'), encoding='utf-8')
srv = subprocess.Popen([sys.executable, 'server.py', '--port', '18001'], cwd=tmp, start_new_session=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(40):
    try: urllib.request.urlopen('http://127.0.0.1:18001/health', timeout=1); break
    except Exception: time.sleep(0.5)
try:
    r = subprocess.run([sys.executable, '-c', MAIN, 'run', 'case/login_flows.xml', '--headless'], cwd=tmp)
finally:
    os.killpg(srv.pid, signal.SIGTERM)
"""

_MOBILE_LOGIN_SNIPPET = r"""
MAIN = "import sys; from rodski.rodski_cli import main; sys.argv = ['rodski'] + sys.argv[1:]; sys.exit(main())"
import subprocess, sys, pathlib, os, signal, time
mod = pathlib.Path('rodski-demo/mobile/app').resolve()
srv = subprocess.Popen([sys.executable, 'scripts/mock_server.py', '--port', '18000'], cwd=mod, start_new_session=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
subprocess.run(['adb', '-s', 'emulator-5554', 'reverse', 'tcp:8000', 'tcp:18000'], capture_output=True)
try:
    subprocess.run([sys.executable, '-c', MAIN, 'run', 'case/login.xml', '--udid', 'emulator-5554'], cwd=mod)
finally:
    subprocess.run(['adb', '-s', 'emulator-5554', 'reverse', '--remove', 'tcp:8000'], capture_output=True)
    os.killpg(srv.pid, signal.SIGTERM)
"""


# ── 执行与记录 ──────────────────────────────────────────

SUMMARY_RE = re.compile(r"^执行完成: (\d+)/(\d+) 通过", re.M)  # 行首，排除嵌套子进程的缩进输出
TALLY_RE = re.compile(r"^(?:汇总|验收结果)[:：].*$", re.M)


def restore_artifacts() -> None:
    """只恢复明确的运行产物，绝不整体 checkout rodski-demo。"""
    out = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "-z", "--", "rodski-demo"],
                         capture_output=True, text=True).stdout
    paths = [p[3:] for p in out.split("\0") if p[:2] in (" M", " D")]
    keep = [p for p in paths if re.search(r"(demo\.db|data\.sqlite|\.png|test_map\.json|/result/)", p)
            and "mobile/app/data/data.sqlite" not in p]
    if keep:
        subprocess.run(["git", "-C", str(REPO), "checkout", "--", *keep], capture_output=True)


def remove_web_recordings(since: float) -> None:
    """browser_plugin 用例会让 web 服务写录制文件（被跟踪目录），清掉本轮新增的。"""
    for f in (REPO / "web" / "recordings").glob("recording_*.json"):
        if f.stat().st_mtime >= since:
            f.unlink()


def collect_cases(since: float) -> dict:
    cases: dict = {}
    for rx in list(DEMO.glob("**/result/*/result.xml")) + list(Path("/tmp/rodski_regression_bm").glob("result/*/result.xml")):
        if rx.stat().st_mtime < since:
            continue
        mod = str(rx).split("/result/")[0]
        mod = mod.replace(str(REPO) + "/", "").replace("/tmp/rodski_regression_bm", "rodski-demo/mock_api/business_model")
        for r in ET.parse(rx).getroot().iter("result"):
            cases.setdefault(f'{mod}::{r.get("case_file")}::{r.get("case_id")}', []).append(r.get("status"))
    return cases


def run_entry(e: Entry, raw: Path) -> tuple:
    if e.blocked:
        why = e.blocked()
        if why:
            return "ENV_BLOCKED", why
    if not e.cmd:
        return "ENV_BLOCKED", "无可执行入口"
    svc = e.service() if e.service else None
    try:
        if svc:
            svc.__enter__()
        p = subprocess.run(e.cmd, cwd=e.cwd, capture_output=True, text=True)
    except RuntimeError as ex:
        return "ENV_BLOCKED", str(ex)
    finally:
        if svc:
            svc.__exit__(None, None, None)
    out = p.stdout + p.stderr
    (raw / (re.sub(r"[^A-Za-z0-9_]+", "_", e.name)[:60] + ".log")).write_text(out, encoding="utf-8")
    found = SUMMARY_RE.findall(out)
    actual = f"{found[-1][0]}/{found[-1][1]}" if found else None
    ok = (actual == e.expect) if e.expect else p.returncode == 0
    detail = f"实际 {actual}" if actual else f"exit {p.returncode}"
    tally = TALLY_RE.findall(out)
    if tally and not e.expect:
        # 编排脚本汇总行（`汇总: PASS=x FAIL=y KNOWN=z` 或 `汇总: PASS x KNOWN y FAIL z`）
        counts = {k: int(v) for k, v in re.findall(r"(PASS|FAIL|KNOWN)[=\s]+(\d+)", tally[-1])}
        detail = tally[-1].strip()
        if counts.get("FAIL"):
            ok = False
        elif counts.get("KNOWN"):
            return "KNOWN", f"{detail}（KNOWN 为已登记的框架缺陷，见模块 README）"
        else:
            ok = True
    if ok:
        return "PASS", detail
    if e.known:
        return "KNOWN", f"{detail}；{e.known}"
    tail = " ".join(out.strip().splitlines()[-3:])[:300]
    return "FAIL", f"{detail}（期望 {e.expect or 'exit 0'}）{tail}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("envs", nargs="*", help=f"只执行这些环境（默认全部）：{' '.join(ENVS)}")
    ap.add_argument("--desktop", action="store_true", help="执行会操作真实鼠标键盘的桌面用例")
    args = ap.parse_args()
    unknown = set(args.envs) - set(ENVS)
    if unknown:
        ap.error(f"未知环境 {sorted(unknown)}，可选：{' '.join(ENVS)}")
    envs = args.envs or ENVS

    out_dir = DEMO / ".regression" / time.strftime("%Y%m%d_%H%M%S")
    raw = out_dir / "raw"
    raw.mkdir(parents=True)
    start = time.time()
    rows = []
    try:
        for e in entries():
            if e.env not in envs:
                continue
            if e.desktop and not args.desktop:
                status, detail = "ENV_BLOCKED", "桌面用例会操作鼠标键盘，加 --desktop 执行"
            else:
                status, detail = run_entry(e, raw)
            rows.append((status, e.name, detail))
            print(f"{status}\t{e.name}\t{detail}", flush=True)
    finally:
        cases = collect_cases(start)
        restore_artifacts()
        remove_web_recordings(start)
    (out_dir / "summary.tsv").write_text("".join(f"{s}\t{n}\t{d}\n" for s, n, d in rows), encoding="utf-8")
    (out_dir / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {s: sum(1 for r in rows if r[0] == s) for s in ("PASS", "FAIL", "KNOWN", "ENV_BLOCKED")}
    print(f"\n汇总 {counts}；逐用例 {len(cases)} 条 → {out_dir.relative_to(REPO)}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
