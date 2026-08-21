"""explore 子命令 — 探索测试 CLI

提供 explore-step 子命令，支持单步执行探索命令。
"""
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


def setup_parser(subparsers):
    """注册 explore-step 子命令"""
    p = subparsers.add_parser(
        "explore-step",
        help="执行单步探索命令",
        description="单步执行探索测试命令，返回结构化结果（JSON）",
    )

    # 必需参数
    p.add_argument("--module", required=True, help="测试模块目录")
    p.add_argument("--session", required=True, help="会话 ID")
    p.add_argument("--action", required=True, help="关键字动作（type/click/navigate/...）")

    # 可选参数
    p.add_argument("--model", default="", help="模型名称（默认空）")
    p.add_argument("--data", default="", help="数据 ID 或值（默认空）")
    p.add_argument("--confidence", type=float, default=1.0,
                   help="动作置信度 0.0-1.0（默认 1.0）")
    p.add_argument("--reversible", dest="reversible", action="store_true", default=True,
                   help="标记为可逆动作（默认）")
    p.add_argument("--no-reversible", dest="reversible", action="store_false",
                   help="标记为不可逆动作")

    # 预算参数
    p.add_argument("--budget-steps", type=int, default=50, help="最大步数（默认 50）")
    p.add_argument("--budget-duration", type=float, default=300.0,
                   help="最大时长（秒，默认 300）")
    p.add_argument("--budget-tokens", type=int, help="最大 token 数（可选）")
    p.add_argument("--budget-cost", type=float, help="最大成本（USD，可选）")

    # 其他选项
    p.add_argument("--update-test-map", action="store_true",
                   help="更新测试地图（可选，v10.1 实现）")
    p.add_argument("--output", choices=["json", "text"], default="json",
                   help="输出格式（默认 json）")


def handle(args):
    """执行 explore-step 命令"""
    from rodski.core.explore.session import (
        ExploreSession,
        ExploreSessionStore,
        BudgetGuard,
    )
    from rodski.core.explore_executor import ExploreExecutor
    from rodski.core.config_manager import ConfigManager

    module_path = Path(args.module).resolve()
    if not module_path.exists():
        _output_error(args, f"模块目录不存在: {module_path}")
        return 1

    # 1. 加载或创建会话
    store = ExploreSessionStore(module_path)
    session = store.load(args.session)

    if session is None:
        # 首次调用：创建新会话
        session = ExploreSession(
            session_id=args.session,
            module_dir=module_path,
            started_at=time.time(),
            budget={
                "steps": args.budget_steps,
                "duration": args.budget_duration,
                "tokens": args.budget_tokens,
                "cost_usd": args.budget_cost,
            },
        )

    # 2. 检查预算
    guard = BudgetGuard(session)
    stopped, reason = guard.check_budget()

    if stopped:
        session.status = "stopped"
        session.stopped_reason = reason
        store.save(session)
        _output_stopped(args, session, guard, reason)
        return 1

    # 3. 检查去重
    command = {
        "action": args.action,
        "model": args.model,
        "data": args.data,
    }

    if guard.is_duplicate(command):
        _output_duplicate(args, session, guard, command)
        return 1

    # 4. 初始化 executor（复用 run.py 的逻辑）
    try:
        keyword_engine = _init_keyword_engine(module_path)
    except Exception as e:
        _output_error(args, f"初始化执行引擎失败: {e}")
        return 1

    # 5. 调用 ExploreExecutor
    explore_executor = ExploreExecutor(keyword_engine, module_path)
    explore_executor.start_session(args.session)

    try:
        result = explore_executor.execute_command(command)
    except Exception as e:
        result = {
            "success": False,
            "evidence": {},
            "errors": [str(e)],
        }

    # 6. 记录到会话历史
    guard.record_action(command)
    session.history.append({
        "command": command,
        "result": result,
        "timestamp": time.time(),
    })

    # 7. 更新 test_map（可选，v10.1 实现）
    # if args.update_test_map and result["success"]:
    #     _update_test_map(module_path, result["evidence"])

    # 8. 保存会话
    store.save(session)

    # 9. 输出结果
    _output_result(args, session, guard, result)
    return 0 if result["success"] else 1


def _init_keyword_engine(module_path: Path):
    """初始化关键字引擎（复用 run.py 逻辑）"""
    from rodski.core.keyword_engine import KeywordEngine
    from rodski.core.config_manager import ConfigManager
    from rodski.drivers.playwright_driver import PlaywrightDriver

    # 加载配置
    config = ConfigManager.load(str(module_path))

    # 初始化驱动（简化版，只支持 Web）
    driver = PlaywrightDriver(
        browser_type="chromium",
        headless=config.get("headless", False),
        record_video=False,
    )
    driver.launch()

    # 初始化引擎
    engine = KeywordEngine(
        driver=driver,
        module_dir=str(module_path),
        config=config,
    )

    return engine


def _output_result(args, session, guard, result):
    """输出执行结果"""
    budget_status = guard.get_budget_status()

    output = {
        "success": result["success"],
        "evidence": result.get("evidence", {}),
        "session_state": {
            "session_id": session.session_id,
            "step_count": int(session.budget_spent["steps"]),
            "started_at": session.started_at,
            "duration_seconds": round(session.budget_spent["duration"], 2),
        },
        "budget_status": budget_status,
        "errors": result.get("errors", []),
    }

    if args.output == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        _print_text_result(output)


def _output_stopped(args, session, guard, reason):
    """输出预算耗尽"""
    budget_status = guard.get_budget_status()

    output = {
        "success": False,
        "evidence": {},
        "session_state": {
            "session_id": session.session_id,
            "step_count": int(session.budget_spent["steps"]),
            "started_at": session.started_at,
            "duration_seconds": round(session.budget_spent["duration"], 2),
        },
        "budget_status": budget_status,
        "errors": [f"预算耗尽: {reason}"],
    }

    if args.output == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"❌ 预算耗尽: {reason}", file=sys.stderr)
        _print_budget_status(budget_status)


def _output_duplicate(args, session, guard, command):
    """输出重复命令"""
    budget_status = guard.get_budget_status()

    output = {
        "success": False,
        "evidence": {},
        "session_state": {
            "session_id": session.session_id,
            "step_count": int(session.budget_spent["steps"]),
            "started_at": session.started_at,
            "duration_seconds": round(session.budget_spent["duration"], 2),
        },
        "budget_status": budget_status,
        "errors": [f"重复命令: {command['action']} {command['model']} {command['data']}"],
    }

    if args.output == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"❌ 重复命令: {command['action']} {command['model']}", file=sys.stderr)


def _output_error(args, message: str):
    """输出错误"""
    output = {
        "success": False,
        "evidence": {},
        "session_state": {},
        "budget_status": {},
        "errors": [message],
    }

    if args.output == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"❌ {message}", file=sys.stderr)


def _print_text_result(output: Dict[str, Any]):
    """打印文本格式结果"""
    if output["success"]:
        print("✓ 执行成功")
    else:
        print("✗ 执行失败")

    # 会话状态
    state = output["session_state"]
    print(f"\n会话: {state.get('session_id', 'N/A')}")
    print(f"  步数: {state.get('step_count', 0)}")
    print(f"  时长: {state.get('duration_seconds', 0)}s")

    # 预算状态
    _print_budget_status(output["budget_status"])

    # 证据
    evidence = output.get("evidence", {})
    if evidence.get("screenshot"):
        print(f"\n截图: {evidence['screenshot']}")
    if evidence.get("url"):
        print(f"URL: {evidence['url']}")
    if evidence.get("browser_errors"):
        print(f"浏览器错误: {len(evidence['browser_errors'])} 个")

    # 错误
    if output["errors"]:
        print(f"\n错误:")
        for err in output["errors"]:
            print(f"  - {err}")


def _print_budget_status(status: Dict[str, Any]):
    """打印预算状态"""
    print("\n预算:")

    steps = status.get("steps", {})
    if steps.get("limit"):
        print(f"  步数: {steps['used']}/{steps['limit']} (剩余 {steps['remaining']})")

    duration = status.get("duration", {})
    if duration.get("limit"):
        print(f"  时长: {duration['used']:.1f}s/{duration['limit']:.1f}s (剩余 {duration['remaining']:.1f}s)")

    if status.get("stopped"):
        print(f"  状态: 已停止 ({status.get('stopped_reason', 'unknown')})")
