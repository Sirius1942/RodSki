"""run 子命令 - 通过 SKIExecutor 执行测试用例（XML 版本）"""
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rodski")


def setup_parser(subparsers):
    parser = subparsers.add_parser("run", help="执行测试用例")
    parser.add_argument("case", nargs="?", help="用例路径（XML 文件、case/ 目录或测试模块目录）或计划引用 (@plan_id)")
    parser.add_argument("--model", help="模型文件路径 (model.xml)，不指定则自动推断")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"],
                        default="chromium", help="浏览器类型 (默认: chromium)")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="验证用例但不实际执行")
    parser.add_argument("--output", help="报告输出路径")
    parser.add_argument("--output-format", choices=["text", "json"],
                        default="text", help="输出格式 (默认: text)")
    parser.add_argument("--report", choices=["html"], default=None,
                        help="执行完毕后自动生成报告 (可选值: html)")
    parser.add_argument("--insert-step", action="append", dest="insert_steps",
                        help="插入动态步骤 (格式: action,model,data)")
    parser.add_argument("--tag", "--tags", type=str, default=None, action="append", dest="tags",
                        help="按标签过滤用例 (逗号分隔，OR 匹配；--tag 为推荐别名)")
    parser.add_argument("--group", type=str, default=None, dest="filter_group",
                        help="按 scenario group 过滤")
    parser.add_argument("--priority", type=str, default=None,
                        help="按优先级过滤用例 (逗号分隔，如 P0,P1)")
    parser.add_argument("--exclude-tag", "--exclude-tags", type=str, default=None, action="append", dest="exclude_tags",
                        help="排除包含指定标签的用例 (逗号分隔；--exclude-tag 为推荐别名)")
    parser.add_argument("--record", action="store_true",
                        help="启用本次执行的视频录制")
    parser.add_argument("--record-mode", choices=["auto", "screen", "playwright", "off"],
                        default=None, help="录制模式 (默认读取配置)")
    parser.add_argument("--record-scope", choices=["target", "full_screen", "all_screens"],
                        default=None, help="屏幕录制范围 (默认读取配置)")
    parser.add_argument("--record-monitor", type=int, default=None,
                        help="屏幕录制 monitor_id，未指定则自动选择目标/主屏")
    parser.add_argument("--record-resolution", type=str, default=None,
                        help="录制分辨率 (screen/2k/hd/WxH，如 1920x1080)")
    parser.add_argument("--debug", action="store_true",
                        help="启用调试执行模式（仅对 scenario_debug/step_debug 类型的 plan 生效）")


def _split_csv_values(raw_values):
    """将逗号分隔的 CLI 参数归一化为列表。

    argparse 中 --tag/--tags 等别名使用 action=append；为兼容测试或旧代码
    直接传入字符串的情况，这里同时接受 str、list/tuple 或 None。
    """
    if raw_values is None:
        return None
    if isinstance(raw_values, str):
        values = [raw_values]
    else:
        values = list(raw_values)

    parsed = []
    for value in values:
        if not value:
            continue
        parsed.extend(part.strip() for part in str(value).split(",") if part.strip())
    return parsed or None


def _build_selector_filters(args) -> Dict[str, Any]:
    """构建 selector 相关过滤参数，供 executor 保留/后续编译使用。"""
    return {
        "filter_tags": _split_csv_values(getattr(args, "tags", None)),
        "filter_group": getattr(args, "filter_group", None),
        "filter_priority": _split_csv_values(getattr(args, "priority", None)),
        "exclude_tags": _split_csv_values(getattr(args, "exclude_tags", None)),
    }


def _is_plan_ref(value) -> bool:
    """判断参数是否为 @plan_id 引用。"""
    return isinstance(value, str) and value.startswith("@") and len(value) > 1


def _resolve_plan_path(plan_ref: str, module_dir: Path) -> Path:
    """将 @plan_id 解析为测试模块下的 plan/{plan_id}.xml。"""
    if not _is_plan_ref(plan_ref):
        raise ValueError(f"无效的计划引用: {plan_ref}")
    plan_id = plan_ref[1:]
    return module_dir / "plan" / f"{plan_id}.xml"


def _resolve_default_plan(module_dir: Path) -> Optional[Path]:
    """解析未指定 case/plan 时的默认计划。"""
    plan_dir = module_dir / "plan"
    if not plan_dir.is_dir():
        return None

    project_full = plan_dir / "project_full.xml"
    if project_full.is_file():
        return project_full

    full_plans = sorted(plan_dir.glob("*_full.xml"))
    if len(full_plans) == 1:
        return full_plans[0]
    if len(full_plans) > 1:
        names = ", ".join(p.stem for p in full_plans)
        raise ValueError(f"存在多个 full 计划 ({names})，请显式指定 @plan_id")
    return None


def _resolve_module_dir_from_cwd(cwd: Optional[Path] = None) -> Path:
    """从当前目录推导测试模块目录。"""
    current = cwd or Path.cwd()
    if current.name in {"case", "model", "data", "plan"}:
        return current.parent
    return current


def _resolve_case_path(input_path: Path) -> Path:
    """智能解析用例路径"""
    if input_path.is_file() and input_path.suffix == '.xml':
        return input_path
    if input_path.is_dir():
        if input_path.name == 'case':
            return input_path
        case_dir = input_path / 'case'
        if case_dir.is_dir():
            return case_dir
    return input_path


def _resolve_module_dir(case_path: Path) -> Path:
    """从 case 路径推导测试模块目录"""
    if case_path.is_file():
        return case_path.parent.parent
    elif case_path.is_dir() and case_path.name == 'case':
        return case_path.parent
    return case_path


def handle(args):
    verbose = getattr(args, "verbose", False)
    dry_run = getattr(args, "dry_run", False)

    raw_case = getattr(args, "case", None)
    plan_path = None

    if _is_plan_ref(raw_case):
        module_dir = _resolve_module_dir_from_cwd()
        case_path = _resolve_case_path(module_dir)
        plan_path = _resolve_plan_path(raw_case, module_dir)
        if not plan_path.exists():
            print(f"错误: 测试计划不存在: {plan_path}", file=sys.stderr)
            return 1
    elif raw_case is None:
        module_dir = _resolve_module_dir_from_cwd()
        try:
            plan_path = _resolve_default_plan(module_dir)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
        if plan_path is None:
            print("错误: 未指定用例路径，且未找到默认测试计划", file=sys.stderr)
            print("提示: 使用 rodski run <case_path> 或 rodski run @plan_id", file=sys.stderr)
            return 1
        case_path = _resolve_case_path(module_dir)
    else:
        raw_path = Path(raw_case)
        if not raw_path.exists():
            print(f"错误: 路径不存在: {raw_case}", file=sys.stderr)
            return 1

        case_path = _resolve_case_path(raw_path)
        module_dir = _resolve_module_dir(case_path)

    if args.model:
        model_path = Path(args.model)
    else:
        model_path = module_dir / "model" / "model.xml"

    if not model_path.exists():
        print(f"错误: 模型文件不存在: {model_path}", file=sys.stderr)
        print(f"提示: 使用 --model 参数指定模型文件路径", file=sys.stderr)
        return 1

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # 构建 selector 过滤参数并检查互斥
    selector_filters = _build_selector_filters(args)
    plan_path_str = str(plan_path) if plan_path else None
    try:
        try:
            from ..core.test_plan_selection import check_plan_selector_conflict
        except ImportError:
            from core.test_plan_selection import check_plan_selector_conflict
        check_plan_selector_conflict(plan_path_str, selector_filters)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(f"用例路径: {case_path}")
    if plan_path is not None:
        print(f"测试计划: {plan_path}")
    print(f"模型文件: {model_path}")
    print(f"浏览器: {args.browser}")

    if dry_run:
        return _handle_dry_run(case_path, model_path, verbose, plan_path=plan_path, selector_filters=selector_filters)

    return _handle_execute(case_path, module_dir, args, plan_path=plan_path, selector_filters=selector_filters)


def _apply_recording_args(config, args):
    recording = dict(config.get("recording", {}) or {})
    if getattr(args, "record", False):
        recording["enabled"] = True
    record_mode = getattr(args, "record_mode", None)
    if record_mode:
        recording["mode"] = record_mode
        if record_mode == "off":
            recording["enabled"] = False
    record_scope = getattr(args, "record_scope", None)
    if record_scope:
        recording["scope"] = record_scope
    record_monitor = getattr(args, "record_monitor", None)
    if record_monitor is not None:
        recording["monitor_id"] = record_monitor
    record_resolution = getattr(args, "record_resolution", None)
    if record_resolution is not None:
        recording["video_size"] = record_resolution
    config.config["recording"] = recording
    return config


def _handle_dry_run(
    case_path: Path,
    model_path: Path,
    verbose: bool,
    plan_path: Optional[Path] = None,
    selector_filters: Optional[Dict[str, Any]] = None,
) -> int:
    """验证用例可执行性但不实际执行"""
    try:
        from ..core.case_parser import CaseParser
        from ..core.model_parser import ModelParser
        from ..core.plan_parser import PlanParser
        from ..core.test_plan_selection import TestPlanSelection, compile_from_selector
    except ImportError:
        from core.case_parser import CaseParser
        from core.model_parser import ModelParser
        from core.plan_parser import PlanParser
        from core.test_plan_selection import TestPlanSelection, compile_from_selector

    try:
        model_parser = ModelParser(str(model_path))
        case_parser = CaseParser(str(case_path))
        cases = case_parser.parse_cases()
        case_parser.close()
    except Exception as e:
        print(f"解析失败: {e}", file=sys.stderr)
        return 1

    print(f"\n[Dry Run] 用例验证结果:")
    print(f"  模型数: {len(model_parser.models)}")
    print(f"  用例数: {len(cases)}")

    if plan_path is not None:
        try:
            parser = PlanParser(str(plan_path))
            parse = getattr(parser, 'parse', None) or parser.parse_plan
            plan = parse()
            selection = TestPlanSelection(cases, plan).select()
        except Exception as e:
            print(f"Plan 解析失败: {e}", file=sys.stderr)
            return 1
        _print_plan_dry_run_selection(plan, selection)
    elif selector_filters and _has_active_selector(selector_filters):
        metadata = CaseParser.collect_scenario_metadata_from_cases(cases)
        # compile_from_selector expects filter_priority as a single string
        raw_priority = selector_filters.get("filter_priority")
        priority_str = raw_priority[0] if isinstance(raw_priority, list) and raw_priority else raw_priority
        selection = compile_from_selector(
            metadata,
            filter_tags=selector_filters.get("filter_tags"),
            filter_group=selector_filters.get("filter_group"),
            exclude_tags=selector_filters.get("exclude_tags"),
            filter_priority=priority_str,
        )
        _print_selector_dry_run_selection(selection)

    for i, case in enumerate(cases, 1):
        print(f"\n  用例 {i}: {case['case_id']} - {case['title']}")
        for phase_name, steps_key in (
            ('pre_process', 'pre_process'),
            ('test_case', 'test_case'),
            ('post_process', 'post_process'),
        ):
            steps = case.get(steps_key) or []
            for j, step in enumerate(steps, 1):
                action = step.get('action', '')
                if not action:
                    continue
                model = step.get('model', '')
                data = step.get('data', '')
                print(f"    {phase_name}[{j}]: action={action}, model={model}, data={data}")
                if verbose and model:
                    model_info = model_parser.get_model(model)
                    if model_info:
                        print(f"      模型元素: {list(model_info.keys())}")
                    else:
                        print(f"      [警告] 模型 '{model}' 不存在")

    print(f"\n验证通过: {len(cases)} 个用例可执行")
    return 0


def _has_active_selector(selector_filters: Dict[str, Any]) -> bool:
    """判断 selector_filters 中是否有任何活跃的过滤条件。"""
    return any(
        selector_filters.get(k)
        for k in ("filter_tags", "filter_group", "exclude_tags", "filter_priority")
    )


def _print_selector_dry_run_selection(selection: Dict[str, List[Dict[str, Any]]]) -> None:
    """Print selector-based selection details for dry-run (no stale section)."""
    print(f"\n[Dry Run] Selector 选择:")

    print("  Selected:")
    for entry in selection.get('selected', []) or []:
        entry_type = entry.get('type')
        if entry_type == 'case':
            print(f"    case {entry.get('case_id')} ({entry.get('reason', '')})")
        elif entry_type == 'scenario':
            print(f"    case {entry.get('case_id')} scenario {entry.get('scenario_id')} ({entry.get('reason', '')})")
    if not selection.get('selected'):
        print("    (none)")

    print("  Skipped:")
    for entry in selection.get('skipped', []) or []:
        entry_type = entry.get('type')
        if entry_type == 'case':
            print(f"    case {entry.get('case_id')} ({entry.get('reason', '')})")
        elif entry_type == 'scenario':
            print(f"    case {entry.get('case_id')} scenario {entry.get('scenario_id')} ({entry.get('reason', '')})")
    if not selection.get('skipped'):
        print("    (none)")


def _print_plan_dry_run_selection(plan, selection) -> None:
    """Print explicit plan selection details for dry-run."""
    print(f"\n[Dry Run] 测试计划选择:")
    print(f"  Plan: {plan.get('id', '')} (kind={plan.get('kind', '')}, default_execute={plan.get('default_execute', '')})")

    print("  Selected:")
    for entry in selection.get('selected', []) or []:
        entry_type = entry.get('type')
        if entry_type == 'case':
            print(f"    case {entry.get('case_id')} ({entry.get('reason', '')})")
        elif entry_type == 'scenario':
            print(f"    case {entry.get('case_id')} scenario {entry.get('scenario_id')} ({entry.get('reason', '')})")
        elif entry_type == 'step':
            print(
                f"    case {entry.get('case_id')} scenario {entry.get('scenario_id')} "
                f"step {entry.get('step_no')} ({entry.get('reason', '')})"
            )
    if not selection.get('selected'):
        print("    (none)")

    print("  Skipped:")
    for entry in selection.get('skipped', []) or []:
        entry_type = entry.get('type')
        if entry_type == 'case':
            print(f"    case {entry.get('case_id')} ({entry.get('reason', '')})")
        elif entry_type == 'scenario':
            print(f"    case {entry.get('case_id')} scenario {entry.get('scenario_id')} ({entry.get('reason', '')})")
        elif entry_type == 'step':
            print(
                f"    case {entry.get('case_id')} scenario {entry.get('scenario_id')} "
                f"step {entry.get('step_no')} ({entry.get('reason', '')})"
            )
    if not selection.get('skipped'):
        print("    (none)")

    print("  Stale references:")
    for entry in selection.get('stale_references', []) or []:
        if entry.get('type') == 'case':
            print(f"    case {entry.get('case_id')} ({entry.get('reason', '')})")
        elif entry.get('type') == 'scenario':
            print(f"    case {entry.get('case_id')} scenario {entry.get('scenario_id')} ({entry.get('reason', '')})")
        elif entry.get('type') == 'step':
            print(
                f"    case {entry.get('case_id')} scenario {entry.get('scenario_id')} "
                f"step {entry.get('step_no')} ({entry.get('reason', '')})"
            )
    if not selection.get('stale_references'):
        print("    (none)")


def _handle_execute(case_path: Path, module_dir: Path, args, plan_path: Optional[Path] = None, selector_filters: Optional[Dict[str, Any]] = None) -> int:
    """实际执行测试用例"""
    try:
        from ..core.ski_executor import SKIExecutor
        from ..core.config_manager import ConfigManager
        from ..drivers.playwright_driver import PlaywrightDriver
        from ..core.json_formatter import JSONFormatter
        from ..core.runtime_control import RuntimeCommandQueue
    except ImportError:
        from core.ski_executor import SKIExecutor
        from core.config_manager import ConfigManager
        from drivers.playwright_driver import PlaywrightDriver
        from core.json_formatter import JSONFormatter
        from core.runtime_control import RuntimeCommandQueue
    import time

    headless = getattr(args, "headless", False)
    browser = getattr(args, "browser", "chromium")
    output_format = getattr(args, "output_format", "text")
    insert_steps = getattr(args, "insert_steps", None)

    # 使用已构建的 selector 过滤参数
    if selector_filters is None:
        selector_filters = _build_selector_filters(args)
    filter_tags = selector_filters["filter_tags"]
    filter_group = selector_filters["filter_group"]
    filter_priority = selector_filters["filter_priority"]
    exclude_tags = selector_filters["exclude_tags"]

    config = _apply_recording_args(ConfigManager(), args)

    def create_driver():
        return PlaywrightDriver(headless=headless, browser=browser)

    driver = create_driver()
    executor = None
    start_time = time.time()
    runtime_control = RuntimeCommandQueue() if insert_steps else None

    try:
        executor = SKIExecutor(
            str(case_path),
            driver,
            config=config,
            driver_factory=lambda: create_driver(),
            module_dir=str(module_dir),
            runtime_control=runtime_control,
        )
        executor.selector_filters = {
            "filter_tags": filter_tags,
            "filter_group": filter_group,
            "filter_priority": filter_priority,
            "exclude_tags": exclude_tags,
        }
        if plan_path is not None:
            executor.plan_path = str(plan_path)
        if getattr(args, "debug", False):
            executor.debug_mode = True

        # 处理插入步骤
        if insert_steps and runtime_control:
            steps = []
            for step_spec in insert_steps:
                parts = step_spec.split(',', 2)
                if len(parts) >= 1:
                    steps.append({
                        'action': parts[0].strip(),
                        'model': parts[1].strip() if len(parts) > 1 else '',
                        'data': parts[2].strip() if len(parts) > 2 else '',
                    })
            if steps:
                runtime_control.insert(steps)
                print(f"已插入 {len(steps)} 个动态步骤")

        if output_format == "text":
            print("-" * 60)

        results = executor.execute_all_cases(
            filter_tags=filter_tags,
            filter_priority=filter_priority,
            exclude_tags=exclude_tags,
        )
        duration = time.time() - start_time

        if output_format == "json":
            output = JSONFormatter.format_success(results, duration)
            print(JSONFormatter.to_json(output, pretty=True))
            return output["exit_code"]

        # Text format output
        print("-" * 60)
        total = len(results)
        passed = sum(1 for r in results if r.get('status', '').upper() == 'PASS')
        failed = sum(1 for r in results if r.get('status', '').upper() == 'FAIL')
        skipped = sum(1 for r in results if r.get('status', '').upper() == 'SKIP')

        print(f"执行完成: {passed}/{total} 通过, {failed} 失败" + (f", {skipped} 跳过" if skipped else ""))

        if failed > 0:
            print(f"\n失败用例:")
            for r in results:
                if r.get('status', '').upper() == 'FAIL':
                    print(f"  - {r.get('case_id')}: {r.get('error', '未知错误')}")

        if args.output:
            import json
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps({
                "summary": {"total": total, "passed": passed, "failed": failed},
                "results": results,
            }, indent=2, ensure_ascii=False))
            print(f"报告已保存: {args.output}")

        # --report html: 执行完毕后自动生成 HTML 报告
        report_format = getattr(args, "report", None)
        if report_format == "html":
            _generate_post_run_report(results, total, passed, failed, duration)

        return 0 if failed == 0 else 1

    except Exception as e:
        if output_format == "json":
            error_output = JSONFormatter.format_error(e)
            print(JSONFormatter.to_json(error_output, pretty=True), file=sys.stderr)
            return error_output["exit_code"]

        print(f"执行错误: {e}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback
            traceback.print_exc()
        return 1
    finally:
        if executor:
            executor.close()
        elif driver:
            try:
                driver.close()
            except Exception:
                pass


def _generate_post_run_report(results, total, passed, failed, duration):
    """执行后自动生成 HTML 报告（--report html 触发）

    报告生成失败不影响 run 主流程的退出码。
    """
    try:
        try:
            from .report import generate_html_from_run_results
        except ImportError:
            from rodski_cli.report import generate_html_from_run_results
        report_path = generate_html_from_run_results(
            results=results,
            total=total,
            passed=passed,
            failed=failed,
            duration=duration,
        )
        print(f"HTML 报告已生成: {report_path}")
    except Exception as e:
        print(f"警告: 报告生成失败: {e}", file=sys.stderr)
