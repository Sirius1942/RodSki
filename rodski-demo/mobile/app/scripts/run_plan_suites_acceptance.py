#!/usr/bin/env python3
"""mobile/app 测试套并发分发验收（v11.11.0，CORE §7.9，REQ-016）。

用法（仓库根目录）:
    python3 rodski-demo/mobile/app/scripts/run_plan_suites_acceptance.py [--udid emulator-5554] [--keep]

前置: 至少 2 台 Android 设备（globalvalue DeviceCount=2，默认一真机一模拟器）已装 com.rodski.demo，
Appium :4723 已启动。脚本在临时目录复制本模块，mock_server.py 起在 18000（Web 页面地址同步改为 18000），
每台设备 `adb reverse tcp:8000 tcp:18000`，然后执行：

- PM-01 `rodski plan compile @plan_suites_android --json`：5 个套，能力按整条用例聚合（mix=[android, web]）
- PM-02 `rodski queue --plans @plan_suites_android --platform android`：
  设备套分到两台设备、每个套只在一台设备上整体执行一次、两台设备区间重叠；
  纯 Web 套 web_note 由本地 worker 执行；summary.json 每个单元带 suite_id 与编译 digest；
  每个单元的 result.xml 只含本套用例（mix 套含数据驱动两个实例，不拆分）
- PM-03 `rodski run @plan_suites_android --suite login_fail --udid <设备> --no-queue`：只执行该套
最后一行: 汇总: PASS=x FAIL=y
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
PORT = 18000
PLAN = "plan_suites_android"
MAIN = "import sys; from rodski.rodski_cli import main; sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())"

EXPECTED_CASES = {
    "login_fail": {"APP002"},
    "order_flow": {"APP003"},
    "login_ok": {"APP001"},
    "mix": {"DD_MIX[base]", "DD_MIX[urgent]"},
    "web_note": {"WEB_NOTE01"},
}
EXPECTED_REQUIRES = {
    "login_fail": ["android"], "order_flow": ["android"], "login_ok": ["android"],
    "mix": ["android", "web"], "web_note": ["web"],
}


def _rodski(module: Path, *args: str, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", MAIN, *args], cwd=module, text=True,
                          capture_output=True, timeout=timeout)


def _results(run_dir: Path) -> dict:
    xml = run_dir / "result.xml"
    if not xml.is_file():
        return {}
    return {e.get("case_id"): e.get("status") for e in ET.parse(xml).getroot().iter("result")}


def _adb_devices() -> list:
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    return [line.split()[0] for line in out.splitlines()[1:] if line.strip().endswith("device")]


def check_compile(module: Path) -> tuple:
    proc = _rodski(module, "plan", "compile", f"@{PLAN}", "--json", timeout=120)
    if proc.returncode != 0:
        return [f"compile 退出码 {proc.returncode}: {proc.stdout[-600:]}{proc.stderr[-600:]}"], ""
    manifest = json.loads(proc.stdout)
    problems = []
    suites = {s["id"]: s for s in manifest["suites"]}
    if list(suites) != list(EXPECTED_CASES):
        problems.append(f"套顺序 {list(suites)}")
    for sid, want in EXPECTED_REQUIRES.items():
        got = suites.get(sid, {}).get("requires")
        if got != want:
            problems.append(f"{sid}.requires={got}，期望 {want}")
    if manifest.get("max_parallel") != 3:
        problems.append(f"max_parallel={manifest.get('max_parallel')}")
    if manifest.get("implicit_suite"):
        problems.append("不应是隐式套")
    return problems, manifest.get("digest", "")


def check_queue(module: Path, digest: str) -> list:
    proc = _rodski(module, "queue", "--plans", f"@{PLAN}", "--platform", "android")
    output = proc.stdout + proc.stderr
    problems = []
    queue_dirs = sorted((module / "result").glob("rodski_*_queue"))
    if not queue_dirs or not (queue_dirs[-1] / "summary.json").is_file():
        return [f"没有 summary.json；退出码 {proc.returncode}；输出尾部: {output[-1500:]}"]
    summary = json.loads((queue_dirs[-1] / "summary.json").read_text(encoding="utf-8"))
    units = summary["plans"]

    by_suite: dict = {}
    for unit in units:
        by_suite.setdefault(unit.get("suite_id"), []).append(unit)
    if sorted(by_suite) != sorted(EXPECTED_CASES):
        problems.append(f"调度单元 {sorted(map(str, by_suite))}")
    for sid, items in by_suite.items():
        if len(items) != 1:
            problems.append(f"套 {sid} 执行了 {len(items)} 次（应整体执行一次）")
        unit = items[0]
        if unit["status"] != "PASS":
            problems.append(f"套 {sid} 状态 {unit['status']}（{unit.get('error') or unit.get('pass_rate')}）")
        if unit.get("digest") != digest:
            problems.append(f"套 {sid} digest={unit.get('digest')}，编译 digest={digest}")
        got = _results(Path(unit["run_dir"])) if unit.get("run_dir") else {}
        want = EXPECTED_CASES.get(sid, set())
        if set(got) != want or any(s != "PASS" for s in got.values()):
            problems.append(f"套 {sid} result.xml 用例 {got}，期望 {sorted(want)} 全部 PASS")

    device_units = [u for u in units if u.get("suite_id") != "web_note"]
    udids = {u.get("device_udid") for u in device_units}
    if None in udids or len(udids) != 2:
        problems.append(f"设备套使用的设备 {udids}，期望两台不同设备")
    web = by_suite.get("web_note", [{}])[0]
    if web.get("device_udid") is not None:
        problems.append(f"web_note 应在本地 worker 执行，实际 device_udid={web.get('device_udid')}")

    # 两台设备的执行区间有重叠 → 套之间确实并发
    spans: dict = {}
    for u in device_units:
        if u.get("device_udid") and u.get("started_at") and u.get("finished_at"):
            spans.setdefault(u["device_udid"], []).append((u["started_at"], u["finished_at"]))
    overlap = False
    lists = list(spans.values())
    if len(lists) == 2:
        overlap = any(a0 < b1 and b0 < a1 for a0, a1 in lists[0] for b0, b1 in lists[1])
    if not overlap:
        problems.append(f"两台设备执行区间无重叠: {spans}")
    peak = summary.get("peak_parallel", 0)
    if not 2 <= peak <= 3:
        problems.append(f"peak_parallel={peak}，期望 2..3（max_parallel=3）")
    if summary.get("exit_code") != 0 or proc.returncode != 0:
        problems.append(f"退出码 summary={summary.get('exit_code')} 进程={proc.returncode}")
    if problems:
        problems.append(f"输出尾部: {output[-1500:]}")
    else:
        plan_text = "；".join(f"{u['suite_id']}@{(u.get('device_udid') or 'local')[:12]}" for u in units)
        print(f"[INFO] 排班: {plan_text}；peak_parallel={peak}")
    return problems


def check_single_suite(module: Path, udid: str) -> list:
    before = set((module / "result").glob("rodski_*"))
    proc = _rodski(module, "run", f"@{PLAN}", "--suite", "login_fail", "--udid", udid, "--no-queue")
    new_dirs = sorted(set((module / "result").glob("rodski_*")) - before)
    got = {}
    for d in new_dirs:
        got.update(_results(d))
    if proc.returncode != 0 or got != {"APP002": "PASS"}:
        return [f"退出码 {proc.returncode}；结果 {got}；输出尾部: {(proc.stdout + proc.stderr)[-1200:]}"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--udid", default="emulator-5554", help="PM-03 单套执行所用设备")
    ap.add_argument("--keep", action="store_true", help="失败时保留临时目录便于排查")
    opts = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="rodski_plan_suites_android_"))
    module = tmp / "product" / "mobile" / "app"
    shutil.copytree(MODULE, module, ignore=shutil.ignore_patterns(
        "result", "logs", "__pycache__", "demo_android_app", "demo_ios_app"))
    gv = module / "data" / "globalvalue.xml"
    gv.write_text(gv.read_text(encoding="utf-8").replace("127.0.0.1:8000/web/note", f"127.0.0.1:{PORT}/web/note"),
                  encoding="utf-8")
    server = subprocess.Popen([sys.executable, "scripts/mock_server.py", "--port", str(PORT)], cwd=module,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    devices = _adb_devices()
    rows = []
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        for udid in devices:
            subprocess.run(["adb", "-s", udid, "reverse", "tcp:8000", f"tcp:{PORT}"], capture_output=True)

        problems, digest = check_compile(module)
        rows.append(("PM-01", "编译清单", problems, "5 个套；mix 需要 [android, web]，web_note 只需 web；digest 已生成"))
        problems = check_queue(module, digest) if digest else ["编译失败，跳过"]
        rows.append(("PM-02", "队列按套分发", problems,
                     "设备套分到两台设备并发、每套整体执行一次；web_note 走本地 worker；digest 与编译一致"))
        problems = check_single_suite(module, opts.udid)
        rows.append(("PM-03", "--suite 单套执行", problems, f"只执行 login_fail（APP002）于 {opts.udid}"))
    finally:
        for udid in devices:
            subprocess.run(["adb", "-s", udid, "reverse", "--remove", "tcp:8000"], capture_output=True)
        subprocess.run(["pkill", "-TERM", "-g", str(server.pid)], capture_output=True)
        server.terminate()
        failed = any(p for _i, _t, p, _ok in rows)
        if failed and opts.keep:
            print(f"[INFO] 保留临时目录: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    for item, title, problems, ok_text in rows:
        if problems:
            print(f"FAIL\t{item}\t{title}\t" + "；".join(problems))
        else:
            print(f"PASS\t{item}\t{title}\t{ok_text}")
    failed = sum(1 for r in rows if r[2])
    print(f"汇总: PASS={len(rows) - failed} FAIL={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
