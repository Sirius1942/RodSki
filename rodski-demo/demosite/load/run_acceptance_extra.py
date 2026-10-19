#!/usr/bin/env python3
"""demosite/load 补充验收：F118（kind=load mode=api 压测产物与阈值）、F119（--load-ui / --load-ui-port /
--no-compile / --dry-run / mode=browser / SKI602 负向）。

用法（仓库根目录）：python3 rodski-demo/demosite/load/run_acceptance_extra.py

- 依赖 demosite :8000（未运行则由本脚本启动，结束只停止自己启动的进程）；需要 locust（rodski[load]）
- 压测计划在模块目录下以 `rodski run @plan_id` 执行（包入口）
- 只使用本模块新增的 plan/load_extra_*.xml 与 case/load_extra_cases.xml，不改动已有文件；
  运行生成的 perf/load_extra_manual*、perf/load_extra_nocompile* 会在结束时清理
- 退出码：FAIL=0 时为 0；最后一行 `汇总: PASS=x FAIL=y KNOWN=z`
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

MODULE = Path(__file__).resolve().parent
ROOT = MODULE.parents[2]
SITE = ROOT / "rodski-demo" / "_sites" / "demosite" / "app.py"
PERF = MODULE / "perf"
RESULT = MODULE / "result"
PY = os.environ.get("RODSKI_PYTHON", sys.executable)
RODSKI = [PY, "-c", "import sys; from rodski.rodski_cli import main; "
          "sys.argv=['rodski']+sys.argv[1:]; sys.exit(main())"]
CUSTOM_UI_PORT = 18159
DEFAULT_UI_PORT = 8089

KNOWN = {
    "F118-verify-fail-error-rate": (
        "压测模式跳过 verify：LOAD_TESTING_GUIDE §5.1 说 verify 失败记为失败请求，"
        "TC-LOAD-001 功能执行 verify 必失败，但压测错误率 0%、退出码 0"),
    "F118-manual-perf-used": (
        "运行时不使用 perf/{plan}.py：LocustLoadEngine 总是动态构造 RodskiLoadUser，"
        "手动修改并标记 source=manual 的 locustfile 不生效（§3.2/§8.3）"),
    "F119-doc-plan-example": "LOAD_TESTING_GUIDE §2/§4 计划示例使用 <cases> 包裹，plan.xsd 不允许，照写报 SKI204",
    "F119-dry-run-perf-path": "§7.4 说 dry-run 预览编译产物路径，实际输出不含 perf/{plan_id}.py",
}

counts = {"PASS": 0, "FAIL": 0, "KNOWN": 0}


def record(ok: bool, item: str, detail: str = "") -> None:
    verdict = "PASS" if ok else ("KNOWN" if item in KNOWN else "FAIL")
    counts[verdict] += 1
    note = f" [{KNOWN[item]}]" if verdict == "KNOWN" else ""
    if ok and item in KNOWN:
        note = " [登记为 KNOWN 但已通过，请复核是否已修复]"
    print(f"{verdict}  {item}{note}{'' if ok else ' | 实际: ' + detail}", flush=True)


def site_up() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:8000/", timeout=1) as r:
            return r.status == 200
    except OSError:
        return False


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def rodski(*args: str, timeout: int = 180) -> tuple[int, str]:
    proc = subprocess.run(RODSKI + list(args), cwd=MODULE, text=True, capture_output=True, timeout=timeout)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def results_since(t0: float) -> list[Path]:
    return sorted((p for p in RESULT.glob("result_*.xml") if p.stat().st_mtime >= t0),
                  key=lambda p: p.stat().st_mtime)


def clean_perf(plan_id: str) -> None:
    for p in (PERF / f"{plan_id}.py", PERF / f"{plan_id}.py.meta"):
        p.unlink(missing_ok=True)


def latest_summary(t0: float):
    files = results_since(t0)
    if not files:
        return None, None
    root = ET.parse(files[-1]).getroot()
    return root, files[-1]


# ───────────────────────────── F118 ─────────────────────────────
def f118_api_plan() -> None:
    t0 = time.time()
    rc, out = rodski("run", "@load_extra_api")
    record(rc == 0, "F118-api-exit0", f"rc={rc} {out[-600:]!r}")
    for marker in ("压测结果摘要", "总请求数", "错误率", "平均 RPS", "P95 延迟", "模式: 预编译"):
        record(marker in out, f"F118-stdout:{marker}", out[-400:])
    root, path = latest_summary(t0)
    if root is None:
        record(False, "F118-result-xml", "未生成 result/result_*.xml")
        return
    ls = root.find("load_summary")
    if ls is None:
        record(False, "F118-load_summary", f"{path} 中无 <load_summary>")
        return
    a = ls.attrib
    total, rps, err = int(a.get("total_requests", 0)), float(a.get("rps_avg", 0)), float(a.get("error_rate_pct", 100))
    record(total > 0, "F118-total_requests>0", str(a))
    record(rps > 0, "F118-rps_avg>0", str(a))
    record(err <= 5.0, "F118-error_rate_pct<=5", str(a))
    record(a.get("concurrency") == "3" and a.get("duration_seconds") == "8", "F118-profile回写", str(a))
    lat = ls.find("latency")
    record(lat is not None and all(k in lat.attrib for k in ("p50_ms", "p95_ms", "p99_ms", "avg_ms", "max_ms")),
           "F118-latency", str(lat.attrib if lat is not None else None))
    eps = {e.get("name"): int(e.get("requests", 0)) for e in ls.iter("endpoint")}
    login = next((v for k, v in eps.items() if "/api/login" in k), 0)
    orders = next((v for k, v in eps.items() if "/api/orders" in k), 0)
    record(login > 0 and orders > 0, "F118-endpoints两接口", str(eps))
    record(login > orders, "F118-weight 3:1 调度比例", str(eps))
    per_case = {r.get("case_id"): r.attrib for r in root.iter("result")}
    record(all(int(per_case.get(c, {}).get("load_requests", 0)) > 0 for c in ("TC-LOAD-X01", "TC-LOAD-X02")),
           "F118-result节点 load_requests", str(per_case))
    record((PERF / "load_extra_api.py").is_file() and (PERF / "load_extra_api.py.meta").is_file(),
           "F118-perf 预编译产物生成", str(list(PERF.glob("load_extra_api*"))))


def f118_verify_fail() -> None:
    # TC-LOAD-001 的 verify 功能执行必失败（strict 缺 _method 等字段）；文档：verify 失败记为失败请求 → 错误率>5% → 退出码 1
    t0 = time.time()
    rc, out = rodski("run", "@load_extra_verify_fail")
    root, _ = latest_summary(t0)
    err = float(root.find("load_summary").get("error_rate_pct", 0)) if root is not None and root.find("load_summary") is not None else -1
    record(rc == 1 and err > 5.0, "F118-verify-fail-error-rate", f"rc={rc} error_rate_pct={err}")


def f118_manual_perf() -> None:
    plan = "load_extra_manual"
    clean_perf(plan)
    try:
        rc, out = rodski("run", f"@{plan}")
        py, meta = PERF / f"{plan}.py", PERF / f"{plan}.py.meta"
        if rc != 0 or not py.is_file():
            record(False, "F118-manual-perf-used", f"首次编译失败 rc={rc} {out[-300:]!r}")
            return
        src = py.read_text(encoding="utf-8")
        new_src, n = re.subn(r"name='POST [^']*'", "name='MANUAL-MARKER'", src)
        meta_obj = json.loads(meta.read_text(encoding="utf-8"))
        meta_obj["source"] = "manual"
        py.write_text(new_src, encoding="utf-8")
        meta.write_text(json.dumps(meta_obj), encoding="utf-8")
        t0 = time.time()
        rc, out = rodski("run", f"@{plan}")
        root, _ = latest_summary(t0)
        names = [e.get("name") for e in root.iter("endpoint")] if root is not None else []
        record(n > 0 and "MANUAL-MARKER" in names, "F118-manual-perf-used", f"rc={rc} endpoints={names}")
    finally:
        clean_perf(plan)


# ───────────────────────────── F119 ─────────────────────────────
def f119_no_compile() -> None:
    plan = "load_extra_nocompile"
    clean_perf(plan)
    try:
        t0 = time.time()
        rc, out = rodski("run", f"@{plan}", "--no-compile")
        root, _ = latest_summary(t0)
        total = int(root.find("load_summary").get("total_requests", 0)) if root is not None else 0
        record(rc == 0 and total > 0, "F119-no-compile执行成功", f"rc={rc} total={total} {out[-300:]!r}")
        record("模式: 解释" in out, "F119-no-compile解释模式", out[-300:])
        record(not (PERF / f"{plan}.py").exists(), "F119-no-compile跳过预编译", str(list(PERF.glob(plan + "*"))))
    finally:
        clean_perf(plan)


def probe_ui(plan: str, port: int, extra: list[str], item: str) -> None:
    if port_open(port):
        print(f"ENV_BLOCKED  {item}: 端口 {port} 已被占用，跳过", flush=True)
        return
    proc = subprocess.Popen(RODSKI + ["run", f"@{plan}", "--load-ui", *extra], cwd=MODULE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.time() + 20
        while time.time() < deadline and not port_open(port) and proc.poll() is None:
            time.sleep(0.2)
        up = port_open(port)
        record(up, f"{item}:端口监听", f"端口 {port} 未监听")
        if up:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as r:
                    record(r.status == 200, f"{item}:仪表盘 /", f"HTTP {r.status}")
            except OSError as e:
                record(False, f"{item}:仪表盘 /", str(e))
            try:
                time.sleep(1.5)
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/stats/requests", timeout=3) as r:
                    j = json.loads(r.read().decode("utf-8"))
                record({"stats", "total_rps", "fail_ratio"} <= set(j), f"{item}:/stats/requests JSON",
                       str(sorted(j)))
            except (OSError, ValueError) as e:
                record(False, f"{item}:/stats/requests JSON", str(e))
        out, _ = proc.communicate(timeout=60)
        record(proc.returncode == 0, f"{item}:压测结束退出码0", f"rc={proc.returncode} {out[-300:]!r}")
        record(f"127.0.0.1:{port}" in out, f"{item}:终端提示监控地址", out[-300:])
        time.sleep(0.5)
        record(not port_open(port), f"{item}:结束后 Web UI 关闭", f"端口 {port} 仍在监听")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def f119_negative() -> None:
    rc, out = rodski("run", "@load_extra_ui_case")
    record(rc != 0 and "SKI602" in out, "F119-mode=api引用界面用例报SKI602", f"rc={rc} {out[-300:]!r}")

    t0 = time.time()
    rc, out = rodski("run", "@load_extra_browser")
    no_result = not results_since(t0)
    record(rc != 0 and no_result and ("browser" in out or "SKI60" in out), "F119-mode-browser",
           f"rc={rc} 生成结果={not no_result} {out[-200:]!r}")

    rc, out = rodski("run", "@load_extra_doc_example")
    record(rc == 0 and "总请求数" in out, "F119-doc-plan-example", f"rc={rc} {out[-200:]!r}")

    t0 = time.time()
    rc, out = rodski("run", "@load_extra_api", "--dry-run")
    record(rc == 0 and "TC-LOAD-X01" in out and "TC-LOAD-X02" in out and not results_since(t0),
           "F119-dry-run不发请求且列出用例", f"rc={rc} {out[-200:]!r}")
    record("perf/load_extra_api.py" in out or str(PERF / "load_extra_api.py") in out,
           "F119-dry-run-perf-path", "输出中无 perf/load_extra_api.py")

    rc, out = rodski("run", "@load_extra_api", "--tag", "smoke")
    record(rc != 0, "F119-@plan与--tag互斥", f"rc={rc} {out[-200:]!r}")


def main() -> int:
    try:
        import locust  # noqa: F401
    except ImportError:
        print("ENV_BLOCKED: 未安装 locust（pip install rodski[load]）")
        print("汇总: PASS=0 FAIL=1 KNOWN=0")
        return 1
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
    try:
        f118_api_plan()
        f118_verify_fail()
        f118_manual_perf()
        f119_no_compile()
        probe_ui("load_extra_ui_port", CUSTOM_UI_PORT, ["--load-ui-port", str(CUSTOM_UI_PORT)], "F119-load-ui-port")
        probe_ui("load_extra_ui_default", DEFAULT_UI_PORT, [], "F119-load-ui默认8089")
        f119_negative()
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
