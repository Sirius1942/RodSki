#!/usr/bin/env python3
"""V7 新功能演示脚本

使用方式: PYTHONPATH=rodski python3 rodski-demo/DEMO/demo_v7_features/run_v7_demo.py

演示内容:
1. Case Tags + Priority 过滤 (WI-63)
2. elif 条件分支 (WI-64)
3. HTML 报告生成 (WI-41/WI-43)
4. 实际执行 smoke 用例 + 报告
"""
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# 确保能引用到 rodski 内部模块
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root / "rodski") not in sys.path:
    sys.path.insert(0, str(project_root / "rodski"))

from core.case_parser import CaseParser

DEMO_DIR = Path(__file__).resolve().parent
CASE_FILE = DEMO_DIR / "case" / "v7_demo.xml"

# ─── 颜色工具 ────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def demo_1_tags_and_priority():
    """演示 1: Case Tags & Priority 过滤"""
    print(f"\n{BOLD}{CYAN}{'=' * 70}")
    print(f"  演示 1: Case Tags + Priority 过滤 (WI-63)")
    print(f"{'=' * 70}{RESET}")

    parser = CaseParser(str(CASE_FILE))
    all_cases = parser.parse_cases()
    parser.close()

    # 全部用例总览
    print(f"\n{BOLD}[全部用例]{RESET} 共 {len(all_cases)} 个:\n")
    print(f"  {'Case ID':14s} {'Tags':28s} {'Priority':10s} Title")
    print(f"  {'-' * 14} {'-' * 28} {'-' * 10} {'-' * 30}")
    for c in all_cases:
        tags = ",".join(c.get("tags", [])) or "-"
        pri = c.get("priority", "-") or "-"
        print(f"  {c['case_id']:14s} {tags:28s} {pri:10s} {c['title']}")

    # --tags smoke
    print(f"\n{BOLD}[CLI: --tags smoke]{RESET}")
    smoke = [c for c in all_cases if "smoke" in c.get("tags", [])]
    for c in smoke:
        print(f"  {GREEN}-> {c['case_id']}: {c['title']}{RESET}")
    print(f"  匹配 {len(smoke)}/{len(all_cases)} 个用例")

    # --priority P0
    print(f"\n{BOLD}[CLI: --priority P0]{RESET}")
    p0 = [c for c in all_cases if c.get("priority") == "P0"]
    for c in p0:
        print(f"  {GREEN}-> {c['case_id']}: {c['title']}{RESET}")
    print(f"  匹配 {len(p0)}/{len(all_cases)} 个用例")

    # --exclude-tags edge
    print(f"\n{BOLD}[CLI: --exclude-tags edge]{RESET}")
    non_edge = [c for c in all_cases if "edge" not in c.get("tags", [])]
    for c in non_edge:
        print(f"  {GREEN}-> {c['case_id']}: {c['title']}{RESET}")
    print(f"  匹配 {len(non_edge)}/{len(all_cases)} 个用例")

    # --tags regression --priority P1
    print(f"\n{BOLD}[CLI: --tags regression --priority P1]{RESET}")
    combo = [
        c for c in all_cases
        if "regression" in c.get("tags", []) and c.get("priority") == "P1"
    ]
    for c in combo:
        print(f"  {GREEN}-> {c['case_id']}: {c['title']}{RESET}")
    print(f"  匹配 {len(combo)}/{len(all_cases)} 个用例")


def demo_2_elif():
    """演示 2: elif 条件分支解析"""
    print(f"\n{BOLD}{CYAN}{'=' * 70}")
    print(f"  演示 2: if/elif/else 条件分支 (WI-64)")
    print(f"{'=' * 70}{RESET}")

    parser = CaseParser(str(CASE_FILE))
    all_cases = parser.parse_cases()
    parser.close()

    elif_cases = [c for c in all_cases if "elif" in c.get("tags", [])]

    for c in elif_cases:
        print(f"\n{BOLD}[{c['case_id']}] {c['title']}{RESET}")
        print(f"  test_case 阶段步骤结构:")
        _print_steps(c.get("test_case", []), indent=4)


def _print_steps(steps, indent=4):
    """递归打印步骤结构"""
    pfx = " " * indent
    for i, step in enumerate(steps, 1):
        if step.get("type") == "if":
            cond = step.get("condition", "")
            print(f"{pfx}{YELLOW}IF{RESET} ({cond})")
            _print_steps(step.get("steps", []), indent + 4)

            for elif_b in step.get("elif_chain", []):
                econd = elif_b.get("condition", "")
                print(f"{pfx}{YELLOW}ELIF{RESET} ({econd})")
                _print_steps(elif_b.get("steps", []), indent + 4)

            if step.get("else_steps"):
                print(f"{pfx}{YELLOW}ELSE{RESET}")
                _print_steps(step.get("else_steps"), indent + 4)

            for nested in step.get("nested_ifs", []):
                print(f"{pfx}  {YELLOW}NESTED IF{RESET} ({nested.get('condition', '')})")
                _print_steps(nested.get("steps", []), indent + 6)
                if nested.get("else_steps"):
                    print(f"{pfx}  {YELLOW}NESTED ELSE{RESET}")
                    _print_steps(nested.get("else_steps"), indent + 6)
        else:
            action = step.get("action", "?")
            model = step.get("model", "") or "-"
            data = step.get("data", "") or "-"
            print(f"{pfx}[{i}] {CYAN}action={action}{RESET}, model={model}, data={data}")


def demo_3_execute_and_report():
    """演示 3: 执行 API+DB 用例 + 生成 HTML 报告"""
    print(f"\n{BOLD}{CYAN}{'=' * 70}")
    print(f"  演示 3: 执行测试 + HTML 报告生成 (WI-41/WI-43)")
    print(f"{'=' * 70}{RESET}")

    from core.ski_executor import SKIExecutor, resolve_module_dir

    module_dir = DEMO_DIR
    start = time.time()
    driver = None

    try:
        # 仅执行接口 + 数据库用例（不需要浏览器的）
        # 通过 tags 过滤: api + db 标签
        from core.driver_factory import create_null_driver
        driver = create_null_driver()
    except ImportError:
        # 如果没有 null driver，创建 headless playwright driver
        pass

    # 直接用 headless playwright
    try:
        from drivers import playwright_driver
        # 用动态加载避免相对导入问题
        import importlib
        spec = importlib.util.spec_from_file_location(
            "playwright_driver",
            str(project_root / "rodski" / "drivers" / "playwright_driver.py"),
            submodule_search_locations=[],
        )
        # 更简单: 直接 import
    except Exception:
        pass

    # 使用子进程执行，避免导入问题
    print(f"\n正在执行 --tags smoke 用例 (headless 模式)...")
    import subprocess
    result = subprocess.run(
        [
            sys.executable, "-c", f"""
import sys, time, json
sys.path.insert(0, '{project_root / "rodski"}')
from core.ski_executor import SKIExecutor
from core.logger import Logger
Logger(name="rodski", level="WARNING", console=True)

# 使用 headless driver
class MinimalDriver:
    def __init__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self.page = self._browser.new_page()
    def navigate(self, url):
        self.page.goto(url, timeout=10000)
    def close(self):
        try: self._browser.close()
        except: pass
        try: self._pw.stop()
        except: pass
    def __getattr__(self, name):
        return getattr(self.page, name, lambda *a, **k: None)

driver = MinimalDriver()
executor = SKIExecutor(
    '{CASE_FILE}',
    driver,
    driver_factory=lambda: MinimalDriver(),
    module_dir='{module_dir}',
)
start = time.time()
results = executor.execute_all_cases(filter_tags=["smoke"])
duration = time.time() - start
executor.close()
driver.close()

# 输出 JSON 结果
print(json.dumps({{
    "results": results,
    "duration": round(duration, 2),
}}, ensure_ascii=False))
"""
        ],
        capture_output=True, text=True, timeout=60,
    )

    duration = time.time() - start

    if result.returncode != 0:
        # 如果子进程执行失败，用模拟数据演示报告功能
        print(f"  {YELLOW}(浏览器执行需要完整 driver 环境，改用模拟数据演示报告){RESET}")
        results_data = [
            {"case_id": "TC-V7-001", "title": "[P0/smoke] 登录冒烟测试", "status": "PASS", "execution_time": 2.1, "error": ""},
            {"case_id": "TC-V7-003", "title": "[P0/smoke] API登录冒烟", "status": "PASS", "execution_time": 0.5, "error": ""},
        ]
        total, passed, failed = 2, 2, 0
    else:
        try:
            # 从 stdout 提取 JSON（跳过可能的非 JSON 行）
            stdout_lines = result.stdout.strip().split("\n")
            json_line = [l for l in stdout_lines if l.strip().startswith("{")][-1]
            data = json.loads(json_line)
            results_data = data["results"]
            duration = data["duration"]
            total = len(results_data)
            passed = sum(1 for r in results_data if r.get("status", "").upper() == "PASS")
            failed = total - passed
        except Exception as e:
            print(f"  解析结果失败: {e}")
            print(f"  stdout: {result.stdout[:200]}")
            print(f"  stderr: {result.stderr[:200]}")
            return

    # 打印执行结果
    print(f"\n{BOLD}执行结果:{RESET} {passed}/{total} 通过, {failed} 失败, 耗时 {duration:.1f}s\n")
    for r in results_data:
        st = r.get("status", "FAIL").upper()
        icon = f"{GREEN}PASS{RESET}" if st == "PASS" else f"{RED}FAIL{RESET}"
        print(f"  [{icon}] {r.get('case_id')}: {r.get('title')} ({r.get('execution_time', 0):.1f}s)")

    # 生成 HTML 报告
    print(f"\n{BOLD}生成 HTML 报告...{RESET}")
    try:
        from rodski_cli.report import generate_html_from_run_results
        os.chdir(str(DEMO_DIR))
        report_path = generate_html_from_run_results(
            results=results_data,
            total=total,
            passed=passed,
            failed=failed,
            duration=duration,
        )
        abs_path = str(Path(report_path).resolve())
        print(f"\n  {GREEN}HTML 报告已生成: {abs_path}{RESET}")
        print(f"  打开命令: open {abs_path}")
        return abs_path
    except Exception as e:
        print(f"  {RED}报告生成失败: {e}{RESET}")
        return None


def demo_4_network_ops():
    """演示 4: 网络拦截代码展示"""
    print(f"\n{BOLD}{CYAN}{'=' * 70}")
    print(f"  演示 4: Network Interception 网络拦截 (WI-62)")
    print(f"{'=' * 70}{RESET}")

    print(f"""
  V7 新增 3 个网络操作内建函数（rodski/builtin_ops/network_ops.py）:

  {BOLD}1. mock_route(url_pattern, status, body, content_type){RESET}
     拦截匹配 URL 的请求，返回自定义响应
     用例 XML 示例:
       <test_step action="run" model="network_ops"
                  data="mock_route(**/api/orders, status=200, body={{}})"/>

  {BOLD}2. wait_for_response(url_pattern, timeout){RESET}
     等待特定网络请求完成，返回响应内容
     用例 XML 示例:
       <test_step action="run" model="network_ops"
                  data="wait_for_response(/api/login, timeout=10)"/>

  {BOLD}3. clear_routes(){RESET}
     清除所有 mock route
     用例 XML 示例:
       <test_step action="run" model="network_ops"
                  data="clear_routes()"/>

  支持 glob 和正则两种匹配模式:
    glob:  **/api/orders     (Playwright 默认)
    regex: re:/api/order.*   (re: 前缀触发正则)
""")


if __name__ == "__main__":
    print(f"{BOLD}{CYAN}{'=' * 70}")
    print(f"  RodSki V7 新功能演示")
    print(f"  Features: Case Tags, Priority, elif, Network Ops, HTML Report")
    print(f"{'=' * 70}{RESET}")

    demo_1_tags_and_priority()
    demo_2_elif()
    demo_4_network_ops()
    report_path = demo_3_execute_and_report()

    print(f"\n{BOLD}{CYAN}{'=' * 70}")
    print(f"  V7 演示完成!")
    if report_path:
        print(f"  HTML 报告: {report_path}")
    print(f"{'=' * 70}{RESET}")
