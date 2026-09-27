#!/usr/bin/env python3
"""Run the complete business-model demo acceptance gate.

The gate keeps the formal PASS set and the intentional negative path-mismatch
fixture separate.  It starts the local mock only when /health is unavailable
and terminates only the process it started.
"""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = Path(__file__).resolve().parent
SERVER = MODULE / "server.py"
CASE_PASS = MODULE / "case" / "login_flows.xml"
CASE_NEGATIVE = MODULE / "case" / "expected_path_mismatch.xml"


def healthy() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=0.5) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def run(command: list[str], *, expected: int = 0) -> str:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    print(f"$ {' '.join(command)}")
    print(output.rstrip())
    if completed.returncode != expected:
        raise SystemExit(f"unexpected exit code: {completed.returncode}, expected {expected}")
    return output


def main() -> int:
    server_process = None
    if not healthy():
        server_process = subprocess.Popen([sys.executable, str(SERVER)], cwd=ROOT,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            if healthy():
                break
            time.sleep(0.1)
        else:
            server_process.terminate()
            raise SystemExit("mock API did not become healthy")

    try:
        cli = [sys.executable, "-m", "rodski.rodski_cli"]
        run(cli + ["business", "validate", str(MODULE)])
        run(cli + ["business", "graph", str(MODULE), "--id", "login_flow", "--format", "json"])
        positive = run([sys.executable, "rodski/ski_run.py", str(CASE_PASS), "--headless"])
        for case_id in ("TC-BM-LOGIN-OK", "TC-BM-LOGIN-INVALID", "TC-BM-LOGIN-LOCKED"):
            if case_id not in positive:
                raise SystemExit(f"formal case missing from output: {case_id}")
        if "总用例数: 3" not in positive or "✅ 通过: 3" not in positive or "❌ 失败: 0" not in positive:
            raise SystemExit("formal business cases did not all pass")

        coverage = run(cli + ["business", "coverage", str(MODULE), "--id", "login_flow"])
        if "nodes: 6/6" not in coverage or "edges: 5/5" not in coverage or "flows: 3/3" not in coverage:
            raise SystemExit("formal business cases did not cover all nodes, edges and flows")

        negative = run([sys.executable, "rodski/ski_run.py", str(CASE_NEGATIVE), "--headless"], expected=1)
        if "Path mismatch" not in negative:
            raise SystemExit("negative fixture did not report path mismatch")
        print("BUSINESS MODEL DEMO ACCEPTANCE: PASS (3 formal PASS + 1 expected FAIL)")
        return 0
    finally:
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
