"""关键字引擎 - 支持14个操作关键字（UI / API / DB / Code）"""
import json
import logging
import subprocess
import sys
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from drivers.base_driver import BaseDriver
from core.performance import monitor_performance
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
from core.model_parser import ModelParser

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
        "close", "type", "verify", "wait", "navigate", "launch",
        "assert", "upload_file", "clear", "get_text", "get",
        "send", "set", "DB", "run", "click", "screenshot",
    ]

    # 默认重试配置
    DEFAULT_RETRY_CONFIG = {
        "max_retries": 0,
        "retry_delay": 1.0,
        "retry_on_errors": ["ElementNotFound", "Timeout", "StaleElement"],
    }

    def __init__(self, driver: BaseDriver, data_dir: Optional[Path] = None, 
                 retry_config: Optional[Dict[str, Any]] = None,
                 model_parser=None, data_manager=None,
                 global_vars: Optional[Dict] = None,
                 case_file: Optional[str] = None,
                 data_resolver=None,
                 driver_factory: Optional[Any] = None,
                 module_dir: Optional[str] = None):
        self.driver = driver
        self._driver_factory = driver_factory
        self._variables: Dict[str, Any] = {}
        self._return_values: list = []
        self.model_parser = model_parser
        self.data_manager = data_manager
        self.data_resolver = data_resolver
        self._global_vars = global_vars or {}
        self._db_connections: Dict[str, Any] = {}
        self._case_file = Path(case_file) if case_file else None
        self._module_dir = Path(module_dir) if module_dir else None
        
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

        # 参数解析由 data_resolver 在更早阶段完成
        resolved_params = params or {}

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
        param_str = ", ".join(f"{k}={v}" for k, v in params.items() if v)
        logger.info(f"执行关键字: {keyword}({param_str})" if param_str else f"执行关键字: {keyword}()")
    
    def _log_keyword_success(self, keyword: str, attempts: int, result: bool) -> None:
        if attempts > 1:
            logger.info(f"{keyword} 成功 (第{attempts}次尝试)")
        else:
            logger.debug(f"{keyword} 成功")
    
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

    # ── 多定位器支持 ─────────────────────────────────────────────

    def _try_locators(
        self,
        element_info: Dict[str, Any]
    ) -> Optional[Tuple[int, int, int, int]]:
        """尝试多个定位器，按 priority 依次尝试

        Args:
            element_info: 元素信息，包含 locations 列表
                {
                    'type': 主定位器类型,
                    'value': 主定位器值,
                    'locations': [
                        {'type': 'id', 'value': 'username', 'priority': 1},
                        {'type': 'ocr', 'value': '用户名', 'priority': 2}
                    ]
                }

        Returns:
            边界框坐标 (x1, y1, x2, y2)，所有定位器都失败返回 None
        """
        locations = element_info.get("locations", [])

        if not locations:
            # 兼容旧格式：使用主定位器
            loc_type = element_info.get("type")
            loc_value = element_info.get("value")
            if loc_type and loc_value:
                locations = [{"type": loc_type, "value": loc_value, "priority": 1}]

        # 按 priority 排序
        sorted_locations = sorted(locations, key=lambda x: x.get("priority", 1))

        for loc in sorted_locations:
            locator_type = loc["type"]
            locator_value = loc["value"]

            try:
                bbox = self.driver.locate_element(locator_type, locator_value)
                if bbox:
                    logger.info(f"定位成功: {locator_type}={locator_value}")
                    return bbox
            except NotImplementedError:
                # 驱动不支持该定位器类型，跳过
                logger.debug(f"驱动不支持定位器类型: {locator_type}")
                continue
            except Exception as e:
                logger.warning(f"定位器 {locator_type}={locator_value} 失败: {e}")
                continue

        return None

    def _is_vision_locator(self, locator_type: str) -> bool:
        """判断是否是视觉定位器类型"""
        return ModelParser.is_vision_locator(locator_type)

    # ── UI 操作关键字 ─────────────────────────────────────────────

    def _ensure_driver(self) -> None:
        """确保驱动可用，如果已关闭则通过工厂重新创建"""
        is_closed = getattr(self.driver, '_is_closed', False)
        if is_closed is True:
            if self._driver_factory:
                logger.info("浏览器已关闭，自动创建新浏览器实例...")
                self.driver = self._driver_factory()
            else:
                raise DriverStoppedError(
                    "浏览器未启动且未提供 driver_factory，无法自动创建"
                )

    def _kw_close(self, params: Dict) -> bool:
        """关闭浏览器"""
        logger.info("关闭浏览器")
        self.driver.close()
        return True

    def _kw_type(self, params: Dict) -> bool:
        """输入文本"""
        locator = params.get("locator", "")
        text = params.get("text", "")
        model_name = params.get("model", "")
        data_ref = params.get("data", "")

        # 批量输入模式：type 模型名 数据引用
        if model_name and data_ref and self.model_parser and self.data_manager:
            return self._batch_type(model_name, data_ref)

        # 单字段输入模式
        if not locator:
            raise InvalidParameterError(
                keyword="type",
                param_name="locator",
                reason="缺少必需参数 'locator'"
            )
        
        logger.info(f"输入: {locator} <- '{text}'")
        result = self.driver.type(locator, text)
        if not result:
            raise DriverError(f"输入失败: {locator}")
        return result

    # ── 数据表动作值支持 ─────────────────────────────────────────
    # 数据表单元格中可写入 UI 动作关键字，type 批量模式会自动识别并执行。
    # 支持: click / double_click / right_click / hover / select【值】
    #       key_press【按键】 / drag【目标】 / scroll / scroll【x,y】

    ELEMENT_ACTIONS = {
        'click', 'double_click', 'right_click', 'hover', 'scroll',
    }

    @staticmethod
    def _extract_bracket_value(value: str) -> str:
        """提取中文方括号【】中的参数值"""
        start = value.find('【')
        end = value.find('】')
        if start != -1 and end != -1 and end > start:
            return value[start + 1:end]
        return ''

    def _execute_element_action(self, value: str, locator: str, element_name: str):
        """检查数据表值是否为 UI 动作关键字，是则执行对应操作。

        Returns:
            (action_name, element_name, result) 或 None（表示不是动作，应当作文本输入）
        """
        value_lower = value.strip().lower()

        # 简单动作：值恰好等于关键字名
        if value_lower in self.ELEMENT_ACTIONS:
            action_map = {
                'click': self.driver.click,
                'double_click': self.driver.double_click,
                'right_click': self.driver.right_click,
                'hover': self.driver.hover,
                'scroll': lambda loc: self.driver.scroll(0, 300),
            }
            fn = action_map[value_lower]
            logger.debug(f"{element_name}: {value_lower} {locator}")
            return (value_lower, element_name, fn(locator))

        # 带参数的动作：key_press【按键】
        if value_lower.startswith('key_press'):
            key = self._extract_bracket_value(value)
            if not key:
                logger.warning(f"{element_name}: key_press 缺少按键参数，格式应为 key_press【按键】")
                return None
            logger.debug(f"{element_name}: 按键 '{key}'")
            return ('key_press', element_name, self.driver.key_press(key))

        # 带参数的动作：select【选项值】
        if value_lower.startswith('select'):
            select_value = self._extract_bracket_value(value)
            if not select_value:
                return None
            logger.debug(f"{element_name}: 选择 {locator} = '{select_value}'")
            return ('select', element_name, self.driver.select(locator, select_value))

        # 带参数的动作：drag【目标定位器】
        if value_lower.startswith('drag'):
            target = self._extract_bracket_value(value)
            if not target:
                return None
            logger.debug(f"{element_name}: 拖拽 {locator} -> {target}")
            return ('drag', element_name, self.driver.drag(locator, target))

        # 带参数的动作：scroll【x,y】
        if value_lower.startswith('scroll'):
            params_str = self._extract_bracket_value(value)
            parts = params_str.split(',')
            x = int(parts[0].strip()) if len(parts) > 0 and parts[0].strip() else 0
            y = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else 300
            logger.debug(f"{element_name}: 滚动 ({x}, {y})")
            return ('scroll', element_name, self.driver.scroll(x, y))

        return None

    def _batch_type(self, model_name: str, data_ref: str) -> bool:
        """批量输入：遍历模型元素，匹配数据表字段

        数据引用格式: type ModelName DataID
        - 数据表名 = 模型名（强制一致）
        - data_ref 直接就是 DataID

        数据表单元格的值决定对该元素执行什么操作：
        - 普通文本 → 输入到元素
        - click / double_click / right_click / hover → 执行对应 UI 动作
        - select【值】 → 下拉选择
        - key_press【按键】 → 按键（支持组合键如 Control+C）
        - drag【目标】 → 拖拽到目标元素
        - scroll / scroll【x,y】 → 页面滚动
        """
        table_name = model_name
        data_id = data_ref

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
                reason=f"数据不存在: 表 '{table_name}' 中找不到 DataID='{data_id}'"
            )

        logger.info(f"批量输入: 模型={model_name}, DataID={data_id}")
        
        operations = []
        resolved_values = {}
        for element_name, element_info in model.items():
            if element_name not in data_row:
                continue
            value = str(data_row[element_name])
            if self.data_resolver:
                value = self.data_resolver.resolve_with_return(value)

            driver_type = element_info.get('driver_type', 'web')
            value_upper = value.strip().upper()

            # BLANK: UI 跳过, 接口传空字符串
            if value_upper == 'BLANK':
                if driver_type == 'web':
                    logger.debug(f"{element_name}: BLANK → 跳过")
                    resolved_values[element_name] = ''
                    continue
                else:
                    value = ''

            # NULL → 接口传 "null"; NONE → 接口传 "none"; UI 均跳过
            if value_upper in ('NULL', 'NONE'):
                if driver_type == 'web':
                    logger.debug(f"{element_name}: {value_upper} → 跳过")
                    resolved_values[element_name] = None
                    continue
                else:
                    mapped = value.lower()
                    resolved_values[element_name] = mapped
                    continue

            resolved_values[element_name] = value
            locator_type = element_info['type']
            locator_value = element_info['value']
            locator = f"{locator_type}={locator_value}"

            # 尝试作为 UI 动作执行
            action_result = self._execute_element_action(value, locator, element_name)
            if action_result is not None:
                operations.append(action_result)
            else:
                # 普通文本输入
                display_value = value
                if value.endswith('.Password'):
                    value = value[:-9]
                    display_value = '***'
                logger.debug(f"{element_name}: {locator} <- '{display_value}'")
                result = self.driver.type(locator, value)
                operations.append(('type', element_name, result))
        
        failed_ops = [op for op in operations if not op[2]]
        if failed_ops:
            failed_names = [op[1] for op in failed_ops]
            raise DriverError(f"批量输入失败: {', '.join(failed_names)}")
        
        # 存储解析后的实际使用值（Return[-1] 等已替换为真实值）
        self.store_return(resolved_values)
        return True

    # ── 接口测试关键字 ─────────────────────────────────────────────

    def _kw_send(self, params: Dict) -> bool:
        """发送接口请求 — 与 type 对称的接口测试关键字

        公式: send ApiModel DataID
        从模型获取接口定义（请求方式/URL），从数据表取值发送 HTTP 请求，
        响应自动保存为步骤返回值（含 status 和响应体字段）。
        """
        model_name = params.get("model", "")
        data_ref = params.get("data", "")

        if not model_name or not data_ref:
            raise InvalidParameterError(
                keyword="send",
                param_name="model/data",
                reason="send 必须指定模型和 DataID (send ApiModel DataID)"
            )
        if not self.model_parser or not self.data_manager:
            raise InvalidParameterError(
                keyword="send",
                param_name="context",
                reason="send 需要 model_parser 和 data_manager（请通过 SKIExecutor 执行）"
            )
        return self._batch_send(model_name, data_ref)

    def _batch_send(self, model_name: str, data_ref: str) -> bool:
        """批量发送接口请求：从模型和数据表组装 HTTP 请求

        数据引用格式: send ModelName DataID
        - 数据表名 = 模型名（强制一致）
        - data_ref 直接就是 DataID

        接口模型元素命名约定：
        - _method: HTTP 请求方式（GET/POST/PUT/DELETE），模型中定义默认值
        - _url: 请求 URL（绝对路径或相对路径）
        - _header_*: 请求头（如 _header_Authorization）
        - 其他元素: 请求体字段（POST/PUT → JSON body；GET/DELETE → 查询参数）
        """
        table_name = model_name
        data_id = data_ref

        model = self.model_parser.get_model(model_name)
        data_row = self.data_manager.get_data(table_name, data_id)

        if not model:
            raise InvalidParameterError(
                keyword="send", param_name="model",
                reason=f"模型不存在: '{model_name}'"
            )
        if not data_row:
            raise InvalidParameterError(
                keyword="send", param_name="data",
                reason=f"数据不存在: 表 '{table_name}' 中找不到 DataID='{data_id}'"
            )

        logger.info(f"接口请求: 模型={model_name}, DataID={data_id}")

        method = "GET"
        url = ""
        headers = {}
        body = {}

        for element_name, element_info in model.items():
            if element_name in data_row:
                value = str(data_row[element_name])
                if self.data_resolver:
                    value = self.data_resolver.resolve_with_return(value)
            else:
                value = element_info.get('value', '')

            if not value or not value.strip():
                continue
            value = value.strip()

            if element_name == '_method':
                method = value.upper()
            elif element_name == '_url':
                url = value
            elif element_name.startswith('_header_'):
                header_name = element_name[8:]
                headers[header_name] = value
            else:
                value_upper = value.upper()
                if value_upper == 'BLANK':
                    body[element_name] = ''
                elif value_upper == 'NULL':
                    body[element_name] = None
                elif value_upper == 'NONE':
                    continue
                else:
                    body[element_name] = value

        if not url:
            raise InvalidParameterError(
                keyword="send", param_name="_url",
                reason="接口模型或数据中缺少 _url（请求地址）"
            )

        from api.rest_helper import RestHelper
        try:
            if method in ('POST', 'PUT', 'PATCH'):
                response = RestHelper.send_request(
                    method=method, url=url,
                    headers=headers or None,
                    body=body if body else None,
                )
            else:
                if body:
                    from urllib.parse import urlencode
                    sep = '&' if '?' in url else '?'
                    url = f"{url}{sep}{urlencode(body)}"
                response = RestHelper.send_request(
                    method=method, url=url,
                    headers=headers or None,
                )
        except Exception as e:
            raise DriverError(f"HTTP {method} 请求失败: {url} - {e}")

        result_data = {"status": response.status_code}
        try:
            json_body = response.json()
            if isinstance(json_body, dict):
                result_data.update(json_body)
            else:
                result_data["body"] = json_body
        except (ValueError, TypeError):
            result_data["body"] = response.text

        self.store_return(result_data)
        logger.info(f"HTTP {method} {url} → {response.status_code}")
        return True

    def _kw_check(self, params: Dict) -> bool:
        """check → verify 的内部别名，保留向后兼容"""
        return self._kw_verify(params)

    def _kw_wait(self, params: Dict) -> bool:
        """等待"""
        seconds = params.get("seconds") or params.get("data", "1.0")
        logger.info(f"等待: {seconds}秒")
        self.driver.wait(float(seconds))
        return True

    def _kw_navigate(self, params: Dict) -> bool:
        """导航到URL，如果当前没有浏览器则自动创建新实例"""
        url = params.get("url", "") or params.get("data", "")
        if not url:
            raise InvalidParameterError(
                keyword="navigate",
                param_name="url",
                reason="缺少必需参数 'url'"
            )
        self._ensure_driver()
        logger.info(f"导航: {url}")
        result = self.driver.navigate(url)
        if not result:
            raise DriverError(f"导航失败: {url}")
        return result

    def _kw_launch(self, params: Dict) -> bool:
        """启动应用或打开页面

        Web 模型: 等同于 navigate，打开 URL
        Desktop 模型: 启动桌面应用
        """
        model_name = params.get("model", "")
        data_ref = params.get("data", "")

        # 批量模式: launch ModelName DataID
        if model_name and data_ref and self.model_parser:
            driver_type = self.model_parser.get_model_driver_type(model_name)
            if driver_type == "web":
                return self._execute_navigate(model_name, data_ref)
            else:
                return self._execute_desktop_launch(model_name, data_ref)

        # 单参数模式: launch app_path 或 launch url
        target = params.get("app_path") or params.get("url") or data_ref
        if not target:
            raise InvalidParameterError(
                keyword="launch",
                param_name="app_path/url",
                reason="缺少必需参数"
            )

        # 判断是 URL 还是应用路径
        if target.startswith(("http://", "https://")):
            logger.info(f"打开页面: {target}")
            return self.driver.navigate(target)
        else:
            logger.info(f"启动应用: {target}")
            return self.driver.launch(app_path=target)

    def _execute_navigate(self, model_name: str, data_ref: str) -> bool:
        """执行 Web 导航"""
        if not self.data_manager:
            raise DriverError("data_manager 未初始化")
        data = self.data_manager.get_data(model_name, data_ref)
        url = data.get("url", "")
        if not url:
            raise InvalidParameterError("launch", "url", "数据中缺少 url 字段")
        logger.info(f"导航: {url}")
        return self.driver.navigate(url)

    def _execute_desktop_launch(self, model_name: str, data_ref: str) -> bool:
        """执行 Desktop 应用启动"""
        if not self.data_manager:
            raise DriverError("data_manager 未初始化")
        data = self.data_manager.get_data(model_name, data_ref)
        app_path = data.get("app_path", "")
        if not app_path:
            raise InvalidParameterError("launch", "app_path", "数据中缺少 app_path 字段")
        logger.info(f"启动应用: {app_path}")
        return self.driver.launch(app_path=app_path)

    def _kw_screenshot(self, params: Dict) -> bool:
        """截图"""
        path = params.get("path", "") or params.get("data", "") or "screenshot.png"
        logger.info(f"截图: {path}")
        return self.driver.screenshot(path)

    def _kw_assert(self, params: Dict) -> bool:
        """断言（保留兼容）"""
        locator = params.get("locator", "") or params.get("data", "")
        expected = params.get("expected", "")
        logger.info(f"断言: {locator} 包含 '{expected}'")
        result = self.driver.assert_element(locator, expected)
        self.store_return(result)
        if not result:
            logger.warning("断言失败")
        return result

    def _kw_verify(self, params: Dict) -> bool:
        """验证 - 与 type 对称的批量验证关键字
        
        公式: verify ModelName DataID
        自动在 ModelName_verify 数据表中查找 DataID 行，
        遍历模型元素，从界面/接口读取实际值并与期望值比较。
        """
        model_name = params.get("model", "")
        data_ref = params.get("data", "")

        if not model_name or not data_ref:
            raise InvalidParameterError(
                keyword="verify",
                param_name="model/data",
                reason="verify 必须指定模型和 DataID (verify ModelName DataID)"
            )
        if not self.model_parser or not self.data_manager:
            raise InvalidParameterError(
                keyword="verify",
                param_name="context",
                reason="verify 需要 model_parser 和 data_manager（请通过 SKIExecutor 执行）"
            )
        return self._batch_verify(model_name, data_ref)

    def _batch_verify(self, model_name: str, data_ref: str) -> bool:
        """批量验证：遍历模型元素，读取界面/接口实际值，与期望值比较

        数据引用格式: verify ModelName DataID
        - 数据表名 = ModelName_verify（自动拼接）
        - data_ref 直接就是 DataID
        """
        table_name = f"{model_name}_verify"
        data_id = data_ref

        model = self.model_parser.get_model(model_name)
        data_row = self.data_manager.get_data(table_name, data_id)

        if not model:
            raise InvalidParameterError(
                keyword="verify", param_name="model",
                reason=f"模型不存在: '{model_name}'"
            )
        if not data_row:
            raise InvalidParameterError(
                keyword="verify", param_name="data",
                reason=f"数据不存在: 表 '{table_name}' 中找不到 DataID='{data_id}'"
            )

        logger.info(f"批量验证: 模型={model_name}, 期望数据={data_ref}")

        results = {}
        mismatches = []

        for element_name, element_info in model.items():
            if element_name not in data_row:
                continue

            expected = str(data_row[element_name])
            if self.data_resolver:
                expected = self.data_resolver.resolve_with_return(expected)
            
            driver_type = element_info.get('driver_type', 'web')
            expected_upper = expected.strip().upper()

            # BLANK: UI 跳过该字段不验证, 接口期望空字符串
            if expected_upper == 'BLANK':
                if driver_type == 'web':
                    logger.debug(f"{element_name}: BLANK → 跳过验证")
                    continue
                else:
                    expected = ''

            # NULL → 接口期望 "null"; NONE → 接口期望 "none"; UI 均跳过
            if expected_upper in ('NULL', 'NONE'):
                if driver_type == 'web':
                    logger.debug(f"{element_name}: {expected_upper} → 跳过验证")
                    continue
                else:
                    expected_mapped = expected.lower()
                    last_return = self.get_return(-1)
                    actual_val = last_return.get(element_name) if isinstance(last_return, dict) else last_return
                    actual_str = str(actual_val) if actual_val is not None else "null"
                    results[element_name] = actual_val
                    matched = actual_str == expected_mapped or (expected_mapped == "null" and actual_val is None)
                    if not matched:
                        mismatches.append({'element': element_name, 'expected': expected_mapped, 'actual': actual_str})
                    logger.debug(f"{element_name}: 实际={actual_str}, 期望={expected_mapped} → {'OK' if matched else 'FAIL'}")
                    continue

            locator_type = element_info['type']
            locator_value = element_info['value']
            locator = f"{locator_type}={locator_value}"

            if driver_type == 'web':
                actual = self.driver.get_text(locator)
                actual_str = str(actual) if actual is not None else ""
            else:
                last_return = self.get_return(-1)
                if isinstance(last_return, dict):
                    actual_str = str(last_return.get(element_name, ""))
                else:
                    actual_str = str(last_return) if last_return is not None else ""

            results[element_name] = actual_str
            matched = expected in actual_str or actual_str == expected
            logger.debug(f"{element_name}: 实际='{actual_str}', 期望='{expected}' → {'OK' if matched else 'FAIL'}")

            if not matched:
                mismatches.append({
                    'element': element_name,
                    'expected': expected,
                    'actual': actual_str,
                })

        self.store_return(results)

        if mismatches:
            detail = "; ".join(
                f"{m['element']}(期望='{m['expected']}', 实际='{m['actual']}')"
                for m in mismatches
            )
            logger.warning(f"批量验证失败: {detail}")
            return False

        logger.info(f"批量验证通过: {len(results)} 个字段全部匹配")
        return True

    def _kw_get(self, params: Dict) -> bool:
        """获取元素文本（兼容老 SKI 的 get 关键字）"""
        return self._kw_get_text(params)

    def _kw_clear(self, params: Dict) -> bool:
        """清空输入框"""
        locator = params.get("locator", "") or params.get("data", "")
        logger.info(f"清空: {locator}")
        result = self.driver.clear(locator)
        if not result:
            raise DriverError(f"清空失败: {locator}")
        return result

    def _kw_get_text(self, params: Dict) -> bool:
        """获取文本"""
        locator = params.get("locator", "") or params.get("data", "")
        var_name = params.get("var_name", "")
        logger.info(f"获取文本: {locator}")
        text = self.driver.get_text(locator)
        if text is not None:
            logger.debug(f"获取到文本: '{text}'")
            if var_name:
                self._variables[var_name] = text
            self.store_return(text)
            return True
        self.store_return(None)
        return False

    def _kw_upload_file(self, params: Dict) -> bool:
        """上传文件"""
        locator = params.get("locator", "") or params.get("model", "")
        file_path = params.get("file_path", "") or params.get("data", "")
        logger.info(f"上传文件: {file_path} -> {locator}")
        result = self.driver.upload_file(locator, file_path)
        if not result:
            raise DriverError(f"上传文件失败: {file_path}")
        return result

    # ── 高级关键字 ─────────────────────────────────────────────────

    def _kw_set(self, params: Dict) -> bool:
        """设置变量"""
        var_name = params.get("var_name", "")
        value = params.get("value", "")
        if not var_name:
            raise InvalidParameterError(keyword="set", param_name="var_name", reason="缺少必需参数")
        
        logger.info(f"设置变量: {var_name} = '{value}'")
        self._variables[var_name] = value
        return True

    def _kw_run(self, params: Dict) -> bool:
        """在沙箱中执行 Python 代码

        用例格式: run | 工程名 | 代码文件路径
        目录结构:
            test_project/
            ├── case/          ← 用例文件
            └── fun/           ← 代码工程根目录
                └── <工程名>/  ← model 列指定
                    └── xxx.py ← data 列指定

        脚本的 stdout 输出自动保存为步骤返回值（尝试 JSON 解析）。
        """
        project_name = params.get("model", "")
        code_path = params.get("data", "")

        if not code_path:
            raise InvalidParameterError(
                keyword="run", param_name="data",
                reason="缺少代码文件路径"
            )

        if not self._module_dir and not self._case_file:
            raise InvalidParameterError(
                keyword="run", param_name="context",
                reason="run 需要知道测试模块目录以定位 fun/ 目录"
            )

        base_dir = self._module_dir or (self._case_file.parent.parent if self._case_file else None)
        if base_dir is None:
            raise InvalidParameterError(
                keyword="run", param_name="context",
                reason="run 需要知道测试模块目录以定位 fun/ 目录"
            )
        base_dir = Path(base_dir).resolve()
        fun_dir = base_dir / "fun"
        if project_name:
            project_dir = (fun_dir / project_name).resolve()
            script_path = (project_dir / code_path).resolve()
        else:
            project_dir = fun_dir.resolve()
            script_path = (fun_dir / code_path).resolve()

        if not script_path.exists():
            raise InvalidParameterError(
                keyword="run", param_name="data",
                reason=f"代码文件不存在: {script_path}"
            )

        logger.info(f"执行代码: {script_path}")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True,
                cwd=str(project_dir.resolve()),
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            raise DriverError(f"代码执行超时 (300s): {script_path}")

        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"退出码: {result.returncode}"
            logger.error(f"代码执行失败:\n{error_msg}")
            raise DriverError(f"代码执行失败: {error_msg}")

        output = result.stdout.strip()
        if output:
            try:
                parsed = json.loads(output)
                self.store_return(parsed)
            except (json.JSONDecodeError, ValueError):
                self.store_return(output)
        else:
            self.store_return(None)

        logger.info(f"代码执行成功: {script_path}")
        return True

    def _kw_db(self, params: Dict) -> bool:
        """数据库操作
        
        用例格式: DB | 连接变量名 | SQL数据引用或直接SQL
        
        执行流程:
        1. model 字段 = GlobalValue 中的数据库连接配置组名 (如 cassdb)
        2. data 字段 = 数据表引用 (如 QuerySQL.Q001) 或直接 SQL
        3. 从 GlobalValue 读取连接配置: cassdb.type, cassdb.host, cassdb.port 等
        4. 如果 data 是数据表引用，从数据表中读取 sql/operation/var_name
        5. 建立连接 → 执行 SQL → store_return 保存结果
        """
        conn_var = params.get("model", "")
        data_ref = params.get("data", "")

        if not data_ref:
            raise InvalidParameterError(keyword="DB", param_name="data", reason="缺少 SQL 或数据表引用")

        # 解析 SQL：从数据表读取 or 直接使用
        sql, operation, var_name = self._resolve_db_sql(data_ref)

        if not sql:
            raise InvalidParameterError(keyword="DB", param_name="data", reason=f"无法解析 SQL: '{data_ref}'")

        logger.info(f"DB {operation}: {sql[:80]}{'...' if len(sql) > 80 else ''}")

        # 获取数据库连接
        connection = self._get_db_connection(conn_var)

        if not connection:
            logger.error(f"无法建立数据库连接: {conn_var}")
            raise DriverError(f"数据库连接失败: 连接变量 '{conn_var}' 未配置或连接失败")

        try:
            result = self._execute_db_sql(connection, operation, sql)
            if var_name:
                self._variables[var_name] = result
            self.store_return(result)
            logger.info(f"DB 操作成功 ({operation})")
            return True
        except Exception as e:
            logger.error(f"SQL 执行失败: {e}")
            self.store_return(None)
            raise DriverError(f"SQL 执行失败: {e}")

    def _resolve_db_sql(self, data_ref: str):
        """解析 DB 的 data 字段，返回 (sql, operation, var_name)
        
        如果 data_ref 匹配 TableName.DataID 格式且数据表存在，从数据表读取:
            - sql 列: 实际 SQL
            - operation 列: query/execute (默认 query)
            - var_name 列: 可选，结果存入变量
        否则视为直接 SQL 语句。
        
        附带检查: 数据表对应的 .md 说明文件是否存在，不存在则自动创建空模板。
        """
        if self.data_manager and '.' in data_ref:
            parts = data_ref.split('.')
            if len(parts) >= 2:
                table_name, data_id = parts[0], parts[1]
                self._ensure_sql_doc(table_name)
                row = self.data_manager.get_data(table_name, data_id)
                if row:
                    sql = str(row.get('sql', '') or row.get('SQL', '')).strip()
                    operation = str(row.get('operation', '') or row.get('Operation', 'query')).strip().lower()
                    var_name = str(row.get('var_name', '') or row.get('VarName', '')).strip()
                    if sql:
                        return sql, operation or 'query', var_name

        # 直接 SQL
        data_ref = data_ref.strip()
        if data_ref.upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
            is_query = data_ref.upper().startswith('SELECT')
            return data_ref, 'query' if is_query else 'execute', ''

        return data_ref, 'query', ''

    def _ensure_sql_doc(self, table_name: str) -> None:
        """检查 SQL 数据表的 .md 说明文件是否存在，不存在则创建空模板"""
        if not self._module_dir and not self._case_file:
            return
        base_dir = self._module_dir or self._case_file.parent.parent
        model_dir = base_dir / "model"
        md_path = model_dir / f"{table_name}.md"
        if md_path.exists():
            return
        try:
            model_dir.mkdir(parents=True, exist_ok=True)
            md_path.write_text(
                f"# {table_name}\n\n"
                f"## 用途\n\n（请补充该 SQL 数据表的用途说明）\n\n"
                f"## 涉及表\n\n（请补充涉及的数据库表及关键字段）\n\n"
                f"## SQL 说明\n\n"
                f"| DataID | 用途 |\n"
                f"|--------|------|\n"
                f"| | |\n",
                encoding="utf-8"
            )
            logger.warning(f"SQL 数据表 '{table_name}' 缺少说明文件，已创建模板: {md_path}")
        except Exception as e:
            logger.warning(f"无法创建 SQL 说明文件 {md_path}: {e}")

    # ── 数据库连接管理 ──────────────────────────────────────────

    def _resolve_db_file_path(self, database: str) -> str:
        """将 SQLite 的 database 相对路径解析为绝对路径（相对测试模块目录）。"""
        if not database:
            return database
        p = Path(database)
        if p.is_absolute():
            return str(p)
        base = self._module_dir
        if base is None and self._case_file is not None:
            base = self._case_file.parent.parent
        if base is not None:
            return str((Path(base) / database).resolve())
        return str(p.resolve())

    def _get_db_connection(self, conn_var: str):
        """根据 GlobalValue 中的连接变量名获取/创建数据库连接
        
        从 global_vars（通过 SKIExecutor 传入的 keyword_engine 上下文）读取:
            conn_var.type     → mysql / postgresql / sqlite
            conn_var.host     → 主机
            conn_var.port     → 端口
            conn_var.database → 数据库名
            conn_var.username → 用户名
            conn_var.password → 密码
        """
        if not conn_var:
            return None

        # 连接池复用
        if conn_var in self._db_connections:
            conn = self._db_connections[conn_var]
            try:
                # 简单存活检测
                conn.cursor().execute("SELECT 1")
                return conn
            except Exception:
                self._db_connections.pop(conn_var, None)

        # 从 SKIExecutor 上下文获取 global_vars
        global_vars = {}
        if hasattr(self, '_global_vars'):
            global_vars = self._global_vars
        elif self.data_manager and hasattr(self.data_manager, '_global_vars'):
            global_vars = self.data_manager._global_vars

        config = global_vars.get(conn_var, {})
        if not config:
            logger.warning(f"GlobalValue 中未找到连接配置: {conn_var}")
            return None

        db_type = config.get('type', 'sqlite').lower()
        host = config.get('host', 'localhost')
        port = config.get('port', '')
        database = config.get('database', '')
        username = config.get('username', '')
        password = config.get('password', '')

        if db_type == 'sqlite' and database:
            database = self._resolve_db_file_path(database)

        logger.info(f"建立数据库连接: {conn_var} ({db_type}://{host}/{database})")

        try:
            conn = self._create_connection(db_type, host, port, database, username, password)
            if conn:
                self._db_connections[conn_var] = conn
            return conn
        except Exception as e:
            logger.error(f"创建数据库连接失败 [{conn_var}]: {e}")
            return None

    @staticmethod
    def _create_connection(db_type: str, host: str, port: str, database: str,
                           username: str, password: str):
        """根据数据库类型创建连接"""
        port_int = int(port) if port else None

        if db_type in ('mysql', 'mariadb'):
            import pymysql
            return pymysql.connect(
                host=host, port=port_int or 3306,
                user=username, password=password,
                database=database, charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        elif db_type in ('postgresql', 'postgres', 'pg'):
            import psycopg2
            import psycopg2.extras
            return psycopg2.connect(
                host=host, port=port_int or 5432,
                user=username, password=password,
                dbname=database
            )
        elif db_type == 'sqlite':
            import sqlite3
            sqlite3.Row
            conn = sqlite3.connect(database)
            conn.row_factory = sqlite3.Row
            return conn
        elif db_type in ('sqlserver', 'mssql'):
            import pymssql
            return pymssql.connect(
                server=host, port=str(port_int or 1433),
                user=username, password=password,
                database=database, charset='utf8'
            )
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

    @staticmethod
    def _execute_db_sql(connection, operation: str, sql: str):
        """执行 SQL 并返回结果"""
        cursor = connection.cursor()
        cursor.execute(sql)

        if operation == 'query':
            if hasattr(cursor, 'description') and cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                # 兼容 DictCursor (pymysql) 和普通 cursor
                if rows and isinstance(rows[0], dict):
                    return rows
                return [dict(zip(columns, row)) for row in rows]
            return []
        else:
            connection.commit()
            return {"affected_rows": cursor.rowcount}