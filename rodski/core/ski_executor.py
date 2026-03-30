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
from core.result_writer import ResultWriter
from core.config_manager import ConfigManager
from data.data_resolver import DataResolver
from core.keyword_engine import KeywordEngine
from drivers.base_driver import BaseDriver
from core.condition_evaluator import ConditionEvaluator
from core.loop_executor import LoopParser, LoopExecutor
from core.dynamic_steps import DynamicStep, TriggerPoint, ExecutionContext

try:
    from vision.screen_recorder import ScreenRecorder
except ImportError:
    ScreenRecorder = None  # 未安装录屏依赖时优雅降级

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

        # 录屏配置
        screen_record_cfg = self.config.get("screen_record", {}) or {}
        self._record_enabled = screen_record_cfg.get("enabled", False)
        self._record_fps = screen_record_cfg.get("fps", 10)
        self._record_max_duration = screen_record_cfg.get("max_duration", 600)
        self._record_output_dir = screen_record_cfg.get(
            "output_dir", "screenshots"
        )
        self._recorder: Optional["ScreenRecorder"] = None
        self._current_recording_path: Optional[str] = None

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

        # 初始化结果写入器
        self.result_writer = ResultWriter(str(self.result_dir))

        self.runtime_control: BaseRuntimeControl = runtime_control or BaseRuntimeControl()
        self._runtime_stopped_graceful = False

        # 初始化条件评估器和循环执行器
        self.condition_evaluator = ConditionEvaluator()
        self.loop_executor = LoopExecutor(self)
        self._variables: Dict[str, Any] = {}
        self._dynamic_steps: List[DynamicStep] = []

        # Long-running stability
        self._step_count = 0
        self._browser_restart_interval = self.config.get("browser_restart_interval", 50)
        self._memory_check_interval = 10
        self._memory_threshold_mb = 100
        try:
            import tracemalloc
            tracemalloc.start()
            self._tracemalloc = tracemalloc
        except ImportError:
            self._tracemalloc = None

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
                print(f"\n🔄 用例 {case_count}/{total_cases}: 驱动已关闭，重新创建浏览器...")
                try:
                    self._ensure_driver_alive()
                    print(f"✅ 新浏览器已启动")
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

            print(f"\n📍 执行用例 {case_count}/{total_cases}: {case['case_id']} - {case['title']}")
            try:
                result = self.execute_case(case)
                results.append(result)

                st = result.get('status', '').upper()
                if st == 'PASS':
                    status = "✅ PASS"
                elif st == 'SKIP':
                    status = "⏹️ SKIP"
                else:
                    status = "❌ FAIL"
                print(f"   {status} ({result['execution_time']}s)")
                if result.get('error'):
                    print(f"   错误: {result['error']}")

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
        resources_snapshot = self._snapshot_runtime_resources()

        # 保存当前 case 的 step_wait 配置（优先级高于全局配置）
        self._current_case_step_wait = case.get('step_wait')

        # 自动录屏：如果配置开启且 ScreenRecorder 可用
        case_id = case['case_id']
        recording_path = None
        if self._record_enabled and ScreenRecorder is not None:
            try:
                self._recorder = ScreenRecorder(
                    output_dir=str(self.module_dir / self._record_output_dir),
                    fps=self._record_fps,
                    max_duration=self._record_max_duration,
                )
                recording_path = self._recorder.start(session_id=case_id)
                self._current_recording_path = recording_path
                logger.info(f"用例录屏已启动: {recording_path}")
            except Exception as e:
                logger.warning(f"启动录屏失败: {e}")
                self._recorder = None

        # 用于最终返回的结果字典（方便 finally 块统一处理）
        result: Dict[str, Any] = {
            'case_id': case_id,
            'title': case.get('title', ''),
            'status': 'PASS',
            'execution_time': 0.0,
            'error': '',
            'screenshot_path': '',
            'recording_path': '',
        }

        try:
            self._current_case_id = case_id
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
                result = self._case_result_dict(
                    case, start, 'FAIL', str(e), screenshot_path, recording_path
                )
                return result
            except Exception as e:
                logger.error(f"预处理失败: {e}")
                print(f"   ❌ 预处理错误: {e}")
                _merge_error(e)

            # 用例阶段（仅当预处理未失败且未优雅终止时执行）
            if err is None and not self._runtime_stopped_graceful:
                try:
                    self._run_steps(test_steps, '用例')
                except ForceRunTermination as e:
                    result = self._case_result_dict(
                        case, start, 'FAIL', str(e), screenshot_path, recording_path
                    )
                    return result
                except Exception as e:
                    logger.error(f"用例阶段失败: {e}")
                    print(f"   ❌ 用例错误: {e}")
                    _merge_error(e)

            # 后处理：无论预处理/用例是否失败均执行（除非强制终止已返回）
            try:
                self._run_steps(post_steps, '后处理')
            except ForceRunTermination as e:
                result = self._case_result_dict(
                    case, start, 'FAIL', str(e), screenshot_path, recording_path
                )
                return result
            except Exception as e:
                logger.error(f"后处理失败: {e}")
                print(f"   ❌ 后处理错误: {e}")
                _merge_error(e)

            if err is not None:
                # 只有界面类型的用例失败时才截图
                component_type = case.get('component_type', '界面')
                if self.auto_screenshot and not self._driver_closed and component_type == '界面':
                    screenshot_path = self._take_failure_screenshot(case_id)
                result = self._case_result_dict(
                    case, start, 'FAIL', str(err), screenshot_path, recording_path
                )
                return result

            if self._runtime_stopped_graceful:
                result = self._case_result_dict(
                    case, start, 'SKIP', 'runtime terminate (graceful)',
                    screenshot_path, recording_path
                )
                return result

            # 正常通过
            result = self._case_result_dict(
                case, start, 'PASS', '', None, recording_path
            )
            return result

        finally:
            # 停止录屏
            if self._recorder is not None:
                try:
                    final_recording_path = self._recorder.stop()
                    if final_recording_path:
                        result['recording_path'] = final_recording_path
                    logger.info(f"用例录屏已保存: {final_recording_path}")
                except Exception as e:
                    logger.warning(f"停止录屏失败: {e}")
                self._recorder = None

            self._restore_runtime_resources(resources_snapshot)

    def _case_result_dict(
        self,
        case: Dict[str, Any],
        start: float,
        status: str,
        error: str,
        screenshot_path: Optional[str],
        recording_path: Optional[str],
    ) -> Dict[str, Any]:
        """构建用例结果字典"""
        return {
            'case_id': case['case_id'],
            'title': case.get('title', ''),
            'status': status,
            'execution_time': round(time.time() - start, 3),
            'error': error,
            'screenshot_path': screenshot_path or '',
            'recording_path': recording_path or '',
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

    def _recycle_browser_if_needed(self) -> None:
        """定期回收浏览器实例，避免内存泄漏"""
        try:
            current_url = ""
            try:
                if hasattr(self.driver, 'current_url'):
                    current_url = self.driver.current_url() or ""
            except Exception:
                pass
            logger.info(f"[BrowserRecycler] 开始回收浏览器，step={self._step_count}, url={current_url}")
            self.driver.restart()
            if current_url:
                time.sleep(1)
                try:
                    self.driver.navigate(current_url)
                    logger.info(f"[BrowserRecycler] 浏览器已恢复，url={current_url}")
                except Exception as e:
                    logger.warning(f"[BrowserRecycler] 恢复URL失败: {e}")
        except Exception as e:
            logger.warning(f"[BrowserRecycler] 浏览器回收失败: {e}")

    def _check_memory_and_gc(self) -> None:
        """监控内存使用，超标时触发GC"""
        if self._tracemalloc is None:
            return
        try:
            current = self._tracemalloc.get_traced_memory()[0] / (1024 * 1024)
            delta = current - getattr(self, '_last_memory_mb', current)
            if delta > self._memory_threshold_mb:
                import gc
                gc.collect()
                logger.info(f"[MemoryMonitor] step={self._step_count}, current={current:.1f}MB, delta=+{delta:.1f}MB, GC triggered")
            else:
                logger.debug(f"[MemoryMonitor] step={self._step_count}, current={current:.1f}MB, delta=+{delta:.1f}MB")
            self._last_memory_mb = current
        except Exception as e:
            logger.debug(f"[MemoryMonitor] 内存监控失败: {e}")

    def _run_steps(self, steps: List[Dict[str, str]], phase_label: str) -> None:
        """顺序执行某阶段内全部 test_step；支持运行时 insert 扩展队列。"""
        dq = deque([s for s in steps if s.get('action')])
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
            print(f"   📌 {phase_label} [{self._phase_runtime_seq}]: {step['action']}")
            self.execute_step(step, phase_label)

            self._step_count += 1
            # 浏览器定期回收
            if self._browser_restart_interval > 0 and self._step_count % self._browser_restart_interval == 0:
                self._recycle_browser_if_needed()
            # 内存监控
            if self._step_count % self._memory_check_interval == 0:
                self._check_memory_and_gc()

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
        condition = step.get('condition', '')
        loop = step.get('loop', '')

        # Check condition
        if condition:
            if not self.condition_evaluator.evaluate(condition, self._variables):
                logger.info(f"步骤跳过 (条件不满足): {action}")
                return

        # Execute dynamic steps (pre_step)
        self._inject_steps(TriggerPoint.PRE_STEP, None)

        resolved_data = self.data_resolver.resolve(data)

        if data and resolved_data != data:
            logger.debug(f"数据解析: '{data}' -> '{resolved_data}'")

        params = {'model': model, 'data': resolved_data}

        # Check loop
        if loop:
            loop_config = LoopParser.parse(loop, self._variables)
            self.loop_executor.execute_loop(step, loop_config)
            self._variables["last_result"] = {"status": "pass", "loop": True}
        else:
            self.keyword_engine.execute(action, params)
            self._variables["last_result"] = {"status": "pass", "action": action}

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

        # Execute dynamic steps (post_step)
        self._inject_steps(TriggerPoint.POST_STEP, None)

    def _inject_steps(self, trigger_point: TriggerPoint, context: Optional[ExecutionContext]) -> None:
        """Inject and execute dynamic steps at trigger point"""
        steps_to_execute = [s for s in self._dynamic_steps if s.position == trigger_point]
        for dynamic_step in steps_to_execute:
            if dynamic_step.condition:
                if not self.condition_evaluator.evaluate(dynamic_step.condition, self._variables):
                    continue
            try:
                params = dynamic_step.params.copy()
                self.keyword_engine.execute(dynamic_step.keyword, params)
            except Exception as e:
                logger.warning(f"Dynamic step failed: {e}")
                if not dynamic_step.retry_on_fail:
                    raise

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
