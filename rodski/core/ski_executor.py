"""SKI 执行引擎 - 完整的测试用例执行器"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
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


class SKIExecutor:
    """SKI 测试执行引擎
    
    支持功能:
    - 用例解析和执行
    - 数据驱动测试
    - 失败自动截图
    - 结果回填到 Excel
    - 支持两种用例执行模式:
      1. 独立模式: 每个用例有 close，执行完后关闭浏览器，下一个用例重新启动
      2. 共享模式: 用例没有 close，后续用例复用同一个浏览器 session
    """
    
    def __init__(
        self, 
        case_file: str, 
        model_file: str, 
        driver: BaseDriver, 
        config: Optional[ConfigManager] = None,
        driver_factory: Optional[Callable[[], BaseDriver]] = None
    ):
        """初始化 SKI 执行器
        
        Args:
            case_file: 用例文件路径
            model_file: 模型文件路径
            driver: 驱动实例
            config: 配置管理器实例（可选，不传则使用默认配置）
            driver_factory: 驱动工厂函数，用于在驱动关闭后重新创建驱动（可选）
        """
        self.case_file = Path(case_file)
        self.model_file = Path(model_file)
        self.driver = driver
        self.driver_factory = driver_factory
        self._driver_closed = False  # 跟踪驱动是否被 close 关闭

        # 加载配置
        self.config = config or ConfigManager()
        self.auto_screenshot = self.config.get("auto_screenshot_on_failure", True)
        self.screenshot_dir = Path(self.config.get("screenshot_dir", "screenshots"))

        # 初始化解析器
        self.model_parser = ModelParser(str(model_file))
        self.data_manager = DataTableParser(str(case_file))
        self.data_manager.parse_all_tables()
        self.global_parser = GlobalValueParser(str(case_file))
        self.global_vars = self.global_parser.parse()
        self.case_parser = CaseParser(str(case_file))

        # 读取默认等待时间
        default_wait_str = self.global_vars.get('DefaultValue', {}).get('WaitTime', '0')
        try:
            self.default_wait_time = float(default_wait_str)
        except (ValueError, TypeError):
            self.default_wait_time = 0.0

        # 初始化关键字引擎（先于 DataResolver，因为 DataResolver 需要引用 return_provider）
        self.keyword_engine = KeywordEngine(
            driver, 
            model_parser=self.model_parser,
            data_manager=self.data_manager,
            global_vars=self.global_vars,
            case_file=str(self.case_file)
        )

        # 初始化数据解析器，连接 KeywordEngine 的返回值作为 Return 引用源
        self.data_resolver = DataResolver(
            data_manager=self.data_manager,
            global_vars=self.global_vars,
            return_provider=self.keyword_engine.get_return
        )

        # 初始化结果回填器
        self.result_writer = ResultWriter(str(case_file))
        
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
                
                # 重新初始化关键字引擎
                self.keyword_engine = KeywordEngine(
                    self.driver,
                    model_parser=self.model_parser,
                    data_manager=self.data_manager,
                    global_vars=self.global_vars,
                    case_file=str(self.case_file)
                )
                
                logger.info("驱动重新创建成功")
            else:
                raise DriverStoppedError(
                    "驱动已关闭且未提供 driver_factory，无法重新创建驱动"
                )

    def execute_all_cases(self):
        """执行所有用例，完成后批量回填结果
        
        支持两种模式:
        1. 独立模式: 用例有 close，执行完后关闭浏览器，下一个用例自动重新启动
        2. 共享模式: 用例没有 close，后续用例复用同一个浏览器 session
        """
        cases = self.case_parser.parse_cases()
        results = []
        case_count = 0
        total_cases = len(cases)

        for case in cases:
            case_count += 1
            # 检查驱动是否可用，如果已关闭则重新创建
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
                
                # 显示执行结果
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
        """执行单个用例，记录执行时间
        
        Args:
            case: 用例字典，包含 case_id, title, pre_process, test_step 等字段
            
        Returns:
            执行结果字典
        """
        start = time.time()
        screenshot_path = None
        
        try:
            # 预处理
            if case['pre_process']['action']:
                print(f"   📌 预处理: {case['pre_process']['action']}")
                self.execute_step(case['pre_process'], '预处理')

            # 测试步骤
            if case['test_step']['action']:
                print(f"   📌 测试步骤: {case['test_step']['action']}")
                self.execute_step(case['test_step'], '测试步骤')

            # 预期结果
            if case['expected_result']['action']:
                print(f"   📌 预期结果: {case['expected_result']['action']}")
                self.execute_step(case['expected_result'], '预期结果')

            # 后处理
            if case['post_process']['action']:
                print(f"   📌 后处理: {case['post_process']['action']}")
                self.execute_step(case['post_process'], '后处理')

            return {
                'case_id': case['case_id'],
                'title': case.get('title', ''),
                'status': 'PASS',
                'execution_time': round(time.time() - start, 3),
            }
        except Exception as e:
            logger.error(f"用例执行失败: {e}")
            print(f"   ❌ 错误: {e}")
            
            # 失败时自动截图
            if self.auto_screenshot and not self._driver_closed:
                screenshot_path = self._take_failure_screenshot(case['case_id'])
            
            return {
                'case_id': case['case_id'],
                'title': case.get('title', ''),
                'status': 'FAIL',
                'execution_time': round(time.time() - start, 3),
                'error': str(e),
                'screenshot_path': screenshot_path or '',
            }

    def _take_failure_screenshot(self, case_id: str) -> Optional[str]:
        """在用例失败时自动截图
        
        Args:
            case_id: 用例ID，用于生成截图文件名
            
        Returns:
            截图文件路径，失败时返回 None
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{case_id}_{timestamp}_failure.png"
            screenshot_path = self.screenshot_dir / filename
            
            # 调用驱动的截图方法
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
        """执行单个步骤
        
        Args:
            step: 步骤字典，包含 action, model, data
            step_type: 步骤类型（预处理/测试步骤/预期结果/后处理）
        
        特殊处理 close 关键字：执行后标记驱动已关闭
        每个步骤执行后自动应用 GlobalValue.DefaultValue.WaitTime 默认等待
        """
        action = step['action']
        model = step['model']
        data = step['data']

        # 解析数据引用
        resolved_data = self.data_resolver.resolve(data)
        
        # 打印数据解析结果
        if data and resolved_data != data:
            logger.debug(f"数据解析: '{data}' -> '{resolved_data}'")

        # 构建参数
        params = {'model': model, 'data': resolved_data}

        # 执行关键字
        try:
            self.keyword_engine.execute(action, params)
        except Exception as e:
            raise
        
        # 特殊处理：close 关键字执行后标记驱动已关闭
        if action.lower() == 'close':
            self._driver_closed = True
            logger.info("浏览器已关闭")
        
        # 应用默认等待时间（wait/close 关键字除外）
        if self.default_wait_time > 0 and action.lower() not in ('wait', 'close'):
            logger.debug(f"默认等待 {self.default_wait_time}s")
            time.sleep(self.default_wait_time)

    def close(self):
        """关闭资源"""
        self.case_parser.close()
        self.data_manager.close()
        self.global_parser.close()
        
        # 确保驱动被关闭
        if not self._driver_closed and self.driver:
            try:
                self.driver.close()
            except Exception as e:
                logger.debug(f"关闭驱动时出错: {e}")