"""SKI 执行引擎 - 完整的测试用例执行器

v3.0+: 基于 XML 用例文件和目录结构，替代原 Excel 单文件模式。

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
import time
import copy
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Deque
from core.model_parser import ModelParser
from core.data_table_parser import DataTableParser
from core.global_value_parser import GlobalValueParser
from core.case_parser import CaseParser
from core.result_writer import ResultWriter, write_execution_summary
from core.config_manager import ConfigManager
from data.data_resolver import DataResolver
from core.keyword_engine import KeywordEngine
from core.dynamic_executor import DynamicExecutor
from drivers.base_driver import BaseDriver

from core.exceptions import DriverStoppedError, is_critical_error
from core.runtime_control import (
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

    def __init__(
        self,
        case_path: str,
        driver: BaseDriver,
        config: Optional[ConfigManager] = None,
        driver_factory: Optional[Callable[[], BaseDriver]] = None,
        module_dir: Optional[str] = None,
        runtime_control: Optional[BaseRuntimeControl] = None,
    ):
        """初始化 SKI 执行器

        Args:
            case_path: case XML 文件路径或 case/ 目录路径
            driver: 驱动实例
            config: 配置管理器实例（可选）
            driver_factory: 驱动工厂函数（可选）
            module_dir: 测试模块目录路径（可选，自动推导）
            runtime_control: 运行时控制队列（暂停/插入/终止）；默认无操作
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

                logger.info("驱动重新创建成功")
            else:
                raise DriverStoppedError(
                    "驱动已关闭且未提供 driver_factory，无法重新创建驱动"
                )

    def execute_all_cases(self):
        """执行所有用例，完成后批量回填结果"""
        cases = self.case_parser.parse_cases()
        results = []
        case_count = 0
        total_cases = len(cases)

        # 初始化结果目录（用于步骤截图）
        self.result_writer._init_run_dir()

        for case in cases:
            case_count += 1
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

            except DriverStoppedError as e:
                logger.critical(f"驱动已停止: {e}")
                results.append({
                    'case_id': case['case_id'],
                    'title': case.get('title', ''),
                    'status': 'FAIL',
                    'execution_time': 0,
                    'error': f'驱动已停止: {str(e)}',
                    'screenshot_path': '',
                })

        self.result_writer.write_results(results)
        return results

    def execute_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个用例（三阶段：预处理 → 用例 → 后处理）。

        每阶段内为多个 test_step，顺序执行。
        - 预处理失败：跳过用例阶段，仍执行后处理。
        - 用例阶段失败：仍执行后处理（清理/关闭等）。
        - 后处理失败：记为失败。
        """
        start = time.time()
        screenshot_path = None
        self._current_case_steps_log = []
        resources_snapshot = self._snapshot_runtime_resources()

        # 保存当前 case 的 step_wait 配置（优先级高于全局配置）
        self._current_case_step_wait = case.get('step_wait')

        try:
            self._current_case_id = case['case_id']
            self._step_index = 0
            self._runtime_stopped_graceful = False

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
                return self._case_result_force_terminated(case, start, e)
            except Exception as e:
                logger.error(f"预处理失败: {e}")
                _merge_error(e)

            # 用例阶段（仅当预处理未失败且未优雅终止时执行）
            if err is None and not self._runtime_stopped_graceful:
                try:
                    self._run_steps(test_steps, '用例')
                except ForceRunTermination as e:
                    return self._case_result_force_terminated(case, start, e)
                except Exception as e:
                    logger.error(f"用例阶段失败: {e}")
                    _merge_error(e)

            # 后处理：无论预处理/用例是否失败均执行（除非强制终止已返回）
            try:
                self._run_steps(post_steps, '后处理')
            except ForceRunTermination as e:
                return self._case_result_force_terminated(case, start, e)
            except Exception as e:
                logger.error(f"后处理失败: {e}")
                _merge_error(e)

            if err is not None:
                # 只有界面类型的用例失败时才截图
                component_type = case.get('component_type', '界面')
                if self.auto_screenshot and not self._driver_closed and component_type == '界面':
                    screenshot_path = self._take_failure_screenshot(case['case_id'])
                if self.result_writer.current_run_dir:
                    write_execution_summary(
                        self.result_writer.current_run_dir,
                        case['case_id'],
                        self._current_case_steps_log,
                        dict(self.keyword_engine._context.named),
                    )
                return {
                    'case_id': case['case_id'],
                    'title': case.get('title', ''),
                    'status': 'FAIL',
                    'execution_time': round(time.time() - start, 3),
                    'error': str(err),
                    'screenshot_path': screenshot_path or '',
                }

            if self._runtime_stopped_graceful:
                if self.result_writer.current_run_dir:
                    write_execution_summary(
                        self.result_writer.current_run_dir,
                        case['case_id'],
                        self._current_case_steps_log,
                        dict(self.keyword_engine._context.named),
                    )
                return {
                    'case_id': case['case_id'],
                    'title': case.get('title', ''),
                    'status': 'SKIP',
                    'execution_time': round(time.time() - start, 3),
                    'error': 'runtime terminate (graceful)',
                    'screenshot_path': '',
                }

            if self.result_writer.current_run_dir:
                write_execution_summary(
                    self.result_writer.current_run_dir,
                    case['case_id'],
                    self._current_case_steps_log,
                    dict(self.keyword_engine._context.named),
                )
            return {
                'case_id': case['case_id'],
                'title': case.get('title', ''),
                'status': 'PASS',
                'execution_time': round(time.time() - start, 3),
            }
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
        """顺序执行某阶段内全部 test_step；支持运行时 insert 扩展队列、条件和循环。"""
        dq = deque([s for s in steps if s.get('action') or s.get('type')])
        self._phase_runtime_seq = 0
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

            # 处理条件步骤
            if step.get('type') == 'if':
                condition = step.get('condition', '')
                try:
                    evaluated = self.dynamic_executor.evaluate_condition(
                        condition, driver=self.driver
                    )
                except Exception as e:
                    # 条件评估失败：友好提示 + 截图
                    screenshot_path = self._take_failure_screenshot(
                        f"if_cond_failed_{hash(condition) & 0xFFFFFFFF:08x}"
                    )
                    logger.warning(
                        f"[IF] ⚠️ 条件无法评估: condition={condition}\n"
                        f"   错误: {e}\n"
                        f"   截图: {screenshot_path}\n"
                        f"   建议: Agent 检查条件语法或页面状态\n"
                        f"   可用操作: 调整条件 / 跳过此分支 / 插入 cleanup 步骤"
                    )
                    logger.warning(f"  [{self._phase_runtime_seq}] if ({condition}) → 评估失败（跳过）")
                    continue

                if evaluated:
                    logger.info(f"  [{self._phase_runtime_seq}] if ({condition}) → True")
                    for sub_step in step.get('steps', []):
                        self.execute_step(sub_step, phase_label)
                else:
                    else_steps = step.get('else_steps', [])
                    if else_steps:
                        logger.info(f"  [{self._phase_runtime_seq}] if ({condition}) → False → else")
                        for sub_step in else_steps:
                            self.execute_step(sub_step, phase_label)
                    else:
                        logger.debug(f"  [{self._phase_runtime_seq}] if ({condition}) → False (无 else 跳过)")
            # 处理循环步骤
            elif step.get('type') == 'loop':
                loop_range = step.get('range', '')
                var_name = step.get('var', 'item')
                items = self.dynamic_executor.parse_loop_range(loop_range)
                logger.info(f"  [{self._phase_runtime_seq}] loop {var_name} in {loop_range} ({len(items)} 次)")
                for idx, item in enumerate(items, 1):
                    self.dynamic_executor.set_variable(var_name, item)
                    logger.debug(f"    循环 [{idx}/{len(items)}]: {var_name}={item}")
                    for sub_step in step.get('steps', []):
                        self.execute_step(sub_step, phase_label)
            # 普通步骤
            else:
                logger.debug(f"  [{self._phase_runtime_seq}] {step['action']}")
                self.execute_step(step, phase_label)

            if self._drain_runtime_at_boundary(dq):
                return

    def _take_failure_screenshot(self, case_id: str) -> Optional[str]:
        """在用例失败时自动截图"""
        try:
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

    def execute_step(self, step: Dict[str, str], step_type: str = ""):
        """执行单个步骤"""
        action = step['action']
        model = step['model']
        data = step['data']

        resolved_data = self.data_resolver.resolve(data)
        history_before = len(self.keyword_engine._context.history)
        named_before = dict(self.keyword_engine._context.named)

        if data and resolved_data != data:
            logger.debug(f"数据解析: '{data}' -> '{resolved_data}'")

        # 特殊处理 set 动作：将变量同步到动态执行器
        if action.lower() == 'set':
            params = {'var_name': model, 'value': resolved_data}
            self.keyword_engine.execute(action, params)
            # 同步到动态执行器
            if hasattr(self, 'dynamic_executor'):
                self.dynamic_executor.set_variable(model, resolved_data)
        else:
            params = {'model': model, 'data': resolved_data}
            self.keyword_engine.execute(action, params)

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
        self._current_case_steps_log.append({
            'index': len(self._current_case_steps_log) + 1,
            'action': action,
            'model': model,
            'phase': step_type,
            'status': 'ok',
            'return_source': return_source,
            'return_value': last_return,
            'named_writes': named_writes,
        })

        if action.lower() == 'close':
            self._driver_closed = True
            logger.info("浏览器已关闭")

        if self.keyword_engine.driver is not self.driver:
            self.driver = self.keyword_engine.driver
            self._driver_closed = False

        if self.auto_screenshot_on_step and not self._driver_closed and action.lower() not in ('close', 'wait', 'DB'):
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

    def _auto_screenshot(self, step_type: str) -> None:
        """步骤执行后自动截图"""
        try:
            if not self.result_writer.current_run_dir:
                return

            screenshot_dir = self.result_writer.current_run_dir / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            self._step_index = getattr(self, '_step_index', 0) + 1
            case_id = getattr(self, '_current_case_id', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{case_id}_{self._step_index:02d}_{step_type}_{timestamp}.png"
            path = screenshot_dir / filename
            self.driver.screenshot(str(path))
            logger.debug(f"步骤截图: {path}")
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

        if not self._driver_closed and self.driver:
            try:
                self.driver.close()
            except Exception as e:
                logger.debug(f"关闭驱动时出错: {e}")
