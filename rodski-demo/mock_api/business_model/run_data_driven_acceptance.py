#!/usr/bin/env python3
"""mock_api/business_model 数据驱动验收（REQ-013 DD-08 / DD-09，CORE §7.8.6）。

用法（仓库根目录）:
    python3 rodski-demo/mock_api/business_model/run_data_driven_acceptance.py

在临时目录中复制本模块，把模型 URL 改到 18001 并启动 server.py（与全量回归一致，避免与 :8000 冲突），
真实执行两个计划，读取新生成的 result.xml 与 execution.log：

- DD-08 login_invalid_matrix_suite：TC-BM-LOGIN-INVALID 按 LoginInvalidMatrix 展开 3 个实例，business_call 的
  input / expect 被替换（business_result 记录实际 DataID），flow 不变；同计划中同一业务模型的
  TC-BM-LOGIN-OK 照常执行一次。
- DD-09 login_path_mismatch_suite：actually_ok 实例输入换成正确账号，实际路径 home 与 flow=F_LOGIN_INVALID 不符
  → 该实例 FAIL；still_invalid 实例 PASS。
最后一行: 汇总: PASS=x FAIL=y
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

HERE = Path(__file__).resolve().parent
PORT = 18001
MAIN = "import sys; from rodski.rodski_cli import main; sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())"


def run_plan(module: Path, plan: str) -> Tuple[int, Dict[str, ET.Element], str]:
    before = {p.name for p in (module / "result").iterdir()} if (module / "result").is_dir() else set()
    proc = subprocess.run([sys.executable, "-c", MAIN, "run", f"@{plan}", "--headless"], cwd=module,
                          text=True, capture_output=True, timeout=300)
    results: Dict[str, ET.Element] = {}
    log = proc.stdout + proc.stderr
    for run_dir in sorted(p for p in (module / "result").iterdir() if p.name not in before):
        if (run_dir / "result.xml").is_file():
            for elem in ET.parse(run_dir / "result.xml").getroot().iter("result"):
                results[elem.get("case_id", "")] = elem
        if (run_dir / "execution.log").is_file():
            log += (run_dir / "execution.log").read_text(encoding="utf-8", errors="replace")
    return proc.returncode, results, log


def business_inputs(elem: ET.Element) -> Tuple[str, str, str]:
    br = elem.find(".//business_result")
    if br is None:
        return "", "", ""
    return br.get("input", ""), br.get("expect", ""), br.get("flow", "")


def dd08(module: Path) -> List[str]:
    code, results, log = run_plan(module, "login_invalid_matrix_suite")
    problems = []
    want = {
        "TC-BM-LOGIN-INVALID[wrong_pwd]": ("LOGIN_INVALID_01", "LOGIN_INVALID_01"),
        "TC-BM-LOGIN-INVALID[short_pwd]": ("LOGIN_INVALID_02", "LOGIN_INVALID_02"),
        "TC-BM-LOGIN-INVALID[wrong_user]": ("LOGIN_INVALID_03", "LOGIN_INVALID_03"),
        "TC-BM-LOGIN-OK": ("LOGIN_OK_01", "LOGIN_OK_01"),
    }
    if sorted(results) != sorted(want):
        problems.append(f"实例集合不符: {sorted(results)}")
    for cid, (inp, exp) in want.items():
        elem = results.get(cid)
        if elem is None:
            continue
        if elem.get("status") != "PASS":
            problems.append(f"{cid} 未通过: {elem.get('error_message', '')[:200]}")
        got = business_inputs(elem)
        if got[:2] != (inp, exp):
            problems.append(f"{cid} business_call 实际 input/expect={got[:2]}，期望 {(inp, exp)}")
        if cid.startswith("TC-BM-LOGIN-INVALID") and got[2] != "F_LOGIN_INVALID":
            problems.append(f"{cid} flow 被改变: {got[2]}")
    if "TC-BM-LOGIN-OK" in results and results["TC-BM-LOGIN-OK"].get("driver"):
        problems.append("未挂驱动表的用例不应带 driver 属性")
    for line in ("数据驱动替换 login_flow: LOGIN_INVALID_01 → LOGIN_INVALID_02（LoginInvalidMatrix[short_pwd]）",
                 "数据驱动替换 login_flow_verify: LOGIN_INVALID_01 → LOGIN_INVALID_03（LoginInvalidMatrix[wrong_user]）"):
        if line not in log:
            problems.append(f"日志缺少: {line}")
    if code != 0:
        problems.append(f"退出码 {code}")
    return problems


def dd09(module: Path) -> List[str]:
    code, results, log = run_plan(module, "login_path_mismatch_suite")
    problems = []
    st = {cid: e.get("status") for cid, e in results.items()}
    want = {"TC-BM-LOGIN-INVALID[still_invalid]": "PASS", "TC-BM-LOGIN-INVALID[actually_ok]": "FAIL"}
    if st != want:
        problems.append(f"结果 {st}，期望 {want}")
    bad = results.get("TC-BM-LOGIN-INVALID[actually_ok]")
    if bad is not None:
        text = ET.tostring(bad, encoding="unicode")
        if "home" not in text or "mismatch" not in text.lower():
            problems.append("actually_ok 的失败原因应是路径不符（实际走 home）")
        if business_inputs(bad)[2] != "F_LOGIN_INVALID":
            problems.append("flow 不应随数据改变")
    if code == 0:
        problems.append("有实例失败时退出码应非 0")
    return problems


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="rodski_bm_dd_"))
    module = tmp / "product" / "demo" / "business_model"
    shutil.copytree(HERE, module, ignore=shutil.ignore_patterns("result", "__pycache__"))
    model = module / "model" / "model.xml"
    model.write_text(model.read_text(encoding="utf-8").replace("localhost:8000", f"localhost:{PORT}"), encoding="utf-8")
    server = subprocess.Popen([sys.executable, "server.py", "--port", str(PORT)], cwd=module,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    passed = failed = 0
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        for code, desc, fn in (("DD-08", "业务模型用例数据驱动", dd08), ("DD-09", "实例路径不符判失败", dd09)):
            problems = fn(module)
            if problems:
                failed += 1
                print(f"FAIL\t{code}\t{desc}\t" + "；".join(problems), flush=True)
            else:
                passed += 1
                print(f"PASS\t{code}\t{desc}", flush=True)
    finally:
        try:
            os.killpg(server.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            # macOS 的 python3 启动器会再派生 Python.app 子进程；启动器（组长）退出后 killpg 报 EPERM，
            # 逐个结束组内仍存活的进程
            subprocess.run(["pkill", "-TERM", "-g", str(server.pid)], capture_output=True)
        server.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"汇总: PASS={passed} FAIL={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
