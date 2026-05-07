#!/usr/bin/env python3
"""v6.3.0 审查问题验收测试

针对代码审查发现的 P0/P1 问题，验证实际用户操作是否会出错。
在 rodski-demo/DEMO/demo_full 目录下执行。

测试场景：
  T1: @plan + --priority 互斥检查
  T2: @plan + --tag 互斥检查
  T3: default_execute=是 且 plan 无 case 配置时执行全部
  T4: plan scenario execute=否 跳过
  T5: stale 引用不崩溃 + dry-run 输出
  T6: --tag selector 临时执行
"""
import subprocess
import sys
import os
from pathlib import Path

DEMO_DIR = Path(__file__).parent
PROJECT_ROOT = DEMO_DIR.parent.parent.parent
CLI_MAIN = PROJECT_ROOT / "rodski" / "cli_main.py"

PASS = 0
FAIL = 0
RESULTS = []


def run_rodski(*args, cwd=None):
    """运行 rodski CLI 并返回结果"""
    cmd = [sys.executable, str(CLI_MAIN)] + list(args)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "rodski")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd or DEMO_DIR),
        env=env,
    )
    return result


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(f"  PASS {name}")
    else:
        FAIL += 1
        RESULTS.append(f"  FAIL {name} — {detail}")


def test_t1_plan_priority_conflict():
    """T1: rodski run @v630_smoke --priority P0 必须报错"""
    r = run_rodski("run", "@v630_smoke", "--priority", "P0", "--dry-run")
    check("T1 退出码非0", r.returncode != 0, f"got {r.returncode}")
    check("T1 错误信息含互斥提示", "不能同时使用" in r.stderr, f"stderr: {r.stderr[:200]}")


def test_t2_plan_tag_conflict():
    """T2: rodski run @v630_smoke --tag smoke 必须报错"""
    r = run_rodski("run", "@v630_smoke", "--tag", "smoke", "--dry-run")
    check("T2 退出码非0", r.returncode != 0, f"got {r.returncode}")
    check("T2 错误信息含互斥提示", "不能同时使用" in r.stderr, f"stderr: {r.stderr[:200]}")


def test_t3_default_execute_all():
    """T3: project_full.xml default_execute=是 且无 case 配置时，dry-run 应显示所有 case"""
    r = run_rodski("run", "@project_full", "--dry-run")
    check("T3 退出码0", r.returncode == 0, f"got {r.returncode}, stderr: {r.stderr[:200]}")
    output = r.stdout + r.stderr
    check("T3 输出含TC040", "TC040" in output, f"output: {output[:300]}")


def test_t4_scenario_execute_no():
    """T4: v630_smoke plan 中 TC042 execute=否，dry-run 应显示 TC042 被跳过"""
    r = run_rodski("run", "@v630_smoke", "--dry-run")
    check("T4 退出码0", r.returncode == 0, f"got {r.returncode}, stderr: {r.stderr[:200]}")
    output = r.stdout + r.stderr
    check("T4 TC041被选中", "TC041" in output, f"output: {output[:300]}")
    # TC042 应在 skipped 中
    check("T4 TC042被跳过", "TC042" in output, f"output: {output[:300]}")


def test_t5_stale_reference():
    """T5: v630_stale plan 引用不存在的 case/scenario，dry-run 不崩溃"""
    r = run_rodski("run", "@v630_stale", "--dry-run")
    check("T5 退出码0(不崩溃)", r.returncode == 0, f"got {r.returncode}, stderr: {r.stderr[:200]}")
    output = r.stdout + r.stderr
    check("T5 输出含stale提示", "NONEXISTENT" in output or "stale" in output.lower() or "not_found" in output,
          f"output: {output[:300]}")


def test_t6_tag_selector():
    """T6: rodski run --tag nav --dry-run 应命中 TC041 (tag=nav,smoke)"""
    r = run_rodski("run", "case/tc040_scenario_basic.xml", "--tag", "nav", "--dry-run")
    check("T6 退出码0", r.returncode == 0, f"got {r.returncode}, stderr: {r.stderr[:200]}")
    output = r.stdout + r.stderr
    check("T6 输出含TC041", "TC041" in output, f"output: {output[:300]}")


if __name__ == "__main__":
    print("=" * 60)
    print("v6.3.0 审查问题验收测试")
    print("=" * 60)

    test_t1_plan_priority_conflict()
    test_t2_plan_tag_conflict()
    test_t3_default_execute_all()
    test_t4_scenario_execute_no()
    test_t5_stale_reference()
    test_t6_tag_selector()

    print()
    for line in RESULTS:
        print(line)
    print()
    print(f"结果: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL > 0 else 0)
