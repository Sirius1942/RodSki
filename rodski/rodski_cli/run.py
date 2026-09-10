"""run 子命令 - 通过 SKIExecutor 执行测试用例（XML 版本）"""
import sys
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rodski")

# 需要浏览器驱动的 action 集合
_BROWSER_ACTIONS = frozenset({
    'navigate', 'click', 'type', 'evaluate', 'hover', 'screenshot',
    'get', 'select', 'upload', 'launch', 'double_click', 'right_click',
    'upload_file', 'clear', 'get_text', 'assert',
})


def _normalize_cdp_endpoint(value: Optional[str]) -> str:
    """把 --cdp 值归一为可 connect_over_cdp 的端点 URL。

    - ``:9222`` / ``localhost:9222`` → ``http://127.0.0.1:9222``
    - 已带 scheme（http/https）原样返回
    - 空值原样返回（由调用方按无 --cdp 处理）
    """
    value = (value or "").strip()
    if not value or "://" in value:
        return value
    host_port = value
    if host_port.startswith(":"):
        host_port = f"127.0.0.1{host_port}"
    else:
        host, _, port = host_port.rpartition(":")
        if not port.isdigit():
            # 只有主机名没有端口，补默认调试端口不适用，交给 connect 失败提示
            return f"http://{host_port}"
        if not host or host == "localhost":
            host = "127.0.0.1"
        host_port = f"{host}:{port}"
    return f"http://{host_port}"


def _model_driver_types(model_path: Optional[Path]) -> Dict[str, str]:
    if not model_path or not model_path.exists():
        return {}
    try:
        root = ET.parse(model_path).getroot()
    except ET.ParseError:
        return {}
    result: Dict[str, str] = {}
    for model in root.findall("model"):
        name = (model.get("name") or "").strip()
        if not name:
            continue
        model_type = (model.get("type") or "ui").strip()
        driver_type = (model.get("driver_type") or "").strip()
        if driver_type:
            result[name] = driver_type
        elif model_type in {"interface", "database"}:
            result[name] = model_type
        else:
            result[name] = "web"
    return result


def _is_mobile_app_target(value: str) -> bool:
    lower = (value or "").strip().lower()
    return lower.startswith("app://android/") or lower.startswith("app://ios/")


def _resolve_globalvalue_for_browser_scan(module_dir: Path, value: str) -> str:
    if not isinstance(value, str) or not value.startswith("GlobalValue."):
        return value
    parts = value.split(".", 2)
    if len(parts) != 3:
        return value
    _, group_name, var_name = parts
    globalvalue_path = module_dir / "data" / "globalvalue.xml"
    if not globalvalue_path.exists():
        return value
    try:
        root = ET.parse(globalvalue_path).getroot()
    except ET.ParseError:
        return value
    for group in root.findall("group"):
        if group.get("name") != group_name:
            continue
        for var in group.findall("var"):
            if var.get("name") == var_name:
                return var.get("value") or value
    return value


def _needs_browser(case_path: Path, model_path: Optional[Path] = None) -> bool:
    """扫描 case XML，判断是否有需要浏览器的步骤"""
    xml_files: List[Path] = []
    if case_path.is_dir():
        xml_files = list(case_path.glob("*.xml"))
    elif case_path.is_file():
        xml_files = [case_path]

    model_driver_types = _model_driver_types(model_path)
    module_dir = _resolve_module_dir(case_path)

    for xml_file in xml_files:
        try:
            root = ET.parse(xml_file).getroot()
            for step in root.iter('test_step'):
                action = (step.get('action') or '').strip().lower()
                if action not in _BROWSER_ACTIONS:
                    continue
                data_value = _resolve_globalvalue_for_browser_scan(module_dir, step.get("data") or "")
                if action == "navigate" and _is_mobile_app_target(data_value):
                    continue
                model_name = (step.get("model") or "").strip()
                driver_type = model_driver_types.get(model_name, "web") if model_name else "web"
                if driver_type in {"android", "ios", "mobile", "interface", "database"}:
                    continue
                if action == "launch" and driver_type in {"windows", "macos", "other"}:
                    continue
                if action in {"type", "verify", "get", "get_text", "clear"} and driver_type in {"windows", "macos", "other"}:
                    continue
                if action in _BROWSER_ACTIONS:
                    return True
        except ET.ParseError:
            pass
    return False


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
    parser.add_argument("--trace", action="store_true",
                        help="启用 observability，导出 trace.json（执行 trace 树 + 耗时/重试指标）")
    parser.add_argument("--coverage", action="store_true",
                        help="启用 JS 代码覆盖率采集（基于 Playwright page.coverage，仅 Chromium 支持）")
    parser.add_argument("--coverage-output", type=str, default=None, dest="coverage_output",
                        help="覆盖率报告输出路径（默认: 本次运行结果目录下的 coverage.json）")
    parser.add_argument("--insert-step", action="append", dest="insert_steps",
                        help="插入动态步骤 (格式: action,model,data)")
    parser.add_argument("--cdp", type=str, default=None, dest="cdp_endpoint",
                        help="附加到已启动的远程调试浏览器（如 --cdp :9222 或 http://127.0.0.1:9222），"
                             "复用其页面与登录态；适用于「暂停→Agent 接管→继续」工作流。"
                             "仅对 Web 用例生效，附加模式下 --headless/--browser 不生效")
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
    parser.add_argument("--no-compile", action="store_true", dest="no_compile",
                        help="压测模式：跳过预编译，直接使用已有 perf/*.py")
    parser.add_argument("--load-ui", action="store_true", dest="load_ui",
                        help="压测模式：启动 Locust Web UI")
    parser.add_argument("--platform", choices=["android", "ios"], default=None,
                        help="移动端平台（android/ios），覆盖 globalvalue.xml Mobile.Platform")
    parser.add_argument("--load-ui-port", type=int, default=8089, dest="load_ui_port",
                        help="压测 Web UI 端口 (默认: 8089)")
    parser.add_argument("--force-compliance", action="store_true", dest="force_compliance",
                        help="on_run_start 内置合规检查失败时显式跳过（目录结构缺失除外），跳过会留痕到日志")
    parser.add_argument("--roam", action="store_true",
                        help="对本次执行中满足三层开关的通过用例执行漫游测试")
    parser.add_argument("--roam-engine", dest="roam_engine_module", default=None,
                        metavar="MODULE_PATH",
                        help="漫游决策引擎模块路径（Python 文件），须导出 create_engine() 工厂函数")


def _get_plan_kind(plan_path) -> str:
    """从 plan XML 读取 kind 属性（不做完整解析），失败时返回 'suite'。"""
    try:
        return ET.parse(plan_path).getroot().get("kind") or "suite"
    except Exception:
        return "suite"


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


def _build_hook_context(
    case_path: Path,
    module_dir: Path,
    plan_path: Optional[Path],
    selector_filters: Dict[str, Any],
) -> Dict[str, Any]:
    """构建所有外部 hook 共享的版本、能力和本次运行上下文。"""
    try:
        from .capabilities import get_capabilities
    except ImportError:
        from rodski.rodski_cli.capabilities import get_capabilities

    capabilities = get_capabilities()
    context = dict(capabilities)
    context.update({
        "rodski_version": capabilities.get("version", "dev"),
        "case_path": str(case_path),
        "module_dir": str(module_dir),
        "plan_id": plan_path.stem if plan_path is not None else None,
        "plan_path": str(plan_path) if plan_path is not None else None,
        "selector_filters": selector_filters,
    })
    return context


def _default_compliance_audit() -> Dict[str, Any]:
    return {
        "passed": True,
        "failed_checks": [],
        "skipped": False,
        "skipped_checks": [],
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

    # 构建 selector 过滤参数。@plan_id 与 selector 互斥检查已归入下方 v8.2.0
    # on_run_start 合规检查聚合（run_compliance_checks 内的 plan_selector_conflict
    # 项），不再在此单独硬校验——这样该检查项与其余三项一致，可用 --force-compliance
    # 显式跳过；只有 directory_structure 检查不可跳过。默认行为（未加
    # --force-compliance 时冲突仍会阻断执行）与迭代前一致。
    selector_filters = _build_selector_filters(args)
    plan_path_str = str(plan_path) if plan_path else None

    # v8.2.0 Hooks 机制：hooks.json 加载 + on_session_start + on_run_start 合规检查
    try:
        from ..core.hooks_config import load_hooks_config
        from ..core.hooks_runner import run_external_hook
        from ..core.compliance_check import run_compliance_checks
        from ..core.exceptions import ComplianceCheckFailedError, InvalidConfigError
    except ImportError:
        from rodski.core.hooks_config import load_hooks_config
        from rodski.core.hooks_runner import run_external_hook
        from rodski.core.compliance_check import run_compliance_checks
        from rodski.core.exceptions import ComplianceCheckFailedError, InvalidConfigError

    try:
        hooks_config = load_hooks_config(module_dir)
    except InvalidConfigError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    hook_context = _build_hook_context(
        case_path=case_path,
        module_dir=module_dir,
        plan_path=plan_path,
        selector_filters=selector_filters,
    )

    if hooks_config.get("on_session_start"):
        decision = run_external_hook(
            "on_session_start",
            hook_context,
            hooks_config["on_session_start"],
        )
        if not decision.allow:
            print(f"错误: on_session_start hook 拒绝: {decision.reason}", file=sys.stderr)
            return 1

    force_compliance = getattr(args, "force_compliance", False)
    compliance_report = run_compliance_checks(
        case_path=str(case_path),
        module_dir=str(module_dir),
        plan_path=plan_path_str,
        selector_filters=selector_filters,
    )
    compliance_audit = compliance_report.to_dict()
    compliance_audit["skipped"] = bool(force_compliance and not compliance_report.passed)
    compliance_audit["skipped_checks"] = (
        list(compliance_report.failed_checks) if compliance_audit["skipped"] else []
    )
    if not compliance_report.passed:
        # 目录结构缺失是硬性前提（连基本文件都定位不到），--force-compliance 不能跳过
        directory_failure = any(
            c["check_name"] == "directory_structure" for c in compliance_report.failed_checks
        )
        if directory_failure or not force_compliance:
            try:
                raise ComplianceCheckFailedError(checks_failed=compliance_report.failed_checks)
            except ComplianceCheckFailedError as e:
                print(f"错误: {e}", file=sys.stderr)
                if not directory_failure:
                    print("提示: 可使用 --force-compliance 显式跳过（跳过会记录到日志）", file=sys.stderr)
                return 1
        else:
            names = ", ".join(c["check_name"] for c in compliance_report.failed_checks)
            logger.warning(f"[--force-compliance] 已跳过合规检查失败项: {names}")

    if hooks_config.get("on_run_start"):
        decision = run_external_hook(
            "on_run_start",
            {**hook_context, "compliance": compliance_audit},
            hooks_config["on_run_start"],
        )
        if not decision.allow:
            print(f"错误: on_run_start hook 拒绝: {decision.reason}", file=sys.stderr)
            return 1

    needs_browser = _needs_browser(case_path, model_path)

    print(f"用例路径: {case_path}")
    if plan_path is not None:
        print(f"测试计划: {plan_path}")
    print(f"模型文件: {model_path}")
    if needs_browser:
        print(f"浏览器: {args.browser}")
    else:
        print(f"执行模式: 接口 / 浏览器: 未启用")

    # 供 _handle_execute 内 on_case_failure/on_run_end 挂载点和 JSON 审计输出读取。
    # 这些属性仅用于同一次 handle() 调用内传递，不属于 argparse 的公开契约。
    args._hooks_config = hooks_config
    args._hook_context = hook_context
    args._compliance_audit = compliance_audit
    args._executor_hooks = {}

    if hooks_config.get("on_case_failure"):
        failure_specs = hooks_config["on_case_failure"]

        def _notify_case_failure(case, error, screenshot_path):
            decision = run_external_hook(
                "on_case_failure",
                {
                    **hook_context,
                    "case_id": case.get("case_id", ""),
                    "title": case.get("title", ""),
                    "description": case.get("description", ""),
                    "component_type": case.get("component_type", ""),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "screenshot_path": screenshot_path,
                },
                failure_specs,
            )
            if not decision.allow:
                logger.warning(
                    "on_case_failure hook 返回 deny；用例已失败，继续失败处理: %s",
                    decision.reason,
                )

        args._executor_hooks["on_case_failure"] = [_notify_case_failure]

    roam_engine_module = getattr(args, "roam_engine_module", None)
    if roam_engine_module and getattr(args, "roam", False):
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("_roam_engine_module", roam_engine_module)
        if _spec is None or _spec.loader is None:
            logger.error("--roam-engine: 无法加载模块文件 %s", roam_engine_module)
            sys.exit(1)
        _mod = _ilu.module_from_spec(_spec)
        try:
            _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
        except Exception as _exc:
            logger.error("--roam-engine: 加载模块 %s 失败: %s", roam_engine_module, _exc)
            sys.exit(1)
        _factory = getattr(_mod, "create_engine", None)
        if not callable(_factory):
            logger.error("--roam-engine: 模块 %s 未导出 create_engine() 工厂函数", roam_engine_module)
            sys.exit(1)
        _engine = _factory()
        args._executor_hooks.setdefault("on_case_pass_roam_ready", []).append(_engine)
        logger.info("--roam-engine: 已注册引擎 %s", type(_engine).__name__)

    if dry_run:
        return _handle_dry_run(case_path, model_path, verbose, plan_path=plan_path, selector_filters=selector_filters)

    if plan_path is not None:
        _plan_kind = _get_plan_kind(plan_path)
        if _plan_kind == "load":
            return _handle_load_run(plan_path, module_dir, args)

    return _handle_execute(case_path, module_dir, args, plan_path=plan_path, selector_filters=selector_filters, needs_browser=needs_browser)


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
        _validate_record_resolution(record_resolution)
        recording["video_size"] = record_resolution
    config.config["recording"] = recording
    return config


def _validate_record_resolution(value: str) -> None:
    """校验 --record-resolution 参数格式，无效时抛出 SystemExit。"""
    import re
    valid_presets = {"screen", "2k", "hd"}
    v = value.strip().lower()
    if v in valid_presets:
        return
    if re.match(r"^\d+x\d+$", v):
        return
    import sys
    print(
        f"错误: 无效的录制分辨率 '{value}'。\n"
        f"支持的格式: screen, 2k, hd, WxH（如 1920x1080）",
        file=sys.stderr,
    )
    raise SystemExit(1)


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
        from rodski.core.case_parser import CaseParser
        from rodski.core.model_parser import ModelParser
        from rodski.core.plan_parser import PlanParser
        from rodski.core.test_plan_selection import TestPlanSelection, compile_from_selector

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
    for k in ("filter_tags", "filter_group", "exclude_tags", "filter_priority"):
        v = selector_filters.get(k)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            if len(v) > 0:
                return True
        elif v:
            return True
    return False


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


def _handle_execute(case_path: Path, module_dir: Path, args, plan_path: Optional[Path] = None, selector_filters: Optional[Dict[str, Any]] = None, needs_browser: bool = True) -> int:
    """实际执行测试用例"""
    try:
        from ..core.ski_executor import SKIExecutor
        from ..core.diagnosis_engine import DiagnosisEngine
        from ..core.config_manager import ConfigManager
        from ..drivers.playwright_driver import PlaywrightDriver
        from ..core.json_formatter import JSONFormatter
        from ..core.runtime_control import RuntimeCommandQueue
    except ImportError:
        from rodski.core.ski_executor import SKIExecutor
        from rodski.core.diagnosis_engine import DiagnosisEngine
        from rodski.core.config_manager import ConfigManager
        from rodski.drivers.playwright_driver import PlaywrightDriver
        from rodski.core.json_formatter import JSONFormatter
        from rodski.core.runtime_control import RuntimeCommandQueue
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

    cdp_endpoint = getattr(args, "cdp_endpoint", None)

    # --coverage：每创建一个 web 驱动实例即开启采集，run 结束后统一 stop 并聚合导出
    enable_coverage = bool(getattr(args, "coverage", False))
    coverage_drivers: List[Any] = []

    def create_driver(driver_type: str = "web", **kwargs):
        if driver_type in ("", "web"):
            if not needs_browser:
                return None
            if cdp_endpoint:
                # CDP 附加模式：headless/browser 由远端浏览器决定，此处不生效
                endpoint = _normalize_cdp_endpoint(cdp_endpoint)
                print(f"附加模式: 连接远程调试浏览器 {endpoint}"
                      f"（headless={headless}, browser={browser} 不生效）")
                web_driver = PlaywrightDriver(cdp_endpoint=endpoint)
            else:
                web_driver = PlaywrightDriver(headless=headless, browser=browser)
            if enable_coverage and hasattr(web_driver, "start_js_coverage"):
                web_driver.start_js_coverage()
                coverage_drivers.append(web_driver)
            return web_driver
        try:
            from ..core.driver_factory import DriverFactory
        except ImportError:
            from core.driver_factory import DriverFactory
        return DriverFactory.get_driver(driver_type, **kwargs)

    driver = create_driver("web")
    executor = None
    start_time = time.time()
    runtime_control = RuntimeCommandQueue() if insert_steps else None

    # observability：--trace 显式开启，--report html 也顺带采集性能数据
    enable_trace = bool(getattr(args, "trace", False)) or getattr(args, "report", None) == "html"

    try:
        executor = SKIExecutor(
            str(case_path),
            driver,
            config=config,
            driver_factory=create_driver,
            module_dir=str(module_dir),
            runtime_control=runtime_control,
            enable_trace=enable_trace,
            hooks=getattr(args, "_executor_hooks", None),
            diagnosis_engine=DiagnosisEngine(),
        )
        executor.roam_enabled = bool(getattr(args, "roam", False))
        executor.roam_mode = getattr(args, "roam_mode", None) or "batch_just_passed"
        executor.roam_case_id = getattr(args, "roam_case_id", None)
        # --platform 覆盖：将 CLI 指定的平台注入 global_vars，
        # 使 keyword_engine._resolve_mobile_platform() 返回正确平台。
        # 同时自动合并平台专属 globalvalue 文件（如 globalvalue_ios.xml），
        # 覆盖 AppTarget / BundleId 等平台特有变量。
        cli_platform = getattr(args, "platform", None)
        if cli_platform:
            executor.global_vars.setdefault("Mobile", {})["Platform"] = cli_platform
            # 尝试加载平台专属 globalvalue 文件（优先级高于默认 globalvalue.xml）
            platform_gv_path = module_dir / "data" / f"globalvalue_{cli_platform}.xml"
            if platform_gv_path.exists():
                try:
                    from ..core.global_value_parser import GlobalValueParser as _GVP
                except ImportError:
                    from core.global_value_parser import GlobalValueParser as _GVP
                platform_vars = _GVP(str(platform_gv_path)).parse()
                # 深度合并：平台 globalvalue 的 group/var 覆盖默认值
                for group, vars_ in platform_vars.items():
                    executor.global_vars.setdefault(group, {}).update(vars_)
                logger.info(f"--platform 覆盖：加载 {platform_gv_path.name}，"
                            f"Mobile.AppTarget={executor.global_vars.get('Mobile',{}).get('AppTarget','')}")
            else:
                logger.info(f"--platform 覆盖：Mobile.Platform = {cli_platform}"
                            f"（未找到 {platform_gv_path.name}，仅覆盖 Platform 字段）")
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

        # v8.2.0 Hooks 机制：on_run_end 外部命令 hook（不影响退出码，仅通知）
        _hooks_cfg = getattr(args, "_hooks_config", None)
        if _hooks_cfg and _hooks_cfg.get("on_run_end"):
            try:
                from ..core.hooks_runner import run_external_hook
            except ImportError:
                from rodski.core.hooks_runner import run_external_hook
            _total = len(results)
            _passed = sum(1 for r in results if r.get('status', '').upper() == 'PASS')
            _failed = sum(1 for r in results if r.get('status', '').upper() == 'FAIL')
            run_external_hook(
                "on_run_end",
                {
                    **getattr(args, "_hook_context", {}),
                    "case_path": str(case_path),
                    "total": _total,
                    "passed": _passed,
                    "failed": _failed,
                    "skipped": sum(
                        1 for r in results if r.get('status', '').upper() == 'SKIP'
                    ),
                    "duration": duration,
                    "status": "passed" if _failed == 0 else "failed",
                    "compliance": getattr(
                        args, "_compliance_audit", _default_compliance_audit()
                    ),
                },
                _hooks_cfg["on_run_end"],
            )

        # observability：导出 trace.json 到本次 run 结果目录
        if enable_trace:
            _export_trace(executor, output_format)

        # --coverage：停止采集并导出 coverage.json 到本次 run 结果目录
        if enable_coverage:
            _export_coverage(executor, coverage_drivers, getattr(args, "coverage_output", None), output_format)

        if output_format == "json":
            output = JSONFormatter.format_success(results, duration)
            output["compliance"] = getattr(
                args, "_compliance_audit", _default_compliance_audit()
            )
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
            perf_metrics = None
            if enable_trace and getattr(executor, "_metrics", None) is not None:
                perf_metrics = executor._metrics.get_summary()
            # 报告写入本次 run 结果目录，使 screenshots/ recordings/ 相对路径可解析
            run_dir = getattr(getattr(executor, "result_writer", None), "current_run_dir", None)
            _generate_post_run_report(results, total, passed, failed, duration, perf_metrics,
                                      output_dir=str(run_dir) if run_dir else None)

        return 0 if failed == 0 else 1

    except Exception as e:
        if output_format == "json":
            error_output = JSONFormatter.format_error(e)
            error_output["compliance"] = getattr(
                args, "_compliance_audit", _default_compliance_audit()
            )
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


def _export_trace(executor, output_format="text"):
    """导出 observability trace + metrics 到本次 run 结果目录的 trace.json。

    导出失败不影响 run 主流程退出码。
    """
    try:
        try:
            from observability import JsonExporter
        except ImportError:
            from rodski.observability import JsonExporter
        tracer = getattr(executor, "_tracer", None)
        metrics = getattr(executor, "_metrics", None)
        if tracer is None:
            return
        run_dir = getattr(getattr(executor, "result_writer", None), "current_run_dir", None)
        if not run_dir:
            return
        out_path = str(Path(run_dir) / "trace.json")
        JsonExporter.export_to_file(out_path, tracer=tracer, collector=metrics)
        if output_format == "text":
            print(f"trace 已导出: {out_path}")
    except Exception as e:
        print(f"警告: trace 导出失败: {e}", file=sys.stderr)


def _export_coverage(executor, coverage_drivers: List[Any], coverage_output: Optional[str], output_format="text"):
    """停止 JS 覆盖率采集，聚合所有驱动实例的结果并导出到 coverage.json。

    - 逐个驱动调用 stop_js_coverage()，聚合原始 entry 列表
    - 计算每个文件的覆盖率百分比及整体平均值
    - 默认写入本次 run 结果目录下的 coverage.json，--coverage-output 可覆盖路径

    导出失败不影响 run 主流程退出码。
    """
    try:
        raw_entries: List[Dict[str, Any]] = []
        for web_driver in coverage_drivers:
            stop_fn = getattr(web_driver, "stop_js_coverage", None)
            if stop_fn is None:
                continue
            try:
                raw_entries.extend(stop_fn() or [])
            except Exception as e:
                logger.warning(f"停止覆盖率采集失败: {e}")

        files = []
        total_pct = 0.0
        for entry in raw_entries:
            source = entry.get("source") if entry.get("source") is not None else entry.get("text")
            if not source:
                continue
            total_bytes = len(source)
            if total_bytes == 0:
                continue
            used_bytes = sum(
                max(0, r.get("end", 0) - r.get("start", 0))
                for r in entry.get("ranges", []) or []
            )
            covered_pct = used_bytes / total_bytes * 100
            total_pct += covered_pct
            files.append({
                "url": entry.get("url", ""),
                "covered_pct": round(covered_pct, 1),
                "used_bytes": used_bytes,
                "total_bytes": total_bytes,
            })

        report = {
            "summary": {
                "total_files": len(files),
                "average_coverage_pct": round(total_pct / len(files), 1) if files else 0.0,
            },
            "files": files,
        }

        if coverage_output:
            out_path = Path(coverage_output)
        else:
            run_dir = getattr(getattr(executor, "result_writer", None), "current_run_dir", None)
            if not run_dir:
                return
            out_path = Path(run_dir) / "coverage.json"

        out_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        if output_format == "text":
            print(f"覆盖率报告已导出: {out_path} (平均覆盖率: {report['summary']['average_coverage_pct']}%)")
    except Exception as e:
        print(f"警告: 覆盖率导出失败: {e}", file=sys.stderr)


def _print_load_summary(stats, elapsed: float = 0) -> None:
    """将压测摘要指标打印到终端。"""
    data = stats.summary()
    total_req   = data.get("total_requests", 0)
    error_rate  = data.get("error_rate_pct", 0.0)
    rps_avg     = data.get("rps_avg", 0.0)
    p50         = data.get("p50_ms", 0)
    p95         = data.get("p95_ms", 0)
    p99         = data.get("p99_ms", 0)
    print("\n" + "=" * 60)
    print("压测结果摘要")
    print("=" * 60)
    print(f"  总请求数   : {total_req}")
    print(f"  错误率     : {error_rate:.2f}%")
    print(f"  平均 RPS   : {rps_avg:.2f}")
    print(f"  P50 延迟   : {p50} ms")
    print(f"  P95 延迟   : {p95} ms")
    print(f"  P99 延迟   : {p99} ms")
    if elapsed:
        print(f"  总耗时     : {elapsed:.1f}s")
    print("=" * 60)


def _handle_load_run(plan_path: Path, module_dir: Path, args) -> int:
    """执行压测计划（plan kind=load）。"""
    # 1. 检查 locust 是否安装
    try:
        import locust  # noqa: F401
    except ImportError:
        print("错误: 压测模式需要 locust，请先安装：", file=sys.stderr)
        print("  pip install locust", file=sys.stderr)
        return 1

    import time

    try:
        from ..core.plan_parser import PlanParser
        from ..load.context import SharedLoadContext
        from ..load.compiler import LoadCompiler
        from ..load.locust_engine import LocustLoadEngine
        from ..load.result_writer import LoadResultWriter
    except ImportError:
        try:
            from rodski.core.plan_parser import PlanParser  # type: ignore[no-redef]
            from rodski.load.context import SharedLoadContext  # type: ignore[no-redef]
            from rodski.load.compiler import LoadCompiler  # type: ignore[no-redef]
            from rodski.load.locust_engine import LocustLoadEngine  # type: ignore[no-redef]
            from rodski.load.result_writer import LoadResultWriter  # type: ignore[no-redef]
        except ImportError:
            from rodski.core.plan_parser import PlanParser  # type: ignore[no-redef]
            from load.context import SharedLoadContext  # type: ignore[no-redef]
            from load.compiler import LoadCompiler  # type: ignore[no-redef]
            from load.locust_engine import LocustLoadEngine  # type: ignore[no-redef]
            from load.result_writer import LoadResultWriter  # type: ignore[no-redef]

    # 2. 解析 plan
    try:
        parser = PlanParser(str(plan_path))
        plan = parser.parse_plan()
    except Exception as e:
        print(f"错误: 压测计划解析失败: {e}", file=sys.stderr)
        return 1

    # 3. 构建共享上下文
    try:
        shared_ctx = SharedLoadContext.build(module_dir)
    except Exception as e:
        print(f"错误: 上下文构建失败: {e}", file=sys.stderr)
        return 1

    # 4. 预编译（可跳过）
    no_compile = getattr(args, "no_compile", False)
    if not no_compile:
        try:
            perf_dir = module_dir / "perf"
            compiler = LoadCompiler(shared_ctx, plan, perf_dir)
            compiler.compile_if_needed(
                plan_path=plan_path,
                case_paths=list((module_dir / "case").glob("*.xml")) if (module_dir / "case").is_dir() else [],
                model_path=module_dir / "model" / "model.xml",
                data_path=module_dir / "data" / "data.sqlite",
            )
        except Exception as e:
            print(f"警告: 预编译失败，继续执行: {e}", file=sys.stderr)

    # 5. 执行压测
    enable_web_ui = getattr(args, "load_ui", False)
    web_ui_port   = getattr(args, "load_ui_port", 8089)

    profile = plan.get("load_profile", {})
    concurrency = profile.get("concurrency", "?")
    duration    = profile.get("duration_seconds", "?")
    mode_str    = "预编译" if not no_compile else "解释"
    print(f"\n压测计划: {plan.get('id')} | {concurrency} VU × {duration}s | 模式: {mode_str}")
    if enable_web_ui:
        print(f"监控界面: http://127.0.0.1:{web_ui_port}  (启动中...)")
    print("启动压测引擎...")

    start_time = time.time()
    try:
        engine = LocustLoadEngine(
            plan,
            shared_ctx,
            enable_web_ui=enable_web_ui,
            web_ui_host="127.0.0.1",
            web_ui_port=web_ui_port,
        )
        stats = engine.run()
    except Exception as e:
        print(f"错误: 压测执行失败: {e}", file=sys.stderr)
        return 1
    elapsed = time.time() - start_time

    # 6. 写结果
    try:
        writer = LoadResultWriter()
        result_path = writer.write(stats, plan, module_dir)
        print(f"压测结果已保存: {result_path}")
    except Exception as e:
        print(f"警告: 结果写入失败: {e}", file=sys.stderr)

    # 7. 打印摘要
    _print_load_summary(stats, elapsed=elapsed)

    # 8. 错误率 > 5% 返回 1
    error_rate = stats.summary().get("error_rate_pct", 0.0)
    return 1 if error_rate > 5.0 else 0


def _generate_post_run_report(results, total, passed, failed, duration, metrics=None, output_dir=None):
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
            metrics=metrics,
            output_dir=output_dir,
        )
        print(f"HTML 报告已生成: {report_path}")
    except Exception as e:
        print(f"警告: 报告生成失败: {e}", file=sys.stderr)
