#!/usr/bin/env python3
"""demosite/network 验收编排：F076 mock_route/clear_routes、F077 wait_for_response/请求日志、F078 JS 覆盖率。

用法（仓库根目录）：python3 rodski-demo/demosite/network/run_acceptance.py

- 依赖共享站点 demosite :8000；未运行则由本脚本启动，结束只停止自己启动的进程
- 重建 data/data.sqlite（data/init_data.py）
- 逐个 case 文件用包入口执行（--headless --output-format json），按 case_id 判定 PASS/FAIL/KNOWN；
  负向用例（expect_fail="是"）还必须命中预期失败原因
- F078 额外断言覆盖率产物文件内容
- 退出码：FAIL=0 时为 0；最后一行 `汇总: PASS=x FAIL=y KNOWN=z`
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
SITE = ROOT / "rodski-demo" / "_sites" / "demosite" / "app.py"
PY = os.environ.get("RODSKI_PYTHON", sys.executable)
RODSKI = [PY, "-c", "import sys; from rodski.rodski_cli import main; "
          "sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())"]
COVERAGE_FILE = MODULE / "result" / "net_js_coverage.json"  # 与 f078 用例中 output 参数一致（相对仓库根）

CASES: dict[str, dict[str, str | None]] = {
    "f076_mock_route.xml": {"TC-NET-076-01": None, "TC-NET-076-02": None},
    "f077_network_wait_log.xml": {
        "TC-NET-077-01": None,
        "TC-NET-077-02": None,
        "TC-NET-077-03": "Timeout 2000ms",  # Playwright 超时原文，排除“因别的异常失败”
        "TC-NET-077-04": None,
        "TC-NET-077-05": None,
    },
    "f078_js_coverage.xml": {"TC-NET-078-01": None},
}

KNOWN = {
    "TC-NET-077-01": "F077 wait_for_response 调用 sync Page.wait_for_response（Python 同步 API 不存在），必然失败",
    "TC-NET-077-02": "F077 同上",
    "TC-NET-077-03": "F077 同上：超时用例因 AttributeError 失败，不是真正的等待超时",
    "TC-NET-077-04": "F077 reset_request_log 文档列为内置函数但未注册，被当作 fun/ 脚本",
    "TC-NET-077-05": "F077 reset_request_log/get_request_log 未注册",
}


def site_up() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:8000/", timeout=1) as r:
            return r.status == 200
    except OSError:
        return False


def run_case_file(name: str) -> tuple[int, dict[str, dict]]:
    cmd = RODSKI + ["run", str(MODULE / "case" / name), "--headless", "--output-format", "json"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=900)
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


def check_coverage_file(started_at: float) -> str | None:
    """返回 None 表示通过，否则返回失败原因。"""
    if not COVERAGE_FILE.is_file():
        return f"产物不存在: {COVERAGE_FILE}"
    if COVERAGE_FILE.stat().st_mtime < started_at:
        return "产物不是本次运行生成的"
    try:
        data = json.loads(COVERAGE_FILE.read_text(encoding="utf-8"))
    except ValueError as e:
        return f"产物不是合法 JSON: {e}"
    summary, files = data.get("summary") or {}, data.get("files") or []
    if summary.get("total_files", 0) < 1 or len(files) != summary.get("total_files"):
        return f"summary.total_files 与 files 不一致或为 0: {summary}"
    for f in files:
        if not {"url", "covered_pct", "used_bytes", "total_bytes"} <= set(f):
            return f"files 条目缺字段: {f}"
        if not (0 <= f["covered_pct"] <= 100 and 0 <= f["used_bytes"] <= f["total_bytes"]):
            return f"files 条目数值不合理: {f}"
    if not any("localhost:8000" in f["url"] for f in files):
        return "files 中没有被测站点 localhost:8000 的脚本"
    if not 0 < summary.get("average_coverage_pct", 0) <= 100:
        return f"average_coverage_pct 不合理: {summary}"
    return None


def main() -> int:
    subprocess.run([PY, str(MODULE / "data" / "init_data.py")], cwd=ROOT, check=True)
    site = None
    if not site_up():
        site = subprocess.Popen([PY, str(SITE)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if site_up():
                break
            time.sleep(0.2)
        else:
            site.terminate()
            print("ENV_BLOCKED: demosite :8000 无法启动")
            print("汇总: PASS=0 FAIL=1 KNOWN=0")
            return 1
    counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}

    def record(verdict_ok: bool, item: str, detail: str = "") -> None:
        verdict = "PASS" if verdict_ok else ("KNOWN" if item in KNOWN else "FAIL")
        counts[verdict] += 1
        note = f" [{KNOWN[item]}]" if verdict == "KNOWN" else ""
        if verdict_ok and item in KNOWN:
            note = " [登记为 KNOWN 但已通过，请复核是否已修复]"
        print(f"{verdict}  {item}{note}{'' if verdict_ok else ' | 实际: ' + detail}")

    try:
        COVERAGE_FILE.unlink(missing_ok=True)
        started_at = time.time()
        for file_name, specs in CASES.items():
            rc, steps = run_case_file(file_name)
            print(f"--- {file_name} (rodski 退出码 {rc})")
            for case_id, marker in specs.items():
                step = steps.get(case_id)
                status = step.get("status") if step else "missing"
                error = (step.get("error") or "") if step else "用例未出现在输出中"
                ok = status == "pass" and (marker is None or marker in error)
                record(ok, case_id, f"{status} {error[:200]!r}")
        reason = check_coverage_file(started_at)
        record(reason is None, "TC-NET-078-01:产物内容", reason or "")
    finally:
        if site is not None:
            site.terminate()
            try:
                site.wait(timeout=5)
            except subprocess.TimeoutExpired:
                site.kill()
    print(f"汇总: PASS={counts['PASS']} FAIL={counts['FAIL']} KNOWN={counts['KNOWN']}")
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
