#!/usr/bin/env python3
"""mock_api/http_verify 验收编排：F044 / F026 / F041 / F052。

用法（仓库根目录）：python3 rodski-demo/mock_api/http_verify/run_acceptance.py

- 重建 data/data.sqlite 与 verify_ops.db（data/init_data.py）
- 起停本模块 server.py（端口 18150；已占用且 /health 正常则复用，只停自己起的进程）
- 逐个 case 文件用包入口执行（--output-format json），按 case_id 判定：
    正向用例：status=pass → PASS
    负向用例（expect_fail="是"）：status=pass 且失败原因包含预期标记 → PASS（防止“因别的原因失败”被误判通过）
  不符合时：在 KNOWN 登记表中 → KNOWN（框架与文档不符，已登记），否则 FAIL
- 退出码：FAIL=0 时为 0，否则 1；最后一行 `汇总: PASS=x FAIL=y KNOWN=z`
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

MODULE = Path(__file__).resolve().parent
ROOT = MODULE.parents[2]
PORT = int(os.environ.get("HTTP_VERIFY_PORT", "18150"))
PY = os.environ.get("RODSKI_PYTHON", sys.executable)
RODSKI = [PY, "-c", "import sys; from rodski.rodski_cli import main; "
          "sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())"]

# case_id -> 负向用例必须出现在失败原因中的标记（None 表示正向用例）
CASES: dict[str, dict[str, str | None]] = {
    "f044_status_literal.xml": {
        "TC-HV-044-01": None,
        "TC-HV-044-02": "status(期望='201'",
        "TC-HV-044-03": "name(期望='Bob'",
        "TC-HV-044-04": None,
        "TC-HV-044-05": None,
        "TC-HV-044-06": "status(期望='shipped'",
        "TC-HV-044-07": None,
        "TC-HV-044-08": None,
        "TC-HV-044-09": "status(期望='500'",
        "TC-HV-044-10": "name(期望='Bob'",
    },
    "f026_special_values.xml": {
        "TC-HV-026-01": None, "TC-HV-026-02": None, "TC-HV-026-03": None, "TC-HV-026-04": None,
        "TC-HV-026-05": None, "TC-HV-026-06": None,
        "TC-HV-026-07": "text_field(期望=''",
        "TC-HV-026-08": "text_field(期望='null'",
    },
    "f041_operators.xml": {
        "TC-HV-041-01": None, "TC-HV-041-02": None,
        "TC-HV-041-03": "$gt 断言失败",
        "TC-HV-041-04": "$gte 断言失败",
        "TC-HV-041-05": "$lt 断言失败",
        "TC-HV-041-06": "$lte 断言失败",
        "TC-HV-041-07": "$contains 断言失败",
        "TC-HV-041-08": "$contains 断言失败",
    },
    "f052_db_operators.xml": {
        "TC-HV-052-01": None, "TC-HV-052-02": None, "TC-HV-052-03": None,
        "TC-HV-052-04": "$gt 断言失败",
    },
}

# 已登记的框架/文档不一致（KNOWN）：case_id -> 说明
KNOWN = {
    "TC-HV-052-02": "F052 DB verify 不支持断言操作符（GUIDE §5.7.1 写明适用 DB）",
    "TC-HV-052-03": "F052 同上",
    "TC-HV-052-04": "F052 同上：失败原因是字符串不等，而不是 $gt 断言失败",
}


def healthy() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=0.5) as r:
            return r.status == 200
    except OSError:
        return False


def run_case_file(name: str) -> tuple[int, dict[str, dict]]:
    cmd = RODSKI + ["run", str(MODULE / "case" / name), "--headless", "--output-format", "json"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=600)
    out = proc.stdout
    steps: dict[str, dict] = {}
    start = out.find("{\n")
    if start >= 0:
        try:
            for step in json.loads(out[start:]).get("steps", []):
                steps[step.get("case_id")] = step
        except ValueError:
            pass
    if not steps:
        print(out[-2000:], proc.stderr[-2000:], sep="\n")
    return proc.returncode, steps


def main() -> int:
    subprocess.run([PY, str(MODULE / "data" / "init_data.py")], cwd=ROOT, check=True)
    server = None
    if not healthy():
        server = subprocess.Popen([PY, str(MODULE / "server.py"), "--port", str(PORT)], cwd=ROOT,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if healthy():
                break
            time.sleep(0.1)
        else:
            server.terminate()
            print(f"ENV_BLOCKED: http_verify mock 无法在 {PORT} 端口启动")
            print("汇总: PASS=0 FAIL=1 KNOWN=0")
            return 1
    counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}
    try:
        for file_name, specs in CASES.items():
            rc, steps = run_case_file(file_name)
            print(f"--- {file_name} (rodski 退出码 {rc})")
            for case_id, marker in specs.items():
                step = steps.get(case_id)
                status = step.get("status") if step else "missing"
                error = (step.get("error") or "") if step else "用例未出现在输出中"
                ok = status == "pass" and (marker is None or marker in error)
                verdict = "PASS" if ok else ("KNOWN" if case_id in KNOWN else "FAIL")
                counts[verdict] += 1
                detail = "" if ok else f" | 实际: {status} {error[:200]!r}"
                note = f" [{KNOWN[case_id]}]" if verdict == "KNOWN" else ""
                if ok and case_id in KNOWN:
                    note = " [登记为 KNOWN 但已通过，请复核是否已修复]"
                print(f"{verdict}  {case_id}{note}{detail}")
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
    print(f"汇总: PASS={counts['PASS']} FAIL={counts['FAIL']} KNOWN={counts['KNOWN']}")
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
