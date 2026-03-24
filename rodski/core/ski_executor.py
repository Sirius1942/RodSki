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
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from core.model_parser import ModelParser
from core.data_table_parser import DataTableParser
from core.global_value_parser import GlobalValueParser
from core.case_parser import CaseParser
from core.result_writer import ResultWriter
from core.config_manager import ConfigManager
from data.data_resolver import DataResolver
from core.keyword_engine import KeywordEngine
from drivers.base_driver import BaseDriver

from core.exceptions import DriverStoppedError, is_critical_error

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
    ):
        """初始化 SKI 执行器

        Args:
            case_path: case XML 文件路径或 case/ 目录路径
            driver: 驱动实例
            config: 配置管理器实例（可选）
            driver_factory: 驱动工厂函数（可选）
            module_dir: 测试模块目录路径（可选，自动推导）
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
        self.screenshot_dir = Path(self.config.get("screenshot_dir", "screenshots"))

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

        # 确保截图目录存在
        if self.auto_screenshot:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

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

                status = "✅ PASS" if result['status'] == 'PASS' else "❌ FAIL"
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

        self._current_case_id = case['case_id']
        self._step_index = 0

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
        except Exception as e:
            logger.error(f"预处理失败: {e}")
            print(f"   ❌ 预处理错误: {e}")
            _merge_error(e)

        # 用例阶段（仅当预处理未失败时执行）
        if err is None:
            try:
                self._run_steps(test_steps, '用例')
            except Exception as e:
                logger.error(f"用例阶段失败: {e}")
                print(f"   ❌ 用例错误: {e}")
                _merge_error(e)

        # 后处理：无论预处理/用例是否失败均执行
        try:
            self._run_steps(post_steps, '后处理')
        except Exception as e:
            logger.error(f"后处理失败: {e}")
            print(f"   ❌ 后处理错误: {e}")
            _merge_error(e)

        if err is not None:
            if self.auto_screenshot and not self._driver_closed:
                screenshot_path = self._take_failure_screenshot(case['case_id'])
            return {
                'case_id': case['case_id'],
                'title': case.get('title', ''),
                'status': 'FAIL',
                'execution_time': round(time.time() - start, 3),
                'error': str(err),
                'screenshot_path': screenshot_path or '',
            }

        return {
            'case_id': case['case_id'],
            'title': case.get('title', ''),
            'status': 'PASS',
            'execution_time': round(time.time() - start, 3),
        }

    def _run_steps(self, steps: List[Dict[str, str]], phase_label: str) -> None:
        """顺序执行某阶段内全部 test_step。"""
        n = len(steps)
        for i, step in enumerate(steps, 1):
            if not step.get('action'):
                continue
            print(f"   📌 {phase_label} [{i}/{n}]: {step['action']}")
            self.execute_step(step, phase_label)

    def _take_failure_screenshot(self, case_id: str) -> Optional[str]:
        """在用例失败时自动截图"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{case_id}_{timestamp}_failure.png"
            screenshot_path = self.screenshot_dir / filename

            success = self.driver.screenshot(str(screenshot_path))
            if success:
                logger.info(f"失败截图已保存: {screenshot_path}")
                return str(screenshot_path)
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

        if data and resolved_data != data:
            logger.debug(f"数据解析: '{data}' -> '{resolved_data}'")

        params = {'model': model, 'data': resolved_data}

        self.keyword_engine.execute(action, params)

        if action.lower() == 'close':
            self._driver_closed = True
            logger.info("浏览器已关闭")

        if self.keyword_engine.driver is not self.driver:
            self.driver = self.keyword_engine.driver
            self._driver_closed = False

        if not self._driver_closed and action.lower() not in ('close', 'wait', 'DB'):
            self._auto_screenshot(step_type)

        if self.default_wait_time > 0 and action.lower() not in ('wait', 'close'):
            logger.debug(f"默认等待 {self.default_wait_time}s")
            time.sleep(self.default_wait_time)

    def _auto_screenshot(self, step_type: str) -> None:
        """步骤执行后自动截图"""
        try:
            self._step_index = getattr(self, '_step_index', 0) + 1
            case_id = getattr(self, '_current_case_id', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{case_id}_{self._step_index:02d}_{step_type}_{timestamp}.png"
            path = self.screenshot_dir / filename
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
