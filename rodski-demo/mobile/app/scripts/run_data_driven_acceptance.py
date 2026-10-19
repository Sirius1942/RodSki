#!/usr/bin/env python3
"""mobile/app Web + App 混合用例数据驱动验收（REQ-013 DD-10，CORE §7.8）。

用法（仓库根目录）:
    python3 rodski-demo/mobile/app/scripts/run_data_driven_acceptance.py [--udid emulator-5554]

前置: Android 设备 / 模拟器已装 com.rodski.demo，Appium :4723 已启动。
脚本在临时目录复制本模块，mock_server.py 起在 18000（Web 页面地址同步改为 18000），
`adb reverse tcp:8000 tcp:18000` 供 App 访问，真实执行 `rodski run @web_app_mix_suite --udid <设备>`：

- DD_MIX[base]：Web 步骤与 App 步骤都用基础 DataID（W001 / WV001 / L002 / V002）
- DD_MIX[urgent]：Web 步骤替换为 W002 / WV002，App 步骤替换为 L003 / V003（V003 同时断言 App 用户名输入框为 nobody）
- 两个实例各自 PASS、各自独立会话（每个实例都重新打开浏览器页面并启动 App）
最后一行: 汇总: PASS=x FAIL=y
"""
from __future__ import annotations

import argparse
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
MAIN = "import sys; from rodski.rodski_cli import main; sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--udid", default="emulator-5554")
    ap.add_argument("--keep", action="store_true", help="失败时保留临时目录便于排查")
    udid = ap.parse_args().udid

    tmp = Path(tempfile.mkdtemp(prefix="rodski_mix_dd_"))
    module = tmp / "product" / "mobile" / "app"
    shutil.copytree(MODULE, module, ignore=shutil.ignore_patterns(
        "result", "logs", "__pycache__", "demo_android_app", "demo_ios_app"))
    gv = module / "data" / "globalvalue.xml"
    gv.write_text(gv.read_text(encoding="utf-8").replace("127.0.0.1:8000/web/note", f"127.0.0.1:{PORT}/web/note"),
                  encoding="utf-8")
    server = subprocess.Popen([sys.executable, "scripts/mock_server.py", "--port", str(PORT)], cwd=module,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    problems = []
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        subprocess.run(["adb", "-s", udid, "reverse", "tcp:8000", f"tcp:{PORT}"], capture_output=True)
        proc = subprocess.run([sys.executable, "-c", MAIN, "run", "@web_app_mix_suite", "--udid", udid, "--headless"],
                              cwd=module, text=True, capture_output=True, timeout=900)
        output = proc.stdout + proc.stderr
        results, log = {}, output
        for run_dir in sorted((module / "result").glob("rodski_*")):
            if (run_dir / "result.xml").is_file():
                for e in ET.parse(run_dir / "result.xml").getroot().iter("result"):
                    results[e.get("case_id")] = e
            if (run_dir / "execution.log").is_file():
                log += (run_dir / "execution.log").read_text(encoding="utf-8", errors="replace")
        st = {k: v.get("status") for k, v in results.items()}
        if st != {"DD_MIX[base]": "PASS", "DD_MIX[urgent]": "PASS"}:
            problems.append(f"结果 {st}；失败原因 "
                            + "；".join(f"{k}: {v.get('error_message', '')[:200]}" for k, v in results.items()
                                       if v.get("status") != "PASS")
                            + f"\n输出尾部: {output[-1200:]}")
        urgent = results.get("DD_MIX[urgent]")
        want = "WebNote.W001=W002; WebNote_verify.WV001=WV002; LoginScreen.L002=L003; LoginScreen_verify.V002=V003"
        if urgent is not None and urgent.get("replacements") != want:
            problems.append(f"urgent replacements={urgent.get('replacements')}")
        if results.get("DD_MIX[base]") is not None and results["DD_MIX[base]"].get("replacements"):
            problems.append("base 实例不应有替换")
        for line in ("数据驱动替换 WebNote: W001 → W002（MixMatrix[urgent]）",
                     "数据驱动替换 LoginScreen: L002 → L003（MixMatrix[urgent]）",
                     "数据驱动替换 LoginScreen_verify: V002 → V003（MixMatrix[urgent]）"):
            if line not in log:
                problems.append(f"日志缺少: {line}")
        if proc.returncode != 0:
            problems.append(f"退出码 {proc.returncode}")
    finally:
        subprocess.run(["adb", "-s", udid, "reverse", "--remove", "tcp:8000"], capture_output=True)
        subprocess.run(["pkill", "-TERM", "-g", str(server.pid)], capture_output=True)
        server.terminate()
        keep = problems and "--keep" in sys.argv
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
    if problems:
        print("FAIL\tDD-10\tWeb + App 混合用例数据驱动\t" + "；".join(problems))
    else:
        print("PASS\tDD-10\tWeb + App 混合用例数据驱动\t两个实例分别替换浏览器步骤与 Android 步骤的 DataID，均 PASS")
    print(f"汇总: PASS={0 if problems else 1} FAIL={1 if problems else 0}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
