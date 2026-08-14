"""SKI 执行引擎 - 完整的测试用例执行器

基于 XML 用例文件和目录结构执行测试。

每个 case 为三阶段（`pre_process` → `test_case` → `post_process`），每阶段内为多条
`test_step`。用例阶段失败时仍会执行后处理（清理/关闭）。

目录结构约束：
    product/
    └── {测试项目}/
        └── {测试模块}/
            ├── case/       ← case XML 文件
            ├── model/      ← model.xml
            ├── fun/        ← 代码工程目录
            ├── data/       ← 数据 XML + globalvalue.xml
            └── result/     ← 测试结果 XML
"""
import logging
import re
import time
import copy
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Deque, Set, Mapping, Tuple
from .model_parser import ModelParser
from .data_table_parser import DataTableParser
from .global_value_parser import GlobalValueParser
from .case_parser import CaseParser
from .plan_parser import PlanParser
from .test_plan_selection import TestPlanSelection
from .result_writer import ResultWriter, write_execution_summary
from .config_manager import ConfigManager
try:
    from ..data.data_resolver import DataResolver
    from ..drivers.base_driver import BaseDriver
except ImportError:
    from rodski.data.data_resolver import DataResolver
    from rodski.drivers.base_driver import BaseDriver
from .keyword_engine import KeywordEngine
from .dynamic_executor import DynamicExecutor

from .exceptions import (
    DriverStoppedError,
    AssertionFailedError,
    RoamCaseNotFoundError,
    RoamNotEligibleError,
    is_critical_error,
)
from .roam import (
    RoamBudget,
    RoamSessionGuard,
    STOP_MANUAL,
    STOP_NO_HANDLER,
    TestMapStore,
)
from .runtime_control import (
    BaseRuntimeControl,
    GracefulRunTermination,
    ForceRunTermination,
)

logger = logging.getLogger("rodski")


def resolve_module_dir(case_path: Path) -> Path:
    """从 case 文件/目录路径推导测试模块目录

    约束：case 文件位于 {module_dir}/case/ 下
    """
    if case_path.is_file():
        return case_path.parent.parent
    elif case_path.is_dir() and case_path.name == 'case':
        return case_path.parent
    return case_path


class SKIExecutor:
    """SKI 测试执行引擎

    支持功能:
    - XML 格式用例解析和执行
    - 基于目录结构的文件自动发现
    - 数据驱动测试
    - 失败自动截图
    - 结果输出到 XML
    - 支持两种用例执行模式:
      1. 独立模式: 每个用例有 close，执行完后关闭浏览器，下一个用例重新启动
      2. 共享模式: 用例没有 close，后续用例复用同一个浏览器 session
    """

    # 驱动级用例录像后端（共用同一套分段机器，区别仅在标识与产物格式）
    _DRIVER_RECORDING_BACKENDS = ("playwright", "appium")

    def __init__(
        self,
        case_path: str,
        driver: BaseDriver,
        config: Optional[ConfigManager] = None,
        driver_factory: Optional[Callable[[], BaseDriver]] = None,
        module_dir: Optional[str] = None,
        runtime_control: Optional[BaseRuntimeControl] = None,
        report_collector=None,
        enable_trace: bool = False,
        hooks: Optional[Dict[str, List[Callable]]] = None,
        diagnosis_engine: Optional[Any] = None,
    ):
        """初始化 SKI 执行器

        Args:
            case_path: case XML 文件路径或 case/ 目录路径
            driver: 驱动实例
            config: 配置管理器实例（可选）
            driver_factory: 驱动工厂函数（可选）
            module_dir: 测试模块目录路径（可选，自动推导）
            runtime_control: 运行时控制队列（暂停/插入/终止）；默认无操作
            hooks: v8.2.0 Hooks 机制进程内回调，形如
                {"before_keyword": [...], "after_keyword": [...], "on_case_failure": [...]}；
                不传则为空字典，行为与现状完全一致
            diagnosis_engine: DiagnosisEngine 实例（可选）；配置后 case 失败时
                自动调用 diagnose()，结果写入 report_collector（若存在）
        """
        self.case_path = Path(case_path).expanduser().resolve()
        self.driver = driver
        self.driver_factory = driver_factory
        self._driver_closed = False

        # 推导测试模块目录（必须为绝对路径，否则 run/subprocess 与 DB 相对路径会错位）
        if module_dir:
            self.module_dir = Path(module_dir).expanduser().resolve()
        else:
            self.module_dir = resolve_module_dir(self.case_path).resolve()

        # 标准子目录
        self.model_dir = self.module_dir / "model"
        self.data_dir = self.module_dir / "data"
        self.fun_dir = self.module_dir / "fun"
        self.result_dir = self.module_dir / "result"

        # 关键文件路径
        self.model_file = self.model_dir / "model.xml"
        self.globalvalue_file = self.data_dir / "globalvalue.xml"

        # 加载配置
        self.config = config or ConfigManager()
        self.auto_screenshot = self.config.get("auto_screenshot_on_failure", True)
        self.auto_screenshot_on_step = self.config.get("auto_screenshot_on_step", True)
        self._screenshot_dir_base = Path(self.config.get("screenshot_dir", "screenshots"))
        self.recording_config = dict(self.config.get("recording", {}) or {})
        self.recording_enabled = bool(self.config.get("recording.enabled", False))
        self._screen_recorder = None
        self._active_recording_backend: Optional[str] = None
        self._current_recording_path: Optional[str] = None
        self._recording_driver = None
        self._recording_segments: List[Dict[str, Any]] = []
        self._recording_segment_index = 0
        self._case_recording_active = False
        self._recording_case_id: Optional[str] = None
        self._recording_output_dir: Optional[Path] = None
        self._recording_video_size: Optional[str] = None
        self._current_scenario_id: Optional[str] = None
        self._current_scenario_title: Optional[str] = None

        # 初始化解析器
        self.model_parser = ModelParser(str(self.model_file)) if self.model_file.exists() else None
        self.data_manager = DataTableParser(str(self.data_dir))
        self.data_manager.parse_all_tables()
        self.global_parser = GlobalValueParser(str(self.globalvalue_file))
        self.global_vars = self.global_parser.parse()
        self.case_parser = CaseParser(str(self.case_path))

        # 读取默认等待时间
        default_wait_str = self.global_vars.get('DefaultValue', {}).get('WaitTime', '0')
        try:
            self.default_wait_time = float(default_wait_str)
        except (ValueError, TypeError):
            self.default_wait_time = 0.0

        # 初始化关键字引擎和数据解析器
        self.keyword_engine = KeywordEngine(
            driver,
            self.data_dir,
            model_parser=self.model_parser,
            data_manager=self.data_manager,
            global_vars=self.global_vars,
            case_file=str(self.case_path),
            driver_factory=self.driver_factory,
            module_dir=str(self.module_dir),
        )
        self.data_resolver = DataResolver(
            data_manager=self.data_manager,
            global_vars=self.global_vars,
            return_provider=self.keyword_engine.get_return
        )
        self.keyword_engine.data_resolver = self.data_resolver

        # 初始化动态执行器（与 keyword_engine 共享 RuntimeContext.history）
        self.dynamic_executor = DynamicExecutor(
            self.data_resolver,
            return_values=self.keyword_engine._context.history,
        )

        # 连接关键字引擎的变量存储到动态执行器
        self.keyword_engine._dynamic_executor = self.dynamic_executor

        # 初始化结果写入器
        self.result_writer = ResultWriter(str(self.result_dir))

        self.runtime_control: BaseRuntimeControl = runtime_control or BaseRuntimeControl()
        self._runtime_stopped_graceful = False

        # 报告收集器（可选）：不影响现有逻辑
        self.report_collector = report_collector

        # Observability（可选）：启用后在用例/步骤边界生成 trace span，
        # 并在关键字引擎层记录耗时/重试指标。默认关闭，不影响现有逻辑。
        self.enable_trace = enable_trace
        self._tracer = None
        self._metrics = None
        if enable_trace:
            try:
                from observability import get_tracer, MetricsCollector
            except ImportError:
                from rodski.observability import get_tracer, MetricsCollector
            self._tracer = get_tracer()
            self._metrics = MetricsCollector.get_instance()
            self._tracer.reset()
            self._metrics.reset()
            # 关键字引擎共享同一 tracer / metrics 收集器
            self.keyword_engine._metrics = self._metrics
            self.keyword_engine._tracer = self._tracer

        # 录像懒启动：移动端/桌面端 driver 是懒加载的（首个相关关键字才创建），
        # 注册回调，待真实 driver 就绪后再启动用例录像。
        self.keyword_engine.on_mobile_driver_created = self._on_mobile_driver_created

        # v8.2.0 Hooks 机制：进程内回调接线。hooks=None 时 self._hooks={}，
        # 各事件列表默认为空，行为与迭代前完全一致。
        self._hooks: Dict[str, List[Callable]] = hooks or {}
        self.keyword_engine.before_keyword_hooks = list(self._hooks.get("before_keyword", []))
        self.keyword_engine.after_keyword_hooks = list(self._hooks.get("after_keyword", []))
        self._diagnosis_engine = diagnosis_engine

        # 漫游默认关闭。CLI 在构造后设置这三个执行意图；决策器仍通过
        # on_case_pass_roam_ready hook 注入，不增加平行回调通道。
        self.roam_enabled = False
        self.roam_mode = "batch_just_passed"
        self.roam_case_id: Optional[str] = None

    def _on_mobile_driver_created(self, driver_type: str, driver) -> None:
        """移动端/桌面端 driver 就绪回调：补启动用例录像。

        移动端 self.driver 初始为 None（web 占位未创建），driver 在首个
        navigate/type 时才由 KeywordEngine 懒加载。此处把执行器的 driver 指向
        真实 driver，并在录像已启用但尚未开始时补启动当前用例的录像分段。
        """
        # 让录像层（基于 self.driver）能看到真实的活跃 driver
        if self.driver is None or getattr(self.driver, "recording_backend", None) is None:
            self.driver = driver
        if not getattr(self, "recording_enabled", False):
            return
        # 已在录像中（分段进行中）则无需重复启动
        if getattr(self, "_active_recording_backend", None):
            return
        case_id = getattr(self, "_current_case_id", None)
        if not case_id:
            return
        try:
            started = self._start_case_recording(case_id)
            if started:
                logger.info(f"录像已懒启动（driver={driver_type}）: {started}")
        except Exception as e:
            logger.warning(f"录像懒启动失败: {e}")
    def _ensure_driver_alive(self) -> None:
        """确保驱动可用，如果驱动已关闭则重新创建"""
        if self._driver_closed:
            if self.driver_factory:
                logger.info("驱动已关闭，重新创建驱动...")
                self.driver = self.driver_factory()
                self._driver_closed = False

                self.keyword_engine = KeywordEngine(
                    self.driver,
                    self.data_dir,
                    model_parser=self.model_parser,
                    data_manager=self.data_manager,
                    global_vars=self.global_vars,
                    case_file=str(self.case_path),
                    driver_factory=self.driver_factory,
                    module_dir=str(self.module_dir),
                )
                self.data_resolver.return_provider = self.keyword_engine.get_return
                self.keyword_engine.data_resolver = self.data_resolver
                self.keyword_engine.before_keyword_hooks = list(
                    getattr(self, "_hooks", {}).get("before_keyword", [])
                )
                self.keyword_engine.after_keyword_hooks = list(
                    getattr(self, "_hooks", {}).get("after_keyword", [])
                )
                self._set_keyword_recording_path(getattr(self, "_current_recording_path", None))

                # observability：重建的关键字引擎需重新注入 tracer / metrics，
                # 否则后续用例的 keyword span / 指标会丢失
                if getattr(self, "_tracer", None) is not None:
                    self.keyword_engine._tracer = self._tracer
                    self.keyword_engine._metrics = self._metrics

                # 录像懒启动回调同样需要重新注入，否则后续用例的移动端录像不启动
                self.keyword_engine.on_mobile_driver_created = self._on_mobile_driver_created

                logger.info("驱动重新创建成功")
            else:
                raise DriverStoppedError(
                    "驱动已关闭且未提供 driver_factory，无法重新创建驱动"
                )

    def execute_all_cases(
        self,
        filter_tags: Optional[List[str]] = None,
        filter_priority: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
    ):
        """执行所有用例，完成后批量回填结果

        Args:
            filter_tags: 仅执行包含指定 tag 的用例（OR 匹配，任一命中即可）
            filter_priority: 仅执行指定优先级的用例（如 ['P0', 'P1']）
            exclude_tags: 排除包含指定 tag 的用例
        """
        cases = self.case_parser.parse_cases()

        roam_case_id = getattr(self, 'roam_case_id', None)
        if roam_case_id:
            matched_cases = [case for case in cases if case.get('case_id') == roam_case_id]
            if not matched_cases:
                raise RoamCaseNotFoundError(
                    case_id=roam_case_id,
                    search_path=str(self.case_path),
                )
            cases = matched_cases

            if getattr(self, 'roam_mode', '') == 'single_case':
                reasons = self._roam_eligibility_reasons(cases[0])
                if reasons:
                    raise RoamNotEligibleError(case_id=roam_case_id, reasons=reasons)

        cases = self._filter_cases(cases, filter_tags, filter_priority, exclude_tags)
        plan_selection = self._compile_plan_selection(cases)
        cases, plan_case_skips = self._apply_plan_selection(cases, plan_selection)

        # Debug mode: 如果启用了 --debug 且 plan kind 是 scenario_debug/step_debug，走调试执行路径
        if getattr(self, 'debug_mode', False) and hasattr(self, 'plan'):
            plan_kind = self.plan.get('kind', '')
            if plan_kind in ('scenario_debug', 'step_debug'):
                return self._execute_debug_plan(cases, plan_case_skips)
        results = []
        case_count = 0
        total_cases = len(cases)

        # 初始化结果目录（用于步骤截图）
        self.result_writer._init_run_dir()

        # 报告收集器：开始执行
        if getattr(self, 'report_collector', None):
            self.report_collector.start_run()

        # Observability：开启 run 级根 span
        if self._tracer is not None:
            self._tracer.start_span("run", total_cases=total_cases)

        for case in cases:
            case_count += 1
            case_skip = plan_case_skips.get(case.get('case_id', ''))
            if case_skip:
                results.append(self._case_result_skipped(case, case_skip))
                logger.info(f"  SKIP ({case_skip})")
                continue
            if self._driver_closed:
                logger.info(f"用例 {case_count}/{total_cases}: 驱动已关闭，重新创建浏览器...")
                try:
                    self._ensure_driver_alive()
                    logger.info(f"新浏览器已启动")
                except DriverStoppedError as e:
                    logger.error(f"无法重新创建驱动: {e}")
                    results.append({
                        'case_id': case['case_id'],
                        'title': case.get('title', ''),
                        'status': 'FAIL',
                        'execution_time': 0,
                        'error': f'驱动不可用: {str(e)}',
                        'screenshot_path': '',
                    })
                    continue

            logger.info(f"执行用例 {case_count}/{total_cases}: {case['case_id']} - {case['title']}")
            if self._tracer is not None:
                self._tracer.start_span(
                    "case",
                    case_id=case.get('case_id', ''),
                    title=case.get('title', ''),
                )
            try:
                result = self.execute_case(case)
                results.append(result)

                st = result.get('status', '').upper()
                if st == 'PASS':
                    logger.info(f"  PASS ({result['execution_time']}s)")
                elif st == 'SKIP':
                    logger.info(f"  SKIP ({result['execution_time']}s)")
                else:
                    logger.info(f"  FAIL ({result['execution_time']}s)")
                if result.get('error'):
                    logger.error(f"  错误: {result['error']}")
                if self._tracer is not None:
                    self._tracer.end_span("ok" if st == 'PASS' else "error")

            except DriverStoppedError as e:
                logger.critical(f"驱动已停止: {e}")
                if self._tracer is not None:
                    self._tracer.end_span("error")
                results.append({
                    'case_id': case['case_id'],
                    'title': case.get('title', ''),
                    'status': 'FAIL',
                    'execution_time': 0,
                    'error': f'驱动已停止: {str(e)}',
                    'screenshot_path': '',
                })

        self.result_writer.write_results(results)

        # Observability：结束 run 级根 span
        if self._tracer is not None:
            self._tracer.end_span("ok")

        # 报告收集器：结束执行
        if getattr(self, 'report_collector', None):
            self.report_collector.end_run()

        return results

    def _compile_plan_selection(self, cases: List[Dict[str, Any]]) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """Parse ``self.plan_path`` or compile selector filters into plan selection metadata."""
        plan_path = getattr(self, 'plan_path', None)
        if plan_path:
            parser = PlanParser(str(plan_path))
            parse = getattr(parser, 'parse', None) or parser.parse_plan
            plan = parse()
            selection = TestPlanSelection(cases, plan).select()
            self.plan = plan
            self.plan_selection_result = selection
            return selection

        # Selector mode: compile from CLI filters if any are active
        selector_filters = getattr(self, 'selector_filters', None) or {}
        has_active = any(
            selector_filters.get(k)
            for k in ("filter_tags", "filter_group", "exclude_tags", "filter_priority")
        )
        if not has_active:
            self.plan_selection_result = None
            return None

        from .test_plan_selection import compile_from_selector
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
        self.plan_selection_result = selection
        return selection

    def _roam_eligibility_reasons(self, case: Mapping[str, Any]) -> List[str]:
        """返回未满足的三层漫游开关；空列表表示可进入漫游阶段。"""
        reasons: List[str] = []
        roam_config = self.global_vars.get('Roam', {}) or {}
        if str(roam_config.get('Enabled', '否')).strip() != '是':
            reasons.append('Roam.Enabled != 是')
        if str(case.get('roam', '否')).strip() != '是':
            reasons.append('case.roam != 是')
        if not bool(getattr(self, 'roam_enabled', False)):
            reasons.append('未通过 --roam 或 rodski roam 显式启用')
        return reasons

    def _resolve_roam_engine(self, context: Dict[str, Any]):
        """通过 on_case_pass_roam_ready 获取覆盖实现，否则使用规则型默认引擎。

        handler 可返回带 next_action() 的 engine，也可直接作为 next_action
        callable 返回 decision dict。后者便于很小的 Python hook，无需定义类。
        """
        first_decision = None
        for handler in getattr(self, '_hooks', {}).get('on_case_pass_roam_ready', []):
            try:
                if hasattr(handler, 'next_action'):
                    return handler, first_decision
                if not callable(handler):
                    logger.warning('on_case_pass_roam_ready handler 不可调用，已忽略: %r', handler)
                    continue
                candidate = handler(context)
                if hasattr(candidate, 'next_action'):
                    return candidate, first_decision
                if isinstance(candidate, Mapping):
                    first_decision = dict(candidate)
                    return handler, first_decision
            except Exception as exc:
                logger.warning('on_case_pass_roam_ready handler 异常，已跳过该 handler: %s', exc)

        # 无内置 fallback：core 不含决策逻辑
        return None, first_decision

    def _run_roam_session(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """在 test_case 与 post_process 之间同步执行一次漫游会话。"""
        roam_config = self.global_vars.get('Roam', {}) or {}
        guard = RoamSessionGuard(RoamBudget.from_mapping(roam_config))
        triggered_by = getattr(self, 'roam_mode', None) or 'batch_just_passed'
        findings: List[Dict[str, Any]] = []
        history: List[Dict[str, Any]] = []
        map_nodes: List[Dict[str, Any]] = []
        map_edges: List[Dict[str, Any]] = []
        map_store = TestMapStore(self.module_dir)

        try:
            test_map = map_store.load()
        except Exception as exc:
            logger.warning('读取测试地图失败，本次会话使用空地图且不覆盖原文件: %s', exc)
            test_map = map_store.empty_map()

        case_id = case.get('case_id', '')

        # 采集真实页面证据（截图、URL、页面状态）
        screenshot_path = self._take_roam_screenshot(case_id, 'start') or ''
        current_url: Optional[str] = None
        page_title: Optional[str] = None
        page_ready = False

        _driver = getattr(self, 'driver', None)
        if _driver and hasattr(_driver, 'current_url'):
            try:
                current_url = _driver.current_url()
            except Exception:
                pass

        if _driver and getattr(_driver, 'page', None):
            try:
                page_title = _driver.page.title()
            except Exception:
                pass
            try:
                state = _driver.page.evaluate("document.readyState")
                page_ready = (state == "complete")
            except Exception:
                pass

        context: Dict[str, Any] = {
            'case_id': case_id,
            'case_title': case.get('title', ''),
            'case_description': case.get('description', ''),
            'original_steps': list(case.get('test_case') or []),
            'model_elements': copy.deepcopy(
                getattr(self.model_parser, 'models', {}) if self.model_parser else {}
            ),
            'screenshot_path': screenshot_path,
            'current_url': current_url,
            'page_identity': {
                'url': current_url,
                'title': page_title,
                'ready': page_ready,
            } if current_url is not None else None,
            'ax_tree': None,
            'driver_type': 'web',
            'history': history,
            'test_map_excerpt': test_map,
            'budget': dict(roam_config),
            'triggered_by': triggered_by,
        }
        engine, first_decision = self._resolve_roam_engine(context)
        if engine is None:
            guard.finish(STOP_NO_HANDLER)
            return guard.build_summary(
                base_case_id=case.get('case_id', ''),
                triggered_by=triggered_by,
                findings=findings,
            )

        while not guard.check_budget():
            context['history'] = list(history)
            context['seen_action_hashes'] = guard.seen_action_hashes
            try:
                if first_decision is not None:
                    decision = first_decision
                    first_decision = None
                elif hasattr(engine, 'next_action'):
                    decision = engine.next_action(context)
                else:
                    decision = engine(context)
                if not isinstance(decision, Mapping):
                    raise TypeError('漫游决策器必须返回 dict')
                decision = dict(decision)
            except Exception as exc:
                logger.warning('漫游决策失败，结束本次会话: %s', exc)
                findings.append(self._roam_failure_finding(case, exc, 'decision'))
                guard.finish(STOP_MANUAL)
                break

            usage = decision.get('usage') or {}
            if isinstance(usage, Mapping):
                guard.record_usage(
                    tokens=usage.get('tokens', usage.get('tokens_used', 0)) or 0,
                    cost_usd=usage.get('cost_usd', 0) or 0,
                )

            finding = decision.get('finding')
            if isinstance(finding, Mapping):
                normalized_finding = dict(finding)
                normalized_finding.setdefault('base_case_id', case.get('case_id', ''))
                normalized_finding.setdefault(
                    'exploration_tier', decision.get('exploration_tier', 'data')
                )
                findings.append(normalized_finding)

            verdict = guard.consider(decision)
            history.append(dict(decision))
            if verdict.stopped_reason:
                break
            if verdict.record_only:
                self._append_roam_map_delta(
                    case, decision, test_map, map_nodes, map_edges, coverage='frontier'
                )
                continue
            if not verdict.execute:
                # A custom engine that ignores seen_action_hashes must not spin
                # until the duration budget on a duplicate decision.
                if verdict.reason == 'duplicate':
                    guard.finish(STOP_MANUAL)
                    break
                continue

            action = decision.get('next_action')
            try:
                self._validate_roam_action(action, decision)
                step = {
                    'action': str(action.get('action') or '').strip(),
                    'model': str(action.get('model') or ''),
                    'data': str(action.get('data') or ''),
                }
                # 动态动作可以携带 insert 语义使用的临时模型/数据，但这些
                # 资源只允许在该动作内存在。始终按动作快照，避免自定义决策器
                # 或关键字副作用污染后处理及下一条用例。
                resources_snapshot = self._snapshot_runtime_resources()
                try:
                    temp_models, temp_tables = self._roam_temp_resources(decision)
                    self.apply_insert_resources(temp_models, temp_tables)
                    self._run_steps([step], '漫游')
                finally:
                    self._restore_runtime_resources(resources_snapshot)
                self._append_roam_map_delta(
                    case, decision, test_map, map_nodes, map_edges, coverage='roam_only'
                )
            except ForceRunTermination:
                raise
            except Exception as exc:
                logger.warning('漫游动作失败，不改变基础用例状态: %s', exc)
                findings.append(self._roam_failure_finding(case, exc, 'action'))
                guard.finish(STOP_MANUAL)
                break

        if not guard.stopped_reason:
            guard.finish(STOP_MANUAL)

        map_delta = {'nodes': map_nodes, 'edges': map_edges}
        map_summary: Dict[str, Any] = {
            'nodes_added': 0,
            'edges_added': 0,
            'written': False,
        }
        if map_nodes or map_edges:
            try:
                merged = map_store.merge(map_delta)
                map_summary = merged.to_dict()
            except Exception as exc:
                logger.warning('测试地图写回失败，不影响漫游结果: %s', exc)
                map_summary['reason'] = 'write_failed'

        return guard.build_summary(
            base_case_id=case.get('case_id', ''),
            triggered_by=triggered_by,
            findings=findings,
            test_map_delta=map_summary,
        )

    def _validate_roam_action(
        self, action: Any, decision: Mapping[str, Any]
    ) -> None:
        """Validate a decision before it reaches the normal keyword engine.

        The decision engine is an extension point, so the executor cannot trust
        an arbitrary mapping to be a valid ``test_step``. Keeping this check at
        the execution boundary prevents unknown keywords, non-string payloads,
        and actions explicitly marked irreversible from affecting the live case.
        """
        if not isinstance(action, Mapping):
            raise ValueError('next_action 必须是 test_step 对象')
        action_name = str(action.get('action') or '').strip()
        if not action_name:
            raise ValueError('next_action.action 不能为空')
        supported = {str(item).lower() for item in KeywordEngine.SUPPORTED}
        if action_name.lower() not in supported:
            raise ValueError(f'漫游动作不支持关键字: {action_name}')
        for field in ('model', 'data'):
            value = action.get(field, '')
            if value is None:
                continue
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(f'next_action.{field} 必须是标量值')
        if decision.get('reversible') is False:
            raise ValueError('不可逆漫游动作不得自动执行')

    @staticmethod
    def _roam_temp_resources(
        decision: Mapping[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Extract and validate temporary resources attached to one decision."""
        resources = decision.get('resources')
        if resources is not None:
            if not isinstance(resources, Mapping):
                raise ValueError('漫游 resources 必须是对象')
            temp_models = resources.get('temp_models')
            temp_tables = resources.get('temp_tables')
        else:
            temp_models = decision.get('temp_models')
            temp_tables = decision.get('temp_tables')

        def validate(value: Any, label: str) -> Optional[Dict[str, Any]]:
            if value is None:
                return None
            if not isinstance(value, Mapping):
                raise ValueError(f'{label} 必须是对象')
            normalized: Dict[str, Any] = {}
            for name, entries in value.items():
                if not str(name).strip() or not isinstance(entries, Mapping):
                    raise ValueError(f'{label} 必须是名称到对象的映射')
                normalized[str(name)] = dict(entries)
            return normalized

        return validate(temp_models, 'temp_models'), validate(temp_tables, 'temp_tables')

    @staticmethod
    def _roam_failure_finding(
        case: Mapping[str, Any], error: Exception, stage: str
    ) -> Dict[str, Any]:
        return {
            'base_case_id': case.get('case_id', ''),
            'category': 'UNKNOWN',
            'confidence': 1.0,
            'description': f'漫游{stage}失败: {error}',
            'exploration_tier': 'data',
            'evidence_path': '',
        }

    @staticmethod
    def _append_roam_map_delta(
        case: Mapping[str, Any],
        decision: Mapping[str, Any],
        test_map: Mapping[str, Any],
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        coverage: str,
    ) -> None:
        action = decision.get('next_action')
        if not isinstance(action, Mapping):
            return
        case_id = str(case.get('case_id') or '')
        model = str(action.get('model') or '')
        data_id = str(action.get('data') or '')
        base_node_id = f'case:{case_id}'
        variant_node_id = f'case:{case_id}:data:{model}:{data_id}'
        now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

        prior_visits = 0
        for node in test_map.get('nodes', []) if isinstance(test_map, Mapping) else []:
            if isinstance(node, Mapping) and node.get('id') == variant_node_id:
                try:
                    prior_visits = int(node.get('roam_visit_count', 0))
                except (TypeError, ValueError):
                    prior_visits = 0
                break

        nodes.extend([
            {
                'id': base_node_id,
                'label': str(case.get('title') or case_id),
                'business_tags': list(case.get('tags') or []),
                'covered_by_cases': [case_id],
                'coverage': 'case_verified',
                'findings': [],
                'last_visited': now,
            },
            {
                'id': variant_node_id,
                'label': f'{model}:{data_id}',
                'business_tags': list(case.get('tags') or []),
                'covered_by_cases': [case_id],
                'roam_visit_count': prior_visits + 1,
                'coverage': coverage,
                'findings': [],
                'last_visited': now,
            },
        ])
        edges.append({
            'from': base_node_id,
            'to': variant_node_id,
            'action': dict(action),
            'discovered_by': f'case:{case_id}',
            'confidence': float(decision.get('confidence', 0.0)),
        })

    def _apply_plan_selection(
        self,
        cases: List[Dict[str, Any]],
        selection: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Annotate cases with plan scenario/step filters and return case-level skips."""
        if not selection:
            return cases, {}

        case_skips: Dict[str, str] = {}
        case_has_selection: Dict[str, bool] = {}
        selected_scenarios: Dict[str, Set[str]] = {}
        selected_steps: Dict[str, Dict[str, Set[int]]] = {}
        skipped_scenarios: Dict[str, Dict[str, str]] = {}

        for entry in selection.get('selected', []):
            case_id = entry.get('case_id', '')
            case_has_selection[case_id] = True
            if entry.get('type') == 'case':
                selected_scenarios.setdefault(case_id, set()).add('*')
            elif entry.get('type') == 'scenario':
                selected_scenarios.setdefault(case_id, set()).add(entry.get('scenario_id', ''))
            elif entry.get('type') == 'step':
                scenario_id = entry.get('scenario_id', '')
                selected_scenarios.setdefault(case_id, set()).add(scenario_id)
                selected_steps.setdefault(case_id, {}).setdefault(scenario_id, set()).add(entry.get('step_no'))

        for entry in selection.get('skipped', []):
            case_id = entry.get('case_id', '')
            reason = entry.get('reason', 'plan_skipped')
            if entry.get('type') == 'case':
                case_skips[case_id] = reason
            elif entry.get('type') == 'scenario':
                skipped_scenarios.setdefault(case_id, {})[entry.get('scenario_id', '')] = reason

        for case in cases:
            case_id = case.get('case_id', '')
            if case_id in case_skips:
                continue
            if not case_has_selection.get(case_id):
                case_skips[case_id] = 'plan_not_selected'
                continue

            scenario_ids = selected_scenarios.get(case_id, set())
            if '*' in scenario_ids:
                continue

            case['_selected_scenario_ids'] = scenario_ids
            case['_selected_step_map'] = selected_steps.get(case_id, {})
            case_skipped = dict(skipped_scenarios.get(case_id, {}))
            for scenario in case.get('scenarios', []) or []:
                scenario_id = scenario.get('id', '')
                if scenario_id not in scenario_ids and scenario_id not in case_skipped:
                    case_skipped[scenario_id] = 'plan_not_selected'
            case['_skipped_scenarios'] = case_skipped

        return cases, case_skips

    def _execute_debug_plan(
        self,
        cases: List[Dict[str, Any]],
        plan_case_skips: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """调试模式执行入口：根据 plan kind 分发到 scenario_debug 或 step_debug。"""
        plan = self.plan
        plan_kind = plan.get('kind', '')
        debug_config = plan.get('debug', {})
        selection = self.plan_selection_result or {}
        results = []

        # 初始化结果目录
        self.result_writer._init_run_dir()

        if getattr(self, 'report_collector', None):
            self.report_collector.start_run()

        for case in cases:
            case_id = case.get('case_id', '')
            if case_id in plan_case_skips:
                results.append(self._case_result_skipped(case, plan_case_skips[case_id]))
                continue

            # 找到 plan selection 中该 case 对应的选中 scenario/step
            selected_entries = [
                e for e in selection.get('selected', [])
                if e.get('case_id') == case_id
            ]
            if not selected_entries:
                results.append(self._case_result_skipped(case, 'plan_not_selected'))
                continue

            result = self._execute_debug_case(case, plan_kind, debug_config, selected_entries)
            results.append(result)

        self.result_writer.write_results(results)

        if getattr(self, 'report_collector', None):
            self.report_collector.end_run()

        return results

    def _execute_debug_case(
        self,
        case: Dict[str, Any],
        plan_kind: str,
        debug_config: Dict[str, str],
        selected_entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """执行单个 case 的调试模式。

        根据 plan_kind (scenario_debug / step_debug) 和 debug_config 决定：
        - 是否执行 pre_process
        - 执行哪些 scenario 步骤
        - 是否执行 post_process
        """
        start = time.time()
        self._current_case_steps_log = []
        self._current_case_scenario_statuses = []
        resources_snapshot = self._snapshot_runtime_resources()
        self._current_case_step_wait = case.get('step_wait')
        # 慢步骤检测阈值：支持 case 级覆盖（cases 根元素 slow_threshold 属性，单位秒）
        _slow_override = case.get('slow_threshold')
        if _slow_override is not None:
            try:
                self.keyword_engine.slow_step_threshold = float(_slow_override)
            except (ValueError, TypeError):
                pass
        self._current_case_id = case.get('case_id', '')
        self._step_index = 0
        self._runtime_stopped_graceful = False

        prepare = debug_config.get('prepare', 'auto')
        cleanup = debug_config.get('cleanup', '否')
        step_mode = debug_config.get('step_mode', 'all')

        pre_steps: List[Dict[str, str]] = case.get('pre_process') or []
        post_steps: List[Dict[str, str]] = case.get('post_process') or []

        # 确定目标 scenario 和 step
        target_scenario_id = None
        target_step_no = None
        for entry in selected_entries:
            if entry.get('type') == 'scenario':
                target_scenario_id = entry.get('scenario_id', '')
                break
            elif entry.get('type') == 'step':
                target_scenario_id = entry.get('scenario_id', '')
                target_step_no = entry.get('step_no')
                break
            elif entry.get('type') == 'case':
                # 整个 case 被选中，取第一个 scenario
                scenarios = case.get('scenarios', []) or []
                if scenarios:
                    target_scenario_id = scenarios[0].get('id', '')
                break

        # 找到目标 scenario 的步骤
        target_scenario = None
        target_scenario_steps = []
        for scenario in (case.get('scenarios', []) or []):
            if scenario.get('id', '') == target_scenario_id:
                target_scenario = scenario
                target_scenario_steps = scenario.get('steps', []) or []
                break

        err: Optional[Exception] = None

        try:
            # Phase 1: pre_process
            if prepare == 'auto' or prepare == 'case':
                try:
                    self._run_steps(pre_steps, '预处理')
                except Exception as e:
                    logger.error(f"[debug] 预处理失败: {e}")
                    err = e
            # prepare=none: 不执行 pre_process

            if err is None:
                # Phase 2: scenario 步骤执行
                if plan_kind == 'scenario_debug':
                    # scenario_debug: 执行完整 scenario
                    # prepare=auto 时不需要额外前置步骤（scenario_debug 的 auto 只执行 pre_process）
                    try:
                        self._execute_step_list(target_scenario_steps, '用例')
                    except Exception as e:
                        logger.error(f"[debug] scenario 执行失败: {e}")
                        err = e

                elif plan_kind == 'step_debug':
                    # step_debug: 根据 step_mode 决定执行范围
                    if step_mode == 'all':
                        # 执行整个 scenario（忽略 step 选择）
                        try:
                            self._execute_step_list(target_scenario_steps, '用例')
                        except Exception as e:
                            logger.error(f"[debug] step_debug all 执行失败: {e}")
                            err = e
                    elif step_mode == 'from':
                        # 从指定 step no 开始执行到 scenario 结束
                        step_idx = (target_step_no or 1) - 1  # 1-based to 0-based
                        # prepare=auto 时执行目标 step 之前的步骤
                        if prepare == 'auto' and step_idx > 0:
                            try:
                                self._execute_step_list(target_scenario_steps[:step_idx], '用例')
                            except Exception as e:
                                logger.error(f"[debug] 前置步骤执行失败: {e}")
                                err = e
                        if err is None:
                            try:
                                self._execute_step_list(target_scenario_steps[step_idx:], '用例')
                            except Exception as e:
                                logger.error(f"[debug] step_debug from 执行失败: {e}")
                                err = e
                    elif step_mode == 'only':
                        # 只执行指定 step no
                        step_idx = (target_step_no or 1) - 1
                        # prepare=auto 时执行目标 step 之前的步骤
                        if prepare == 'auto' and step_idx > 0:
                            try:
                                self._execute_step_list(target_scenario_steps[:step_idx], '用例')
                            except Exception as e:
                                logger.error(f"[debug] 前置步骤执行失败: {e}")
                                err = e
                        if err is None and step_idx < len(target_scenario_steps):
                            try:
                                self._execute_step_list(
                                    [target_scenario_steps[step_idx]], '用例'
                                )
                            except Exception as e:
                                logger.error(f"[debug] step_debug only 执行失败: {e}")
                                err = e

            # Phase 3: post_process
            if cleanup == '是':
                try:
                    self._run_steps(post_steps, '后处理')
                except Exception as e:
                    logger.error(f"[debug] 后处理失败: {e}")
                    if err is None:
                        err = e

            if err is not None:
                return {
                    'case_id': case.get('case_id', ''),
                    'title': case.get('title', ''),
                    'status': 'FAIL',
                    'execution_time': round(time.time() - start, 3),
                    'error': str(err),
                    'screenshot_path': '',
                }

            return {
                'case_id': case.get('case_id', ''),
                'title': case.get('title', ''),
                'status': 'PASS',
                'execution_time': round(time.time() - start, 3),
            }
        finally:
            self._restore_runtime_resources(resources_snapshot)

    @staticmethod
    def _case_result_skipped(case: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            'case_id': case.get('case_id', ''),
            'title': case.get('title', ''),
            'status': 'SKIP',
            'execution_time': 0,
            'error': reason,
            'screenshot_path': '',
        }

    @staticmethod
    def _filter_cases(
        cases: List[Dict[str, Any]],
        filter_tags: Optional[List[str]] = None,
        filter_priority: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """按 tags / priority / exclude_tags 过滤用例列表

        - filter_tags: OR 匹配 -- 用例 tags 与 filter_tags 有交集即命中
        - filter_priority: 用例 priority 在列表中即命中
        - exclude_tags: 用例 tags 与 exclude_tags 有交集则排除
        - 所有参数均为空时返回原列表（向后兼容）
        """
        if not filter_tags and not filter_priority and not exclude_tags:
            return cases

        filtered = []
        for case in cases:
            case_tags = set(case.get('tags') or [])
            case_priority = (case.get('priority') or '').strip()

            # exclude_tags 检查（优先排除）
            if exclude_tags and case_tags & set(exclude_tags):
                logger.debug(f"用例 {case['case_id']} 被 exclude_tags 排除")
                continue

            # filter_tags 检查
            if filter_tags and not (case_tags & set(filter_tags)):
                logger.debug(f"用例 {case['case_id']} 不匹配 filter_tags")
                continue

            # filter_priority 检查
            if filter_priority and case_priority not in filter_priority:
                logger.debug(f"用例 {case['case_id']} 不匹配 filter_priority")
                continue

            filtered.append(case)

        logger.info(f"过滤后用例数: {len(filtered)}/{len(cases)}")
        return filtered

    def _recording_option(self, key: str, default: Any = None) -> Any:
        recording_config = getattr(self, "recording_config", {}) or {}
        config = getattr(self, "config", None)
        if config is not None and hasattr(config, "get"):
            try:
                value = config.get(f"recording.{key}", recording_config.get(key, default))
            except TypeError:
                value = recording_config.get(key, default)
            if type(value).__module__ != "unittest.mock":
                return value
        return recording_config.get(key, default)

    def _select_recording_backend(self) -> Optional[str]:
        if not getattr(self, "recording_enabled", False):
            return None
        mode = self._recording_option("mode", "auto")
        if mode == "off":
            return None
        # 驱动尚未就绪（移动端/桌面端懒加载，self.driver 为 None）：
        # 推迟到 driver 创建回调里再启动录像，避免误起 screen 录桌面。
        if self.driver is None and getattr(self, "driver_factory", None):
            return None
        if mode == "screen":
            return mode
        if mode in ("playwright", "appium"):
            # 显式指定驱动级后端，但 driver 还没就绪 → 推迟
            if not hasattr(self.driver, "start_case_recording"):
                return None
            return mode
        # auto：优先用驱动自报的 recording_backend（playwright / appium），
        # 二者共用同一套用例级录像分段机器，仅 backend 标识不同。
        if hasattr(self.driver, "start_case_recording"):
            declared = getattr(self.driver, "recording_backend", None)
            if declared in self._DRIVER_RECORDING_BACKENDS:
                return declared
            return "playwright"
        return "screen"

    @staticmethod
    def _safe_recording_id(case_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(case_id)).strip("_")
        return safe or "case"

    def _relative_run_path(self, path: str) -> str:
        if not path or not self.result_writer.current_run_dir:
            return path or ""
        try:
            return str(Path(path).resolve().relative_to(self.result_writer.current_run_dir.resolve()))
        except Exception:
            return str(path)

    def _set_keyword_recording_path(self, path: Optional[str]) -> None:
        if hasattr(self.keyword_engine, "set_current_recording_path"):
            self.keyword_engine.set_current_recording_path(path)
        else:
            setattr(self.keyword_engine, "_current_recording_path", path)

    def _next_recording_segment_path(self, case_id: str) -> Path:
        if self._recording_output_dir is None:
            raise RuntimeError("录制输出目录未初始化")
        safe_case_id = self._safe_recording_id(case_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._recording_segment_index += 1
        return self._recording_output_dir / f"{safe_case_id}_{timestamp}_{self._recording_segment_index:02d}.webm"

    def _append_recording_segment(self, path: str, backend: str) -> str:
        relative_path = self._relative_run_path(path)
        if not relative_path:
            return ""
        for segment in self._recording_segments:
            if segment.get("path") == relative_path:
                return relative_path
        self._recording_segments.append({
            "index": len(self._recording_segments) + 1,
            "path": relative_path,
            "backend": backend,
        })
        return relative_path

    def _start_playwright_recording_segment(self, case_id: str) -> str:
        if not self._case_recording_active or self._active_recording_backend not in self._DRIVER_RECORDING_BACKENDS:
            return ""
        if self._current_recording_path:
            return self._relative_run_path(self._current_recording_path)
        if self._recording_output_dir is None or not hasattr(self.driver, "start_case_recording"):
            return ""

        # 锁定录像驱动引用：移动端 self.driver 会随每步在 web 占位/真实 driver 间切换，
        # 录像的 start/stop 必须用同一个真实 driver，否则 stop 时引用已丢。
        self._recording_driver = self.driver
        target_path = self._next_recording_segment_path(case_id)
        started = self.driver.start_case_recording(
            str(self._recording_output_dir),
            case_id,
            str(target_path),
            video_size=self._recording_video_size,
        )
        if not started:
            return ""

        self._current_recording_path = str(started if isinstance(started, (str, Path)) else target_path)
        self._set_keyword_recording_path(self._current_recording_path)
        return self._relative_run_path(self._current_recording_path)

    def _finalize_current_playwright_segment(self, case_id: str) -> str:
        if self._active_recording_backend not in self._DRIVER_RECORDING_BACKENDS or not self._current_recording_path:
            self._set_keyword_recording_path(None)
            return ""

        path = None
        # 优先用锁定的录像驱动（移动端 self.driver 可能已被切回 web 占位）
        rec_driver = getattr(self, "_recording_driver", None) or self.driver
        if hasattr(rec_driver, "stop_case_recording"):
            path = rec_driver.stop_case_recording(case_id, self._current_recording_path)
        final_path = str(path or self._current_recording_path)
        relative_path = self._append_recording_segment(final_path, self._active_recording_backend)
        self._current_recording_path = None
        self._recording_driver = None
        self._set_keyword_recording_path(None)
        return relative_path

    def _start_case_recording(self, case_id: str) -> str:
        self._recording_segments = []
        self._recording_segment_index = 0
        self._case_recording_active = False
        self._recording_case_id = None
        self._recording_output_dir = None
        self._recording_video_size = None

        backend = self._select_recording_backend()
        if not backend:
            self._current_recording_path = None
            self._set_keyword_recording_path(None)
            return ""
        try:
            if not self.result_writer.current_run_dir:
                self.result_writer._init_run_dir()
            output_dir = self.result_writer.current_run_dir / str(self._recording_option("output_dir", "recordings"))
            output_dir.mkdir(parents=True, exist_ok=True)
            safe_case_id = self._safe_recording_id(case_id)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if backend in self._DRIVER_RECORDING_BACKENDS:
                if not hasattr(self.driver, "start_case_recording"):
                    logger.warning(f"当前驱动不支持原生录制（backend={backend}）")
                    return ""
                self._active_recording_backend = backend
                self._case_recording_active = True
                self._recording_case_id = case_id
                self._recording_output_dir = output_dir
                self._recording_video_size = str(self._recording_option("video_size", "screen"))
                started = self._start_playwright_recording_segment(case_id)
                if not started:
                    self._active_recording_backend = None
                    self._case_recording_active = False
                    self._current_recording_path = None
                    self._set_keyword_recording_path(None)
                    return ""
                return started

            try:
                from ..vision.screen_recorder import ScreenRecorder
            except ImportError:
                from rodski.vision.screen_recorder import ScreenRecorder
            recorder = ScreenRecorder(
                output_dir=str(output_dir),
                fps=int(self._recording_option("fps", 10)),
                max_duration=int(self._recording_option("max_duration", 600)),
                scope=str(self._recording_option("scope", "target")),
                monitor_id=self._recording_option("monitor_id", None),
                overlay_step=bool(self._recording_option("overlay_step", True)),
            )
            path = recorder.start(session_id=f"{safe_case_id}_{timestamp}")
            self._screen_recorder = recorder
            self._active_recording_backend = "screen"
            self._current_recording_path = path
            self._set_keyword_recording_path(path)
            return self._relative_run_path(path)
        except Exception as e:
            logger.warning(f"启动用例录制失败: {e}")
            import sys as _sys
            print(f"[录制警告] 用例 {case_id} 录制未启动: {e}", file=_sys.stderr)
            self._screen_recorder = None
            self._active_recording_backend = None
            self._current_recording_path = None
            self._case_recording_active = False
            self._recording_case_id = None
            self._recording_output_dir = None
            self._recording_video_size = None
            self._set_keyword_recording_path(None)
            return ""

    def _stop_case_recording(self, case_id: str, started_path: str = "") -> str:
        if not getattr(self, "_active_recording_backend", None):
            self._set_keyword_recording_path(None)
            return started_path or ""
        try:
            if self._active_recording_backend in self._DRIVER_RECORDING_BACKENDS:
                self._finalize_current_playwright_segment(case_id)
                return self._recording_segments[0]["path"] if self._recording_segments else (started_path or "")

            path = None
            if self._active_recording_backend == "screen" and self._screen_recorder is not None:
                path = self._screen_recorder.stop()
                final_path = self._relative_run_path(path or self._current_recording_path or started_path)
                if final_path:
                    self._recording_segments = [{"index": 1, "path": final_path, "backend": "screen"}]
                return final_path
            return self._relative_run_path(self._current_recording_path or started_path)
        except Exception as e:
            logger.warning(f"停止用例录制失败: {e}")
            return started_path or ""
        finally:
            self._screen_recorder = None
            self._active_recording_backend = None
            self._current_recording_path = None
            self._case_recording_active = False
            self._recording_case_id = None
            self._recording_output_dir = None
            self._recording_video_size = None
            self._set_keyword_recording_path(None)

    def _attach_recording_path(self, result: Dict[str, Any], recording_path: str) -> Dict[str, Any]:
        result["recording_path"] = recording_path or ""
        result["recordings"] = list(self._recording_segments)
        return result

    def execute_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个用例（三阶段：预处理 → 用例 → 后处理）。

        每阶段内为多个 test_step，顺序执行。
        - 预处理失败：跳过用例阶段，仍执行后处理。
        - 用例阶段失败：仍执行后处理（清理/关闭等）。
        - 后处理失败：记为失败。
        """
        start = time.time()
        screenshot_path = None
        screenshot_attempted = False
        case_diagnosis = None
        roam_summary: Optional[Dict[str, Any]] = None
        self._current_case_steps_log = []
        self._current_case_scenario_statuses = []
        resources_snapshot = self._snapshot_runtime_resources()

        # 保存当前 case 的 step_wait 配置（优先级高于全局配置）
        self._current_case_step_wait = case.get('step_wait')

        self._pending_case_status: Optional[str] = None

        try:
            self._current_case_id = case['case_id']
            self._step_index = 0
            self._runtime_stopped_graceful = False
            self._current_scenario_id = None
            self._current_scenario_title = None
            recording_path = self._start_case_recording(case['case_id'])
            self._current_plan_selected_scenario_ids = case.get('_selected_scenario_ids')
            self._current_plan_selected_step_map = case.get('_selected_step_map') or {}
            self._current_plan_skipped_scenarios = case.get('_skipped_scenarios') or {}

            def _finish(result: Dict[str, Any]) -> Dict[str, Any]:
                if getattr(self, '_current_case_scenario_statuses', None):
                    result['scenario_statuses'] = list(self._current_case_scenario_statuses)
                # 附带每步执行明细（含每步截图相对路径），供报告每步内联展示
                if getattr(self, '_current_case_steps_log', None):
                    result['steps'] = list(self._current_case_steps_log)
                if case_diagnosis is not None:
                    result['case_diagnosis'] = case_diagnosis
                if roam_summary is not None:
                    result['roam_summary'] = roam_summary
                final_recording_path = self._stop_case_recording(case['case_id'], recording_path)
                return self._attach_recording_path(result, final_recording_path)

            def _capture_failure_screenshot() -> None:
                nonlocal screenshot_path, screenshot_attempted
                if screenshot_attempted:
                    return
                screenshot_attempted = True
                component_type = case.get('component_type', '界面')
                if self.auto_screenshot and not self._driver_closed and component_type == '界面':
                    screenshot_path = self._take_failure_screenshot(case['case_id'])

            # 报告收集器：开始用例
            if getattr(self, 'report_collector', None):
                self.report_collector.start_case(case)

            err: Optional[Exception] = None

            def _merge_error(e: Exception) -> None:
                nonlocal err
                if err is None:
                    err = e
                else:
                    err = Exception(f"{err}; {e}")

            pre_steps: List[Dict[str, str]] = case.get('pre_process') or []
            test_steps: List[Dict[str, str]] = case.get('test_case') or []
            post_steps: List[Dict[str, str]] = case.get('post_process') or []

            # 预处理
            try:
                self._run_steps(pre_steps, '预处理')
            except ForceRunTermination as e:
                return _finish(self._case_result_force_terminated(case, start, e))
            except Exception as e:
                logger.error(f"预处理失败: {e}")
                _merge_error(e)
                _capture_failure_screenshot()

            # 用例阶段（仅当预处理未失败且未优雅终止时执行）
            if err is None and not self._runtime_stopped_graceful:
                try:
                    self._run_steps(test_steps, '用例')
                except ForceRunTermination as e:
                    return _finish(self._case_result_force_terminated(case, start, e))
                except Exception as e:
                    logger.error(f"用例阶段失败: {e}")
                    _merge_error(e)
                    _capture_failure_screenshot()

            # 漫游严格插入在 test_case 成功后、post_process 前。批量入口对
            # 不满足三层开关的用例静默跳过；single_case 已在入口显式校验。
            if (
                err is None
                and not self._runtime_stopped_graceful
                and case.get('expect_fail', '否').strip() != '是'
                and getattr(self, 'roam_enabled', False)
            ):
                roam_reasons = self._roam_eligibility_reasons(case)
                if not roam_reasons:
                    try:
                        roam_summary = self._run_roam_session(case)
                    except ForceRunTermination as e:
                        return _finish(self._case_result_force_terminated(case, start, e))
                    except Exception as roam_exc:
                        logger.warning('漫游阶段异常，继续执行后处理: %s', roam_exc)
                        roam_summary = {
                            'base_case_id': case.get('case_id', ''),
                            'triggered_by': getattr(self, 'roam_mode', None) or 'batch_just_passed',
                            'variants_tried': 0,
                            'duration_seconds': 0.0,
                            'stopped_reason': STOP_MANUAL,
                            'findings': [self._roam_failure_finding(case, roam_exc, 'session')],
                        }

            # 后处理：无论预处理/用例是否失败均执行（除非强制终止已返回）
            try:
                self._run_steps(post_steps, '后处理')
            except ForceRunTermination as e:
                return _finish(self._case_result_force_terminated(case, start, e))
            except Exception as e:
                logger.error(f"后处理失败: {e}")
                _merge_error(e)
                _capture_failure_screenshot()

            if err is not None:
                _capture_failure_screenshot()

                # v8.2.0 Hooks 机制：on_case_failure 挂载点（进程内回调 + DiagnosisEngine 接入）
                # getattr 兜底：测试代码中常见 object.__new__(SKIExecutor) 绕过 __init__ 的构造方式
                for hook in getattr(self, '_hooks', {}).get("on_case_failure", []):
                    try:
                        hook(case, err, screenshot_path)
                    except Exception as hook_exc:  # noqa: BLE001
                        logger.warning(f"on_case_failure 回调异常，忽略: {hook_exc}")
                _diag_engine = getattr(self, '_diagnosis_engine', None)
                if _diag_engine is not None:
                    try:
                        diagnosis_report = _diag_engine.diagnose(
                            error=err,
                            screenshot_path=screenshot_path,
                            context={
                                "case_id": case.get('case_id', ''),
                                "title": case.get('title', ''),
                            },
                        )
                        case_diagnosis = diagnosis_report.to_dict()
                        if getattr(self, 'report_collector', None):
                            self.report_collector.record_diagnosis(case_diagnosis)
                    except Exception as diag_exc:  # noqa: BLE001
                        logger.warning(f"DiagnosisEngine 诊断异常，忽略: {diag_exc}")

                if self.result_writer.current_run_dir:
                    write_execution_summary(
                        self.result_writer.current_run_dir,
                        case['case_id'],
                        self._current_case_steps_log,
                        dict(self.keyword_engine._context.named),
                    )

                # expect_fail 逻辑：预期失败的用例实际失败时标记为 PASS
                expect_fail = case.get('expect_fail', '否').strip()
                if expect_fail == '是':
                    logger.info(f"用例 {case['case_id']} 预期失败且实际失败 → 标记为 PASS")
                    return _finish({
                        'case_id': case['case_id'],
                        'title': case.get('title', ''),
                        'status': 'PASS',
                        'execution_time': round(time.time() - start, 3),
                        'error': f"[预期失败] {str(err)}",
                        'screenshot_path': screenshot_path or '',
                    })

                return _finish({
                    'case_id': case['case_id'],
                    'title': case.get('title', ''),
                    'status': 'FAIL',
                    'execution_time': round(time.time() - start, 3),
                    'error': str(err),
                    'screenshot_path': screenshot_path or '',
                })

            if self._runtime_stopped_graceful:
                if self.result_writer.current_run_dir:
                    write_execution_summary(
                        self.result_writer.current_run_dir,
                        case['case_id'],
                        self._current_case_steps_log,
                        dict(self.keyword_engine._context.named),
                    )
                return _finish({
                    'case_id': case['case_id'],
                    'title': case.get('title', ''),
                    'status': 'SKIP',
                    'execution_time': round(time.time() - start, 3),
                    'error': 'runtime terminate (graceful)',
                    'screenshot_path': '',
                })

            if self.result_writer.current_run_dir:
                write_execution_summary(
                    self.result_writer.current_run_dir,
                    case['case_id'],
                    self._current_case_steps_log,
                    dict(self.keyword_engine._context.named),
                )

            # expect_fail 逻辑：预期失败的用例实际成功时标记为 FAIL
            expect_fail = case.get('expect_fail', '否').strip()
            if expect_fail == '是':
                logger.warning(f"用例 {case['case_id']} 预期失败但实际成功 → 标记为 FAIL")
                return _finish({
                    'case_id': case['case_id'],
                    'title': case.get('title', ''),
                    'status': 'FAIL',
                    'execution_time': round(time.time() - start, 3),
                    'error': '[预期失败但实际成功] 用例应该失败但通过了所有步骤',
                })

            return _finish({
                'case_id': case['case_id'],
                'title': case.get('title', ''),
                'status': 'PASS',
                'execution_time': round(time.time() - start, 3),
            })
        finally:
            self._restore_runtime_resources(resources_snapshot)

    def _case_result_force_terminated(
        self, case: Dict[str, Any], start: float, exc: ForceRunTermination
    ) -> Dict[str, Any]:
        screenshot_path = None
        component_type = case.get('component_type', '界面')
        if self.auto_screenshot and not self._driver_closed and component_type == '界面':
            screenshot_path = self._take_failure_screenshot(case['case_id'])
        return {
            'case_id': case['case_id'],
            'title': case.get('title', ''),
            'status': 'FAIL',
            'execution_time': round(time.time() - start, 3),
            'error': str(exc),
            'screenshot_path': screenshot_path or '',
        }

    def apply_insert_resources(
        self,
        temp_models: Optional[Dict[str, Dict[str, Dict[str, str]]]],
        temp_tables: Optional[Dict[str, Dict[str, Dict[str, Any]]]],
    ) -> None:
        """为 insert 步骤注册临时模型与数据表（与正式资源同一解析结构）。"""
        if temp_models and self.model_parser:
            self.model_parser.merge_models(temp_models)
        if temp_tables:
            for name, rows in temp_tables.items():
                self.data_manager.merge_table(name, rows)

    def _drain_runtime_at_boundary(self, dq: Deque[Dict[str, str]]) -> bool:
        """在步骤边界处理控制队列。若优雅终止返回 True（调用方应结束本阶段）。"""
        try:
            self.runtime_control.drain_at_boundary(self, dq)
        except GracefulRunTermination:
            self._runtime_stopped_graceful = True
            return True
        except ForceRunTermination:
            raise
        return False

    def _snapshot_runtime_resources(self) -> Dict[str, Any]:
        """保存当前 case 执行前资源快照，确保临时资源只在当前 case 生效。"""
        return {
            'models': copy.deepcopy(self.model_parser.models) if self.model_parser else None,
            'tables': copy.deepcopy(self.data_manager.tables),
        }

    def _restore_runtime_resources(self, snapshot: Dict[str, Any]) -> None:
        if self.model_parser and snapshot.get('models') is not None:
            self.model_parser.models = snapshot['models']
        self.data_manager.tables = snapshot.get('tables', {})

    def _run_steps(self, steps: List[Dict[str, str]], phase_label: str) -> None:
        """顺序执行某阶段内全部 test_step；支持 scenario、运行时 insert 扩展队列、条件和循环。"""
        dq = deque([s for s in steps if s.get('action') or s.get('type')])
        self._phase_runtime_seq = 0
        scenario_states: Dict[str, str] = {}
        first_scenario_error: Optional[Exception] = None

        while dq:
            if self._drain_runtime_at_boundary(dq):
                return

            # 暂停状态下仍需周期性处理控制队列（resume/force_terminate），避免死锁
            while not self.runtime_control.wait_unpaused(timeout=0.1):
                if self._drain_runtime_at_boundary(dq):
                    return

            if self._drain_runtime_at_boundary(dq):
                return
            if not dq:
                continue
            step = dq.popleft()
            self._phase_runtime_seq += 1

            if step.get('type') == 'scenario':
                scenario_id = step.get('id', '')
                skipped_scenarios = getattr(self, '_current_plan_skipped_scenarios', {}) or {}
                if scenario_id in skipped_scenarios:
                    reason = skipped_scenarios[scenario_id]
                    logger.info(f"  [{self._phase_runtime_seq}] scenario {scenario_id} -> SKIP ({reason})")
                    if scenario_id:
                        scenario_states[scenario_id] = 'SKIP'
                    self._record_scenario_status(step, phase_label, 'SKIP', reason)
                    continue
                selected_scenarios = getattr(self, '_current_plan_selected_scenario_ids', None)
                if selected_scenarios is not None and scenario_id not in selected_scenarios:
                    reason = 'plan_not_selected'
                    logger.info(f"  [{self._phase_runtime_seq}] scenario {scenario_id} -> SKIP ({reason})")
                    if scenario_id:
                        scenario_states[scenario_id] = 'SKIP'
                    self._record_scenario_status(step, phase_label, 'SKIP', reason)
                    continue
                try:
                    self._execute_scenario(step, phase_label, scenario_states)
                except Exception as e:
                    scenario_id = step.get('id', '')
                    if scenario_id:
                        scenario_states[scenario_id] = 'FAIL'
                    self._record_scenario_status(step, phase_label, 'FAIL', str(e))
                    if first_scenario_error is None:
                        first_scenario_error = e
            else:
                self._execute_step_item(step, phase_label)

            if self._drain_runtime_at_boundary(dq):
                return

        if first_scenario_error is not None:
            raise first_scenario_error

    def _execute_step_item(self, step: Dict[str, Any], phase_label: str) -> None:
        """执行一个普通步骤 / if / loop 项；scenario 仅由 _run_steps 顶层调度。"""
        if step.get('type') == 'if':
            self._execute_if_block(step, phase_label)
        elif step.get('type') == 'loop':
            loop_range = step.get('range', '')
            var_name = step.get('var', 'item')
            items = self.dynamic_executor.parse_loop_range(loop_range)
            logger.info(f"  [{self._phase_runtime_seq}] loop {var_name} in {loop_range} ({len(items)} 次)")
            for idx, item in enumerate(items, 1):
                self.dynamic_executor.set_variable(var_name, item)
                logger.debug(f"    循环 [{idx}/{len(items)}]: {var_name}={item}")
                self._execute_step_list(step.get('steps', []), phase_label)
        else:
            logger.debug(f"  [{self._phase_runtime_seq}] {step['action']}")
            self.execute_step(step, phase_label)

    def _execute_scenario(
        self,
        scenario: Dict[str, Any],
        phase_label: str,
        scenario_states: Dict[str, str],
    ) -> None:
        """执行 scenario 容器，并维护同一 case/phase 内 depends 状态。"""
        scenario_id = scenario.get('id', '')
        title = scenario.get('title', '')
        depends = scenario.get('depends') or []
        blocked_by = [dep for dep in depends if scenario_states.get(dep) != 'PASS']

        if blocked_by:
            reason = f"depends not passed: {', '.join(blocked_by)}"
            logger.info(f"  [{self._phase_runtime_seq}] scenario {scenario_id} - {title} -> SKIP ({reason})")
            if scenario_id:
                scenario_states[scenario_id] = 'SKIP'
            self._record_scenario_status(scenario, phase_label, 'SKIP', reason)
            return

        logger.info(
            f"  [{self._phase_runtime_seq}] scenario {scenario_id} - {title} "
            f"(group={scenario.get('group', '')}, tag={scenario.get('tag') or []})"
        )
        self._current_scenario_id = scenario_id
        self._current_scenario_title = title
        scenario_steps = scenario.get('steps', []) or []
        selected_step_map = getattr(self, '_current_plan_selected_step_map', {}) or {}
        selected_step_numbers = selected_step_map.get(scenario_id)
        if selected_step_numbers:
            scenario_steps = [
                sub_step
                for idx, sub_step in enumerate(scenario_steps, 1)
                if idx in selected_step_numbers
            ]
        for sub_step in scenario_steps:
            self._execute_step_item(sub_step, f"{phase_label}/{scenario_id}" if scenario_id else phase_label)

        if scenario_id:
            scenario_states[scenario_id] = 'PASS'
        self._record_scenario_status(scenario, phase_label, 'PASS', '')
        self._current_scenario_id = None
        self._current_scenario_title = None

    def _record_scenario_status(
        self,
        scenario: Dict[str, Any],
        phase_label: str,
        status: str,
        error: str = '',
    ) -> None:
        """记录 scenario 级执行状态，供日志/结果对象和测试断言使用。"""
        statuses = getattr(self, '_current_case_scenario_statuses', None)
        if statuses is None:
            self._current_case_scenario_statuses = []
            statuses = self._current_case_scenario_statuses
        statuses.append({
            'id': scenario.get('id', ''),
            'title': scenario.get('title', ''),
            'group': scenario.get('group', ''),
            'tag': list(scenario.get('tag') or []),
            'depends': list(scenario.get('depends') or []),
            'phase': phase_label,
            'status': status,
            'error': error,
        })

    def _execute_if_block(self, step: Dict[str, Any], phase_label: str) -> None:
        """执行 if / elif / else 条件块（支持嵌套 if，最多 2 层）"""
        condition = step.get('condition', '')
        try:
            evaluated = self.dynamic_executor.evaluate_condition(
                condition, driver=self.driver
            )
        except Exception as e:
            screenshot_path = self._take_failure_screenshot(
                f"if_cond_failed_{hash(condition) & 0xFFFFFFFF:08x}"
            )
            logger.warning(
                f"[IF] 条件无法评估: condition={condition}\n"
                f"   错误: {e}\n"
                f"   截图: {screenshot_path}\n"
                f"   建议: Agent 检查条件语法或页面状态\n"
                f"   可用操作: 调整条件 / 跳过此分支 / 插入 cleanup 步骤"
            )
            logger.warning(f"  [{self._phase_runtime_seq}] if ({condition}) -> 评估失败（跳过）")
            return

        if evaluated:
            logger.info(f"  [{self._phase_runtime_seq}] if ({condition}) -> True")
            self._execute_step_list(step.get('steps', []), phase_label)
            return

        # if 条件为 False：尝试 elif 链
        elif_chain = step.get('elif_chain', [])
        for idx, elif_item in enumerate(elif_chain):
            elif_cond = elif_item.get('condition', '')
            try:
                elif_result = self.dynamic_executor.evaluate_condition(
                    elif_cond, driver=self.driver
                )
            except Exception as e:
                logger.warning(f"  [{self._phase_runtime_seq}] elif ({elif_cond}) -> 评估失败（跳过）: {e}")
                continue
            if elif_result:
                logger.info(f"  [{self._phase_runtime_seq}] elif ({elif_cond}) -> True")
                self._execute_step_list(elif_item.get('steps', []), phase_label)
                return

        # 所有 if/elif 均为 False：执行 else
        else_steps = step.get('else_steps', [])
        if else_steps:
            logger.info(f"  [{self._phase_runtime_seq}] if ({condition}) -> False -> else")
            self._execute_step_list(else_steps, phase_label)
        else:
            logger.debug(f"  [{self._phase_runtime_seq}] if ({condition}) -> False (无 else 跳过)")

    def _execute_step_list(self, steps: List[Dict[str, Any]], phase_label: str) -> None:
        """执行步骤列表，支持嵌套 if/loop 块。"""
        for sub_step in steps:
            self._execute_step_item(sub_step, phase_label)

    def _take_failure_screenshot(self, case_id: str) -> Optional[str]:
        """在用例失败时自动截图"""
        try:
            if not self.result_writer.current_run_dir:
                self.result_writer._init_run_dir()
            if not self.result_writer.current_run_dir:
                return None

            screenshot_dir = self.result_writer.current_run_dir / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{case_id}_{timestamp}_failure.png"
            screenshot_path = screenshot_dir / filename

            success = self.driver.screenshot(str(screenshot_path))
            if success:
                logger.info(f"失败截图已保存: {screenshot_path}")
                return f"screenshots/{filename}"
            else:
                logger.warning(f"截图失败: {screenshot_path}")
                return None
        except Exception as e:
            logger.warning(f"自动截图失败: {e}")
            return None

    def _take_roam_screenshot(self, case_id: str, suffix: str) -> Optional[str]:
        """漫游专用截图（不复用 _take_failure_screenshot，避免语义混淆和后缀污染）。"""
        try:
            if not self.result_writer.current_run_dir:
                self.result_writer._init_run_dir()
            if not self.result_writer.current_run_dir:
                return None
            screenshot_dir = self.result_writer.current_run_dir / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{case_id}_roam_{suffix}_{timestamp}.png"
            screenshot_path = screenshot_dir / filename
            success = self.driver.screenshot(str(screenshot_path))
            if success:
                return f"screenshots/{filename}"
            return None
        except Exception as exc:
            logger.debug("漫游截图失败: %s", exc)
            return None

    def execute_step(self, step: Dict[str, str], step_type: str = ""):
        """执行单个步骤"""
        action = step['action']
        model = step['model']
        data = step['data']

        resolved_data = self.data_resolver.resolve_case_data(data)

        if data and resolved_data != data:
            logger.debug(f"数据解析: '{data}' -> '{resolved_data}'")

        action_key = action.lower()
        if self._driver_closed and action_key not in ('close', 'wait', 'set', 'send', 'db', 'run'):
            self._ensure_driver_alive()
            if self._active_recording_backend in self._DRIVER_RECORDING_BACKENDS and self._case_recording_active:
                self._start_playwright_recording_segment(getattr(self, '_current_case_id', 'unknown'))

        # 更新录像步骤文字叠加
        if getattr(self, '_active_recording_backend', None) == "screen" and getattr(self, '_screen_recorder', None) is not None:
            step_no = len(self._current_case_steps_log) + 1
            parts = [f"Step {step_no}", action]
            if model:
                parts.append(model)
            if data:
                parts.append(data)
            self._screen_recorder.set_step("  |  ".join(parts))

        history_before = len(self.keyword_engine._context.history)
        named_before = dict(self.keyword_engine._context.named)

        # 浏览器监控（v0.1）：标记当前步骤，供后续 collect 关联
        _step_index_for_monitor = len(self._current_case_steps_log) + 1
        _monitor_step_id = f"{getattr(self, '_current_case_id', 'unknown')}_step{_step_index_for_monitor:03d}"
        _monitor = getattr(self.driver, 'set_monitor_step', None)
        if _monitor is not None and action_key not in ('close',):
            try:
                _monitor(_monitor_step_id)
            except Exception:
                pass
        # appium 录像必须在 close 关键字 quit 掉 Appium session 之前停止并落盘，
        # 否则 stop_recording_screen 会因 session 已断而失败。Playwright 不受此限
        # （其录像上下文由 stop_case_recording 内部管理），仍按 close 后处理。
        if action_key == 'close' and self._active_recording_backend == "appium":
            self._finalize_current_playwright_segment(getattr(self, '_current_case_id', 'unknown'))

        # 特殊处理 set 动作：将变量同步到动态执行器
        if action_key == 'set':
            params = {'var_name': model, 'value': resolved_data}
            self.keyword_engine.execute(action, params)
            # 同步到动态执行器
            if hasattr(self, 'dynamic_executor'):
                self.dynamic_executor.set_variable(model, resolved_data)
        else:
            params = {'model': model, 'data': resolved_data}
            try:
                self.keyword_engine.execute(action, params)
            except AssertionFailedError as exc:
                history_after = self.keyword_engine._context.history
                last_return = history_after[-1] if len(history_after) > history_before else None
                named_after = dict(self.keyword_engine._context.named)
                named_writes = {k: v for k, v in named_after.items() if named_before.get(k) != v}
                step_index = len(self._current_case_steps_log) + 1
                # 失败时也收集监控异常（可能是失败原因）
                _collect_monitor_fail = getattr(self.driver, 'collect_monitor_errors', None)
                _browser_errors_fail = []
                if _collect_monitor_fail is not None:
                    try:
                        _browser_errors_fail = _collect_monitor_fail() or []
                    except Exception:
                        pass
                if _browser_errors_fail:
                    logger.warning("[BrowserMonitor] step %s(fail) 捕获 %d 条异常: %s",
                                   _monitor_step_id, len(_browser_errors_fail),
                                   "; ".join(e.get('text') or e.get('message', '') for e in _browser_errors_fail[:3]))
                self._current_case_steps_log.append({
                    'index': step_index,
                    'action': action,
                    'model': model,
                    'phase': step_type,
                    'status': 'fail',
                    'return_source': 'keyword_result',
                    'return_value': last_return,
                    'named_writes': named_writes,
                    'error': str(exc),
                    'browser_monitor': _browser_errors_fail,
                })

                if getattr(self, 'report_collector', None):
                    self.report_collector.record_step({
                        'index': step_index,
                        'action': action,
                        'model': model,
                        'data': resolved_data,
                        'status': 'fail',
                        'return_value': last_return,
                        'error': str(exc),
                        'browser_monitor': _browser_errors_fail,
                    })
                raise

        history_after = self.keyword_engine._context.history
        last_return = history_after[-1] if len(history_after) > history_before else None
        named_after = dict(self.keyword_engine._context.named)
        named_writes = {k: v for k, v in named_after.items() if named_before.get(k) != v}
        if isinstance(last_return, dict) and '_capture' in last_return:
            return_source = 'auto_capture'
        elif action.lower() == 'type' and model and self.model_parser and self.model_parser.get_auto_capture(model, 'type'):
            return_source = 'auto_capture'
        elif action.lower() == 'evaluate':
            return_source = 'evaluate'
        elif action.lower() == 'get' and model == '' and resolved_data and not resolved_data.startswith(('#', '.', '//', 'css=', 'xpath=', 'id=', 'text=')):
            return_source = 'get_named'
        else:
            return_source = 'keyword_result'
        step_index = len(self._current_case_steps_log) + 1
        # 浏览器监控：收集本 step 内捕获的异常
        _collect_monitor = getattr(self.driver, 'collect_monitor_errors', None)
        _browser_errors = []
        if _collect_monitor is not None:
            try:
                _browser_errors = _collect_monitor() or []
            except Exception:
                pass
        if _browser_errors:
            logger.warning("[BrowserMonitor] step %s 捕获 %d 条异常: %s",
                           _monitor_step_id, len(_browser_errors),
                           "; ".join(e.get('text') or e.get('message', '') for e in _browser_errors[:3]))
        self._current_case_steps_log.append({
            'index': step_index,
            'action': action,
            'model': model,
            'phase': step_type,
            'status': 'ok',
            'return_source': return_source,
            'return_value': last_return,
            'named_writes': named_writes,
            'browser_monitor': _browser_errors,
        })

        # 报告收集器：记录步骤
        if getattr(self, 'report_collector', None):
            self.report_collector.record_step({
                'index': step_index,
                'action': action,
                'model': model,
                'data': resolved_data,
                'status': 'ok',
                'return_value': last_return,
                'browser_monitor': _browser_errors,
            })

        if action_key == 'close':
            if self._active_recording_backend in self._DRIVER_RECORDING_BACKENDS:
                self._finalize_current_playwright_segment(getattr(self, '_current_case_id', 'unknown'))
            self._driver_closed = True
            logger.info("浏览器已关闭")

        if self.keyword_engine.driver is not self.driver:
            self.driver = self.keyword_engine.driver
            self._driver_closed = False

        if self.auto_screenshot_on_step and not self._driver_closed and action_key not in ('close', 'wait', 'db'):
            self._auto_screenshot(step_type)

        # 步骤等待：优先使用 case 级别的 step_wait，否则使用全局 default_wait_time
        wait_time = 0.0
        if hasattr(self, '_current_case_step_wait') and self._current_case_step_wait:
            try:
                wait_time = float(self._current_case_step_wait) / 1000.0  # 毫秒转秒
            except (ValueError, TypeError):
                wait_time = self.default_wait_time
        else:
            wait_time = self.default_wait_time

        if wait_time > 0 and action.lower() not in ('wait', 'close'):
            logger.debug(f"步骤等待 {wait_time}s")
            time.sleep(wait_time)

        # 步骤完成后清空叠加文字
        if getattr(self, '_active_recording_backend', None) == "screen" and getattr(self, '_screen_recorder', None) is not None:
            self._screen_recorder.set_step(None)

    def _auto_screenshot(self, step_type: str) -> None:
        """步骤执行后自动截图"""
        try:
            if not self.result_writer.current_run_dir:
                return

            self._step_index = getattr(self, '_step_index', 0) + 1
            case_id = getattr(self, '_current_case_id', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            scenario_id = getattr(self, '_current_scenario_id', None)
            scenario_title = getattr(self, '_current_scenario_title', None)

            if scenario_id:
                # 场景步骤：存入 screenshots/{caseid}_{scenarioid}_{scenariotitle}/
                safe_title = re.sub(r'[^\w一-鿿-]', '_', scenario_title or '').strip('_')
                folder_name = f"{case_id}_{scenario_id}"
                if safe_title:
                    folder_name = f"{folder_name}_{safe_title}"
                screenshot_dir = self.result_writer.current_run_dir / "screenshots" / folder_name
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{self._step_index:02d}_{timestamp}.png"
            else:
                # 非场景步骤：直接存 screenshots/
                screenshot_dir = self.result_writer.current_run_dir / "screenshots"
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                safe_phase = re.sub(r'[/\\]', '_', step_type)
                filename = f"{case_id}_{self._step_index:02d}_{safe_phase}_{timestamp}.png"

            path = screenshot_dir / filename
            # 移动端 self.driver 可能是 web 占位，优先用录像/关键字引擎的活跃 driver
            shot_driver = getattr(self, "_recording_driver", None) or self.driver
            if not hasattr(shot_driver, "screenshot"):
                shot_driver = getattr(self.keyword_engine, "driver", self.driver)
            ok = shot_driver.screenshot(str(path))
            logger.debug(f"步骤截图: {path}")
            # 记录相对路径到最近一条 step log，供报告每步内联展示
            if ok and getattr(self, "_current_case_steps_log", None):
                self._current_case_steps_log[-1]["screenshot"] = self._relative_run_path(str(path))
        except Exception as e:
            logger.debug(f"自动截图失败: {e}")

    def close(self):
        """关闭资源"""
        self.case_parser.close()
        self.data_manager.close()
        self.global_parser.close()

        for name, conn in self.keyword_engine._db_connections.items():
            try:
                conn.close()
            except Exception as e:
                logger.debug(f"关闭数据库连接 {name} 时出错: {e}")
        self.keyword_engine._db_connections.clear()

        if getattr(self, "_active_recording_backend", None):
            self._stop_case_recording(getattr(self, '_current_case_id', 'unknown'))

        if not self._driver_closed and self.driver:
            try:
                self.driver.close()
            except Exception as e:
                logger.debug(f"关闭驱动时出错: {e}")
