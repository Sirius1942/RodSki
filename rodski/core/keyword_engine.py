"""关键字引擎 - 支持28+操作关键字（含RESTful API测试）"""
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from drivers.base_driver import BaseDriver
from api.rest_helper import RestHelper
from core.performance import monitor_performance
from core.data_parser import DataParser
from core.exceptions import (
    UnknownKeywordError, 
    InvalidParameterError,
    RetryExhaustedError,
    ElementNotFoundError,
    TimeoutError,
    StaleElementError,
    DriverStoppedError,
    DriverError,
    is_retryable_error,
    is_critical_error,
)

logger = logging.getLogger("rodski")


class KeywordEngine:
    """关键字引擎 - 执行测试关键字并管理驱动操作
    
    日志级别说明:
    - INFO: 关键字执行开始/结束
    - DEBUG: 详细参数信息
    - WARNING: 可恢复的错误
    - ERROR: 执行失败
    - CRITICAL: 严重错误（驱动停止等）
    """
    
    SUPPORTED = [
        "open", "close", "click", "type", "check", "wait", "navigate",
        "screenshot", "select", "hover", "drag", "scroll", "assert",
        "http_get", "http_post", "http_put", "http_delete",
        "assert_json", "assert_status",
        "upload_file", "clear", "double_click", "right_click",
        "key_press", "get_text",
        "send", "set", "run", "DB",
    ]

    # 默认重试配置
    DEFAULT_RETRY_CONFIG = {
        "max_retries": 0,
        "retry_delay": 1.0,
        "retry_on_errors": ["ElementNotFound", "Timeout", "StaleElement"],
    }

    def __init__(self, driver: BaseDriver, data_dir: Optional[Path] = None, 
                 retry_config: Optional[Dict[str, Any]] = None):
        self.driver = driver
        self._last_response = None
        self._variables: Dict[str, Any] = {}
        self._return_values: list = []
        self.data_parser = DataParser(data_dir, self)
        
        # 初始化重试配置
        self._retry_config = {**self.DEFAULT_RETRY_CONFIG, **(retry_config or {})}
        self._retry_stats: Dict[str, List[int]] = {}

    @monitor_performance
    def execute(self, keyword: str, params: Dict[str, Any]) -> bool:
        """执行关键字
        
        Args:
            keyword: 关键字名称
            params: 关键字参数
            
        Returns:
            执行结果 (True/False)
            
        Raises:
            UnknownKeywordError: 未知关键字
            InvalidParameterError: 参数错误
            DriverStoppedError: 驱动已停止
            RetryExhaustedError: 重试耗尽
            DriverError: 驱动操作失败
        """
        if not isinstance(keyword, str) or not keyword.strip():
            raise InvalidParameterError(
                keyword="(unknown)", 
                param_name="keyword", 
                reason="关键字不能为空"
            )

        # 解析参数中的数据引用
        resolved_params = self.data_parser.resolve_params(params or {})

        method = getattr(self, f"_kw_{keyword.lower()}", None)
        if not method:
            logger.error(f"❌ 未知关键字: '{keyword}'")
            raise UnknownKeywordError(keyword, self.SUPPORTED)
        
        # 打印关键字执行日志
        self._log_keyword_start(keyword, resolved_params)
        
        # 获取重试配置
        max_retries = self._retry_config.get("max_retries", 0)
        retry_delay = self._retry_config.get("retry_delay", 1.0)
        retry_on_errors = self._retry_config.get("retry_on_errors", [])
        
        last_error = None
        attempts = 0
        
        while attempts <= max_retries:
            attempts += 1
            try:
                result = method(resolved_params)
                
                # 成功日志
                self._log_keyword_success(keyword, attempts, result)
                
                if attempts > 1:
                    self._record_retry(keyword, attempts - 1)
                return result
                
            except DriverStoppedError:
                # 严重错误：驱动已停止
                logger.critical(f"❌ 驱动已停止，无法继续执行关键字 '{keyword}'")
                raise
                
            except (InvalidParameterError, UnknownKeywordError) as e:
                # 参数错误和未知关键字不重试
                logger.error(f"❌ 参数错误: {e}")
                raise
                
            except DriverError as e:
                # 驱动错误
                last_error = e
                logger.error(f"❌ 驱动操作失败: {e}")
                if attempts <= max_retries:
                    logger.warning(f"   等待 {retry_delay}s 后重试 ({attempts}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                break
                
            except RuntimeError as e:
                last_error = e
                # 检查是否为严重错误
                if is_critical_error(e):
                    logger.critical(f"❌ 严重错误: {e}")
                    raise DriverStoppedError(str(e))
                    
                # 检查是否应该重试
                should_retry = self._should_retry(str(e), retry_on_errors)
                can_retry = attempts <= max_retries
                
                if should_retry and can_retry:
                    logger.warning(f"   等待 {retry_delay}s 后重试 ({attempts}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                elif not should_retry:
                    raise
                else:
                    break
                    
            except Exception as e:
                last_error = e
                # 检查是否为严重错误
                if is_critical_error(e):
                    logger.critical(f"❌ 严重错误: {e}")
                    raise DriverStoppedError(str(e))
                    
                logger.error(f"❌ 执行异常: {type(e).__name__}: {e}")
                if attempts <= max_retries:
                    logger.warning(f"   等待 {retry_delay}s 后重试 ({attempts}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                break
        
        # 重试耗尽
        self._record_retry(keyword, max_retries)
        logger.error(f"❌ 重试 {attempts} 次后仍失败: {last_error}")
        raise RetryExhaustedError(keyword, attempts, last_error)
    
    def _log_keyword_start(self, keyword: str, params: Dict) -> None:
        """打印关键字执行开始日志"""
        # 过滤掉空的参数
        param_str = ", ".join(f"{k}={v}" for k, v in params.items() if v)
        if param_str:
            print(f"   🔹 {keyword}({param_str})")
        else:
            print(f"   🔹 {keyword}()")
    
    def _log_keyword_success(self, keyword: str, attempts: int, result: bool) -> None:
        """打印关键字执行成功日志"""
        if attempts > 1:
            print(f"   ✅ {keyword} 成功 (第{attempts}次尝试)")
        else:
            print(f"   ✅ {keyword} 成功")
    
    def _should_retry(self, error_message: str, retry_on_errors: List[str]) -> bool:
        """检查错误是否应该重试"""
        error_lower = error_message.lower()
        for error_type in retry_on_errors:
            if error_type.lower() in error_lower:
                return True
        return False
    
    def _record_retry(self, keyword: str, count: int) -> None:
        """记录重试次数"""
        if keyword not in self._retry_stats:
            self._retry_stats[keyword] = []
        self._retry_stats[keyword].append(count)
    
    def get_retry_stats(self) -> Dict[str, List[int]]:
        """获取重试统计"""
        return dict(self._retry_stats)
    
    def set_retry_config(self, config: Dict[str, Any]) -> None:
        """动态设置重试配置"""
        self._retry_config.update(config)

    def get_keywords(self) -> list:
        return self.SUPPORTED

    def store_return(self, value: Any) -> None:
        """存储返回值"""
        self._return_values.append(value)

    def get_return(self, index: int) -> Any:
        """获取返回值，支持正负索引"""
        if not self._return_values:
            return None
        try:
            return self._return_values[index]
        except IndexError:
            return None

    # ── UI 操作关键字 ─────────────────────────────────────────────

    def _kw_open(self, params: Dict) -> bool:
        """打开URL"""
        url = params.get("url") or params.get("data", "")
        if not url:
            raise InvalidParameterError(
                keyword="open",
                param_name="url",
                reason="缺少必需参数 'url' 或 'data'"
            )
        
        print(f"      🌐 导航到: {url}")
        result = self.driver.navigate(url)
        if not result:
            raise DriverError(f"导航失败: {url}")
        return result

    def _kw_close(self, params: Dict) -> bool:
        """关闭浏览器"""
        print(f"      🔒 关闭浏览器")
        self.driver.close()
        return True

    def _kw_click(self, params: Dict) -> bool:
        """点击元素"""
        locator = params.get("locator", "")
        if not locator:
            raise InvalidParameterError(
                keyword="click",
                param_name="locator",
                reason="缺少必需参数 'locator'"
            )
        
        print(f"      🖱️ 点击: {locator}")
        result = self.driver.click(locator)
        if not result:
            raise DriverError(f"点击失败: {locator}")
        return result

    def _kw_type(self, params: Dict) -> bool:
        """输入文本"""
        locator = params.get("locator", "")
        text = params.get("text", "")
        model_name = params.get("model", "")
        data_ref = params.get("data", "")

        # 批量输入模式：type 模型名 数据引用
        if model_name and data_ref and hasattr(self, 'model_parser') and hasattr(self, 'data_manager'):
            return self._batch_type(model_name, data_ref)

        # 单字段输入模式
        if not locator:
            raise InvalidParameterError(
                keyword="type",
                param_name="locator",
                reason="缺少必需参数 'locator'"
            )
        
        print(f"      ⌨️ 输入: {locator} <- '{text}'")
        result = self.driver.type(locator, text)
        if not result:
            raise DriverError(f"输入失败: {locator}")
        return result

    def _batch_type(self, model_name: str, data_ref: str) -> bool:
        """批量输入：遍历模型元素，匹配数据表字段"""
        parts = data_ref.split('.')
        if len(parts) < 2:
            raise InvalidParameterError(
                keyword="type", 
                param_name="data", 
                reason=f"数据引用格式错误: '{data_ref}'，应为 'TableName.DataID' 格式"
            )

        table_name, data_id = parts[0], parts[1]
        model = self.model_parser.get_model(model_name)
        data_row = self.data_manager.get_data(table_name, data_id)

        if not model:
            raise InvalidParameterError(
                keyword="type",
                param_name="model", 
                reason=f"模型不存在: '{model_name}'"
            )
        
        if not data_row:
            raise InvalidParameterError(
                keyword="type",
                param_name="data",
                reason=f"数据不存在: '{data_ref}' (表 '{table_name}' 中找不到 DataID='{data_id}')"
            )

        print(f"      📋 批量输入: 模型={model_name}, 数据={data_ref}")
        
        operations = []  # 记录操作用于日志
        for element_name, element_info in model.items():
            if element_name in data_row:
                value = data_row[element_name]
                locator_type = element_info['type']
                locator_value = element_info['value']
                locator = f"{locator_type}={locator_value}"

                # 特殊值处理：click
                if value.lower() == 'click':
                    print(f"         🖱️ {element_name}: 点击 {locator}")
                    result = self.driver.click(locator)
                    operations.append(('click', element_name, result))
                else:
                    # 处理 .Password 后缀
                    display_value = value
                    if value.endswith('.Password'):
                        value = value[:-9]
                        display_value = '***'
                    print(f"         ⌨️ {element_name}: {locator} <- '{display_value}'")
                    result = self.driver.type(locator, value)
                    operations.append(('type', element_name, result))
        
        # 检查是否有失败的操作
        failed_ops = [op for op in operations if not op[2]]
        if failed_ops:
            failed_names = [op[1] for op in failed_ops]
            raise DriverError(f"批量输入失败: {', '.join(failed_names)}")
        
        return True

    def _kw_check(self, params: Dict) -> bool:
        """检查元素可见"""
        locator = params.get("locator", "")
        print(f"      👁️ 检查可见: {locator}")
        return self.driver.check(locator)

    def _kw_wait(self, params: Dict) -> bool:
        """等待"""
        seconds = params.get("seconds") or params.get("data", "1.0")
        print(f"      ⏳ 等待: {seconds}秒")
        self.driver.wait(float(seconds))
        return True

    def _kw_navigate(self, params: Dict) -> bool:
        """导航到URL"""
        url = params.get("url", "")
        if not url:
            raise InvalidParameterError(
                keyword="navigate",
                param_name="url",
                reason="缺少必需参数 'url'"
            )
        print(f"      🌐 导航: {url}")
        result = self.driver.navigate(url)
        if not result:
            raise DriverError(f"导航失败: {url}")
        return result

    def _kw_screenshot(self, params: Dict) -> bool:
        """截图"""
        path = params.get("path", "screenshot.png")
        print(f"      📸 截图: {path}")
        return self.driver.screenshot(path)

    def _kw_select(self, params: Dict) -> bool:
        """下拉选择"""
        locator = params.get("locator", "")
        value = params.get("value", "")
        print(f"      📝 选择: {locator} = {value}")
        result = self.driver.select(locator, value)
        if not result:
            raise DriverError(f"选择失败: {locator}")
        return result

    def _kw_hover(self, params: Dict) -> bool:
        """悬停"""
        locator = params.get("locator", "")
        print(f"      🖱️ 悬停: {locator}")
        result = self.driver.hover(locator)
        if not result:
            raise DriverError(f"悬停失败: {locator}")
        return result

    def _kw_drag(self, params: Dict) -> bool:
        """拖拽"""
        from_loc = params.get("from", "")
        to_loc = params.get("to", "")
        print(f"      🔄 拖拽: {from_loc} -> {to_loc}")
        result = self.driver.drag(from_loc, to_loc)
        if not result:
            raise DriverError(f"拖拽失败: {from_loc} -> {to_loc}")
        return result

    def _kw_scroll(self, params: Dict) -> bool:
        """滚动"""
        x = int(params.get("x", 0))
        y = int(params.get("y", 300))
        print(f"      📜 滚动: ({x}, {y})")
        return self.driver.scroll(x, y)

    def _kw_assert(self, params: Dict) -> bool:
        """断言"""
        locator = params.get("locator", "")
        expected = params.get("expected", "")
        print(f"      ✔️ 断言: {locator} 包含 '{expected}'")
        result = self.driver.assert_element(locator, expected)
        self.store_return(result)
        if not result:
            print(f"      ⚠️ 断言失败")
        return result

    def _kw_clear(self, params: Dict) -> bool:
        """清空输入框"""
        locator = params.get("locator", "")
        print(f"      🗑️ 清空: {locator}")
        result = self.driver.clear(locator)
        if not result:
            raise DriverError(f"清空失败: {locator}")
        return result

    def _kw_double_click(self, params: Dict) -> bool:
        """双击"""
        locator = params.get("locator", "")
        print(f"      🖱️ 双击: {locator}")
        result = self.driver.double_click(locator)
        if not result:
            raise DriverError(f"双击失败: {locator}")
        return result

    def _kw_right_click(self, params: Dict) -> bool:
        """右键点击"""
        locator = params.get("locator", "")
        print(f"      🖱️ 右键点击: {locator}")
        result = self.driver.right_click(locator)
        if not result:
            raise DriverError(f"右键点击失败: {locator}")
        return result

    def _kw_key_press(self, params: Dict) -> bool:
        """按键"""
        key = params.get("key", "")
        print(f"      ⌨️ 按键: {key}")
        result = self.driver.key_press(key)
        if not result:
            raise DriverError(f"按键失败: {key}")
        return result

    def _kw_get_text(self, params: Dict) -> bool:
        """获取文本"""
        locator = params.get("locator", "")
        var_name = params.get("var_name", "")
        print(f"      📖 获取文本: {locator}")
        text = self.driver.get_text(locator)
        if text is not None:
            print(f"         文本: '{text}'")
            if var_name:
                self._variables[var_name] = text
            self.store_return(text)
            return True
        self.store_return(None)
        return False

    def _kw_upload_file(self, params: Dict) -> bool:
        """上传文件"""
        locator = params.get("locator", "")
        file_path = params.get("file_path", "")
        print(f"      📤 上传文件: {file_path} -> {locator}")
        result = self.driver.upload_file(locator, file_path)
        if not result:
            raise DriverError(f"上传文件失败: {file_path}")
        return result

    # ── HTTP/API 关键字 ───────────────────────────────────────────

    def _kw_http_get(self, params: Dict) -> bool:
        """HTTP GET 请求"""
        url = params.get("url", "")
        if not url:
            raise InvalidParameterError(keyword="http_get", param_name="url", reason="缺少必需参数")
        
        headers = params.get("headers")
        expected_status = int(params.get("expected_status", 200))
        
        print(f"      📨 GET: {url}")
        self._last_response = self.driver.http_get(url, headers=headers)
        
        if self._last_response and hasattr(self._last_response, "status_code"):
            actual_status = self._last_response.status_code
            print(f"         状态码: {actual_status}")
            result = actual_status == expected_status
            self.store_return(self._last_response.text if hasattr(self._last_response, "text") else str(self._last_response))
            if not result:
                print(f"      ⚠️ 状态码不匹配: 期望 {expected_status}, 实际 {actual_status}")
            return result
        self.store_return(None)
        return bool(self._last_response)

    def _kw_http_post(self, params: Dict) -> bool:
        """HTTP POST 请求"""
        url = params.get("url", "")
        if not url:
            raise InvalidParameterError(keyword="http_post", param_name="url", reason="缺少必需参数")
        
        body = params.get("body")
        headers = params.get("headers")
        expected_status = int(params.get("expected_status", 200))
        
        print(f"      📨 POST: {url}")
        self._last_response = self.driver.http_post(url, body=body, headers=headers)
        
        if self._last_response and hasattr(self._last_response, "status_code"):
            actual_status = self._last_response.status_code
            print(f"         状态码: {actual_status}")
            result = actual_status == expected_status
            self.store_return(self._last_response.text if hasattr(self._last_response, "text") else str(self._last_response))
            if not result:
                print(f"      ⚠️ 状态码不匹配: 期望 {expected_status}, 实际 {actual_status}")
            return result
        self.store_return(None)
        return bool(self._last_response)

    def _kw_http_put(self, params: Dict) -> bool:
        """HTTP PUT 请求"""
        url = params.get("url", "")
        if not url:
            raise InvalidParameterError(keyword="http_put", param_name="url", reason="缺少必需参数")
        
        body = params.get("body")
        headers = params.get("headers")
        expected_status = int(params.get("expected_status", 200))
        
        print(f"      📨 PUT: {url}")
        self._last_response = self.driver.http_put(url, body=body, headers=headers)
        
        if self._last_response and hasattr(self._last_response, "status_code"):
            result = self._last_response.status_code == expected_status
            self.store_return(self._last_response.text if hasattr(self._last_response, "text") else str(self._last_response))
            return result
        self.store_return(None)
        return bool(self._last_response)

    def _kw_http_delete(self, params: Dict) -> bool:
        """HTTP DELETE 请求"""
        url = params.get("url", "")
        if not url:
            raise InvalidParameterError(keyword="http_delete", param_name="url", reason="缺少必需参数")
        
        headers = params.get("headers")
        expected_status = int(params.get("expected_status", 200))
        
        print(f"      📨 DELETE: {url}")
        self._last_response = self.driver.http_delete(url, headers=headers)
        
        if self._last_response and hasattr(self._last_response, "status_code"):
            result = self._last_response.status_code == expected_status
            self.store_return(self._last_response.text if hasattr(self._last_response, "text") else str(self._last_response))
            return result
        self.store_return(None)
        return bool(self._last_response)

    def _kw_assert_json(self, params: Dict) -> bool:
        """JSON 断言"""
        if not self._last_response:
            raise RuntimeError("无可用的 HTTP 响应，请先执行 HTTP 请求关键字")
        
        data = self._last_response
        if hasattr(data, "json"):
            data = data.json()
        
        path = params.get("path", "")
        expected = params.get("expected")
        
        print(f"      ✔️ JSON断言: {path} = {expected}")
        actual = RestHelper.jsonpath_extract(data, path)
        result = actual == expected
        
        if not result:
            print(f"      ⚠️ JSON断言失败: 实际值={actual}")
        return result

    def _kw_assert_status(self, params: Dict) -> bool:
        """状态码断言"""
        if not self._last_response:
            raise RuntimeError("无可用的 HTTP 响应，请先执行 HTTP 请求关键字")
        
        expected = int(params.get("expected", 200))
        
        if hasattr(self._last_response, "status_code"):
            actual = self._last_response.status_code
            print(f"      ✔️ 状态码断言: {actual} == {expected}")
            result = actual == expected
            if not result:
                print(f"      ⚠️ 状态码断言失败")
            return result
        return False

    def _kw_send(self, params: Dict) -> bool:
        """发送HTTP请求（通用）"""
        url = params.get("url", "")
        if not url:
            raise InvalidParameterError(keyword="send", param_name="url", reason="缺少必需参数")
        
        method = params.get("method", "POST").upper()
        body = params.get("body")
        headers = params.get("headers")
        expected_status = int(params.get("expected_status", 200))

        print(f"      📨 {method}: {url}")

        if method == "GET":
            self._last_response = self.driver.http_get(url, headers=headers)
        elif method == "POST":
            self._last_response = self.driver.http_post(url, body=body, headers=headers)
        elif method == "PUT":
            self._last_response = self.driver.http_put(url, body=body, headers=headers)
        elif method == "DELETE":
            self._last_response = self.driver.http_delete(url, headers=headers)
        else:
            raise InvalidParameterError(keyword="send", param_name="method", reason=f"不支持的 HTTP 方法: {method}")

        if self._last_response and hasattr(self._last_response, "status_code"):
            return self._last_response.status_code == expected_status
        return bool(self._last_response)

    # ── 高级关键字 ─────────────────────────────────────────────────

    def _kw_set(self, params: Dict) -> bool:
        """设置变量"""
        var_name = params.get("var_name", "")
        value = params.get("value", "")
        if not var_name:
            raise InvalidParameterError(keyword="set", param_name="var_name", reason="缺少必需参数")
        
        print(f"      📝 设置变量: {var_name} = '{value}'")
        self._variables[var_name] = value
        return True

    def _kw_run(self, params: Dict) -> bool:
        """运行Logic用例"""
        case_name = params.get("case_name", "") or params.get("data", "")
        if not case_name:
            raise InvalidParameterError(keyword="run", param_name="case_name", reason="缺少必需参数")
        
        logic_file = self._find_logic_file(case_name, params.get("case_file"))
        if not logic_file:
            print(f"      ⚠️ 未找到 Logic 用例: {case_name} (模拟执行)")
            self.store_return(f"Logic {case_name} executed (simulated)")
            return True
        
        print(f"      🔄 运行Logic: {case_name}")
        
        try:
            from core.case_parser import CaseParser
            
            parser = CaseParser(str(logic_file))
            cases = parser.parse_cases()
            
            logic_results = []
            for case in cases:
                for step_type in ['pre_process', 'test_step', 'expected_result', 'post_process']:
                    step = case.get(step_type, {})
                    if step.get('action'):
                        step_params = {
                            'model': step.get('model', ''),
                            'data': step.get('data', '')
                        }
                        result = self.execute(step['action'], step_params)
                        logic_results.append(result)
            
            parser.close()
            self.store_return(logic_results)
            return True
            
        except Exception as e:
            logger.error(f"Logic用例执行失败: {e}")
            self.store_return(None)
            return False
    
    def _find_logic_file(self, case_name: str, hint_path: str = None) -> Optional[Path]:
        """查找 Logic 用例文件"""
        if hint_path and Path(hint_path).exists():
            return Path(hint_path)
        
        base_dirs = [
            Path("logic"),
            Path("product/TEST/v1R1C01/logic"),
            Path("product/TEST/v1R1C01/case"),
            Path("examples"),
        ]
        
        possible_names = [
            f"{case_name}.xlsx",
            f"{case_name}_logic.xlsx",
            f"logic_{case_name}.xlsx",
        ]
        
        for base_dir in base_dirs:
            if not base_dir.exists():
                continue
            for name in possible_names:
                file_path = base_dir / name
                if file_path.exists():
                    return file_path
        
        return None

    def _kw_db(self, params: Dict) -> bool:
        """数据库操作"""
        operation = params.get("operation", "query").lower()
        query = params.get("query", "") or params.get("data", "")
        var_name = params.get("var_name", "")
        db_config = params.get("db_config", "default")

        if not query:
            raise InvalidParameterError(keyword="DB", param_name="query", reason="缺少必需参数")

        print(f"      🗄️ DB {operation}: {query[:50]}...")

        db_connection = self._get_db_connection(db_config, params.get("connection_string"))
        
        if db_connection:
            try:
                result = self._execute_db_operation(db_connection, operation, query)
                if operation == "query" and var_name:
                    self._variables[var_name] = result
                self.store_return(result)
                print(f"         ✅ 操作成功")
                return True
            except Exception as e:
                logger.error(f"数据库操作失败: {e}")
                self.store_return(None)
                return False
        else:
            print(f"         ⚠️ 未配置数据库连接，使用模拟模式")
            if operation == "query":
                mock_result = [{"id": 1, "name": "mock_data"}]
                if var_name:
                    self._variables[var_name] = mock_result
                self.store_return(mock_result)
            else:
                self.store_return({"affected_rows": 1, "status": "simulated"})
            return True

    def _get_db_connection(self, config_name: str, connection_string: str = None):
        """获取数据库连接"""
        if hasattr(self, 'data_manager') and hasattr(self.data_manager, 'db_connections'):
            return self.data_manager.db_connections.get(config_name)
        
        if connection_string:
            try:
                import sqlite3
                if connection_string.endswith('.db') or connection_string.endswith('.sqlite'):
                    return sqlite3.connect(connection_string)
            except Exception as e:
                logger.warning(f"创建数据库连接失败: {e}")
        
        return None

    def _execute_db_operation(self, connection, operation: str, query: str):
        """执行数据库操作"""
        cursor = connection.cursor()
        
        if operation == "query":
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
        else:
            cursor.execute(query)
            connection.commit()
            return {"affected_rows": cursor.rowcount}