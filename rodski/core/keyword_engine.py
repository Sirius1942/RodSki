"""关键字引擎 - 支持14个操作关键字（UI / API / DB / Code）"""
import json
import logging
import subprocess
import sys
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
try:
    from ..drivers.base_driver import BaseDriver
except ImportError:
    from drivers.base_driver import BaseDriver
from .performance import monitor_performance
from .exceptions import (
    UnknownKeywordError,
    InvalidParameterError,
    RetryExhaustedError,
    ElementNotFoundError,
    TimeoutError,
    StaleElementError,
    DriverStoppedError,
    DriverError,
    AssertionFailedError,
    AutoCaptureError,
    is_retryable_error,
    is_critical_error,
)
from .assertion.image_matcher import ImageMatcher
from .assertion.video_analyzer import VideoAnalyzer
from .model_parser import (
    ModelParser,
    MODEL_TYPE_UI,
    MODEL_TYPE_INTERFACE,
    LEGACY_DRIVER_TYPE_WEB,
    LEGACY_DRIVER_TYPE_INTERFACE,
)
from .runtime_context import RuntimeContext

logger = logging.getLogger("rodski")


def _add_parsed_arg(token: str, args: list, kwargs: dict) -> None:
    """将解析出的参数 token 添加到 args 或 kwargs

    Args:
        token: 参数 token 字符串
        args: 位置参数列表（原地修改）
        kwargs: 关键字参数字典（原地修改）
    """
    if not token:
        return
    if '=' in token:
        eq_pos = token.index('=')
        key = token[:eq_pos].strip()
        val = token[eq_pos + 1:].strip()
        if key.isidentifier():
            kwargs[key] = _coerce_value(val)
            return
    args.append(_coerce_value(token))


def _coerce_value(val: str):
    """将字符串值转为 Python 类型

    支持: 整数、浮点数、字符串（带引号或不带引号）

    Args:
        val: 原始字符串值

    Returns:
        转换后的 Python 值
    """
    if not val:
        return val
    # 去掉引号
    if (val.startswith("'") and val.endswith("'")) or \
       (val.startswith('"') and val.endswith('"')):
        return val[1:-1]
    # 整数
    try:
        return int(val)
    except ValueError:
        pass
    # 浮点数
    try:
        return float(val)
    except ValueError:
        pass
    # 布尔值
    if val.lower() == 'true':
        return True
    if val.lower() == 'false':
        return False
    return val


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
        "assert", "evaluate",
        "upload_file", "clear", "get_text", "get",
        "send", "set", "DB", "run",
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
        self._desktop_drivers: Dict[str, Any] = {}  # 按类型缓存的桌面驱动
        self._variables: Dict[str, Any] = {}
        self._context = RuntimeContext()
        self.model_parser = model_parser
        self.data_manager = data_manager
        self.data_resolver = data_resolver
        self._global_vars = global_vars or {}
        self._db_connections: Dict[str, Any] = {}
        self._case_file = Path(case_file) if case_file else None
        self._module_dir = Path(module_dir) if module_dir else None
        self._current_recording_path: Optional[str] = None

        # 初始化重试配置
        self._retry_config = {**self.DEFAULT_RETRY_CONFIG, **(retry_config or {})}
        self._retry_stats: Dict[str, List[int]] = {}

    def set_current_recording_path(self, path: Optional[str]) -> None:
        self._current_recording_path = path

    # ── 驱动自动路由 ──────────────────────────────────────────────

    DESKTOP_DRIVER_TYPES = {"macos", "windows", "other"}

    def _get_driver_for_type(self, driver_type: str) -> BaseDriver:
        """根据 driver_type 返回对应的驱动实例

        遵循设计约束：驱动类型由模型元素的 type 属性决定。
        - web/interface → 使用 self.driver（PlaywrightDriver/InterfaceDriver）
        - macos/windows/other → 懒加载创建 DesktopDriver 并缓存
        """
        if driver_type not in self.DESKTOP_DRIVER_TYPES:
            return self.driver

        # 已缓存则返回
        if driver_type in self._desktop_drivers:
            return self._desktop_drivers[driver_type]

        # 尝试通过 driver_factory 创建
        if self._driver_factory:
            try:
                desktop_driver = self._driver_factory(driver_type=driver_type)
                self._desktop_drivers[driver_type] = desktop_driver
                logger.info(f"自动创建桌面驱动: {driver_type}")
                return desktop_driver
            except Exception as e:
                logger.warning(f"通过 driver_factory 创建桌面驱动失败: {e}")

        # 回退：直接创建 DesktopDriver
        try:
            from ..drivers.desktop_driver import DesktopDriver
        except ImportError:
            from drivers.desktop_driver import DesktopDriver
        try:
            desktop_driver = DesktopDriver(target_platform=driver_type if driver_type != "other" else None)
            self._desktop_drivers[driver_type] = desktop_driver
            logger.info(f"直接创建桌面驱动: {driver_type}")
            return desktop_driver
        except ImportError:
            raise DriverError(
                "DesktopDriver 不可用，请确认 pyautogui 已安装: pip install pyautogui"
            )

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
                self._log_step_summary(keyword, resolved_params, result)

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

            except AssertionFailedError as e:
                # 断言失败不重试，直接向上抛出
                logger.error(f"❌ 断言失败: {e}")
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
    
    def _log_step_summary(self, keyword: str, params: Dict, result: Any) -> None:
        """Info 模式：每步执行后输出结构化摘要行"""
        model = params.get('model', '') or '-'
        history = self._context.history
        last = history[-1] if history else None

        if isinstance(last, dict) and '_capture' in last:
            return_source = 'auto_capture'
            cap = last.get('_capture', {})
            extra = f" capture={cap}"
        elif keyword == 'evaluate':
            return_source = 'evaluate'
            extra = ''
        elif keyword == 'get' and params.get('data', '') and not any(
            params.get('data', '').startswith(p) for p in self._SELECTOR_PREFIXES
        ):
            return_source = 'get_named'
            extra = ''
        else:
            return_source = 'keyword_result'
            extra = ''

        if keyword == 'set':
            data = params.get('data', '')
            if '=' in data:
                extra += f" named_write={data.split('=', 1)[0].strip()}"

        logger.info(f"[STEP] action={keyword} model={model} status=OK source={return_source}{extra}")

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"  history[{len(history)-1}]={repr(last)[:200]}")
            if self._context.named:
                logger.debug(f"  named={self._context.named}")

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
        self._context.append_history(value)

    def get_return(self, index: int) -> Any:
        """获取返回值，支持正负索引"""
        return self._context.get_history(index)

    def _get_nested_return(self, data: Any, path: str) -> Any:
        """从 Return 值中按点号路径获取嵌套字段

        Args:
            data: Return 值（通常为 dict）
            path: 字段路径，如 "data.inquiryId" 或 "code"
        """
        if not isinstance(data, dict):
            return data
        # 先尝试直接 key
        if path in data:
            return data[path]
        # 再按点号路径导航
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
            if current is None:
                return None
        return current

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

    def _execute_at_element(
        self,
        element_info: Dict[str, Any],
        action: str,
        value: str = None
    ) -> bool:
        """在元素位置执行操作（支持多定位器自动切换）

        Args:
            element_info: 元素信息，包含 locations 列表
            action: 操作类型 ('click', 'type', 'get_text', 'double_click', 'right_click', 'hover')
            value: 输入值（仅 action='type' 时使用）

        Returns:
            操作是否成功

        Raises:
            ElementNotFoundError: 所有定位器都失败时抛出
        """
        bbox = self._try_locators(element_info)

        if not bbox:
            raise ElementNotFoundError(
                f"无法定位元素，所有定位器均失败",
                locator=str(element_info.get("locations", []))
            )

        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if action == "click":
            self.driver.click(cx, cy)
            return True
        elif action == "double_click":
            self.driver.double_click(cx, cy)
            return True
        elif action == "right_click":
            self.driver.right_click(cx, cy)
            return True
        elif action == "hover":
            self.driver.hover(cx, cy)
            return True
        elif action == "type":
            if value is None:
                raise InvalidParameterError(
                    keyword="type",
                    param_name="value",
                    reason="type 操作需要提供 value 参数"
                )
            self.driver.type_text(cx, cy, value)
            return True
        elif action == "get_text":
            return self.driver.get_text(x1, y1, x2, y2)
        else:
            raise InvalidParameterError(
                keyword="action",
                param_name="action",
                reason=f"不支持的操作类型: {action}"
            )

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
        self.store_return(True)
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
        result = self.driver.type_locator(locator, text)
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

    @staticmethod
    def _parse_kv_args(kv_string: str) -> Dict[str, str]:
        """解析 key=value,key=value 格式的参数字符串

        Args:
            kv_string: 参数字符串，如 "type=image,reference=img/foo.png,threshold=0.85"

        Returns:
            {key: value, ...} 字典

        注意:
            value 中可以包含逗号（但不能包含等号），解析时以第一个 = 为界拆分 key 和 value。
            element_bbox 的值格式为 x,y,w,h（4个整数），需特殊处理以保留逗号。
        """
        result = {}
        if not kv_string.strip():
            return result

        # 用逗号分割，注意 value 中可能含有逗号
        parts = []
        current = ""
        in_bracket = False
        i = 0
        while i < len(kv_string):
            c = kv_string[i]
            if c == '[':
                in_bracket = True
                current += c
            elif c == ']':
                in_bracket = False
                current += c
            elif c == ',' and not in_bracket:
                parts.append(current.strip())
                current = ""
            else:
                current += c
            i += 1
        if current.strip():
            parts.append(current.strip())

        # 二次合并：element_bbox=x,y,w,h 格式，4个整数用逗号分隔
        # 合并策略：如果某个 part 只有数字（含负号），且前一个 part 是 element_bbox，
        # 则将其视为 bbox 的一部分合并回来
        merged_parts = []
        skip_count = 0
        for idx, part in enumerate(parts):
            if skip_count > 0:
                skip_count -= 1
                continue
            # 检查是否是 element_bbox 且后面跟数字（x,y,w,h 格式）
            if part.startswith("element_bbox=") and idx + 3 < len(parts):
                # 检查后续3个部分是否都是数字（bbox 的 y, w, h）
                following = parts[idx + 1:idx + 4]
                if all(p.strip().lstrip('-').isdigit() for p in following):
                    # 合并为 element_bbox=x,y,w,h
                    merged = ",".join([part] + following)
                    merged_parts.append(merged)
                    skip_count = 3
                    continue
            merged_parts.append(part)

        for part in merged_parts:
            if '=' not in part:
                continue
            # 找第一个 = 的位置（value 中不应有 =）
            eq_idx = part.index('=')
            key = part[:eq_idx].strip()
            value = part[eq_idx + 1:].strip()
            result[key] = value

        return result

    def _execute_element_action(self, value: str, locator: str, element_name: str, driver=None):
        """检查数据表值是否为 UI 动作关键字，是则执行对应操作。

        Args:
            driver: 指定驱动实例，默认使用 self.driver
        """
        target_driver = driver or self.driver
        value_lower = value.strip().lower()

        # 简单动作：值恰好等于关键字名
        if value_lower in self.ELEMENT_ACTIONS:
            action_map = {
                'click': target_driver.click_locator,
                'double_click': target_driver.double_click_locator if hasattr(target_driver, 'double_click_locator') else target_driver.click_locator,
                'right_click': target_driver.right_click_locator if hasattr(target_driver, 'right_click_locator') else target_driver.click_locator,
                'hover': target_driver.hover_locator if hasattr(target_driver, 'hover_locator') else target_driver.click_locator,
                'scroll': lambda loc: target_driver.scroll(0, 300),
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
            return ('key_press', element_name, target_driver.key_press(key))

        # 带参数的动作：select【选项值】
        if value_lower.startswith('select'):
            select_value = self._extract_bracket_value(value)
            if not select_value:
                return None
            logger.debug(f"{element_name}: 选择 {locator} = '{select_value}'")
            return ('select', element_name, target_driver.select(locator, select_value))

        # 带参数的动作：drag【目标定位器】
        if value_lower.startswith('drag'):
            target = self._extract_bracket_value(value)
            if not target:
                return None
            logger.debug(f"{element_name}: 拖拽 {locator} -> {target}")
            return ('drag', element_name, target_driver.drag(locator, target))

        # 带参数的动作：scroll【x,y】
        if value_lower.startswith('scroll'):
            params_str = self._extract_bracket_value(value)
            parts = params_str.split(',')
            x = int(parts[0].strip()) if len(parts) > 0 and parts[0].strip() else 0
            y = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else 300
            logger.debug(f"{element_name}: 滚动 ({x}, {y})")
            return ('scroll', element_name, target_driver.scroll(x, y))

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

        if '.' in data_id:
            raise InvalidParameterError(
                keyword="type", param_name="data",
                reason=f"data 只能是 DataID（如 'L001'），不能包含表名前缀，错误值: '{data_id}'"
            )

        model = self.model_parser.get_model(model_name)
        data_row = self.data_manager.get_data(table_name, data_id)

        if not model:
            raise InvalidParameterError(
                keyword="type",
                param_name="model",
                reason=f"模型不存在: '{model_name}'"
            )
        if self.model_parser.get_model_type(model_name) != MODEL_TYPE_UI:
            raise InvalidParameterError(
                keyword="type",
                param_name="model",
                reason=f"type 仅支持 UI 模型: '{model_name}'"
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
            if element_name.startswith('__'):
                continue
            if element_name not in data_row:
                continue
            value = str(data_row[element_name])
            if self.data_resolver:
                value = self.data_resolver.resolve_with_return(value)

            value_upper = value.strip().upper()

            if value_upper == 'BLANK':
                logger.debug(f"{element_name}: BLANK → 跳过")
                resolved_values[element_name] = ''
                continue

            if value_upper in ('NULL', 'NONE'):
                logger.debug(f"{element_name}: {value_upper} → 跳过")
                resolved_values[element_name] = None
                continue

            resolved_values[element_name] = value
            target_driver = self._get_driver_for_type(self.model_parser.get_model_driver_type(model_name))

            locations = element_info.get('locations', [])
            if not locations:
                locations = [{"type": element_info['locator_type'], "value": element_info['locator_value'], "priority": 1}]
            sorted_locations = sorted(locations, key=lambda x: x.get("priority", 1))

            op_done = False
            last_error = None

            for loc in sorted_locations:
                locator_type = loc["type"]
                locator_value = loc["value"]
                locator = f"{locator_type}={locator_value}"

                try:
                    action_result = self._execute_element_action(value, locator, element_name, driver=target_driver)
                    if action_result is not None:
                        operations.append(action_result)
                        op_done = True
                        logger.debug(f"  ↳ 定位器 {locator} 成功 (priority={loc.get('priority',1)})")
                        break

                    display_value = value
                    input_value = value
                    if input_value.endswith('.Password'):
                        input_value = input_value[:-9]
                        display_value = '***'
                    logger.debug(f"{element_name}: {locator} <- '{display_value}'")
                    result = target_driver.type_locator(locator, input_value)
                    if result:
                        operations.append(('type', element_name, True))
                        op_done = True
                        logger.debug(f"  ↳ 定位器 {locator} 成功 (priority={loc.get('priority',1)})")
                        break
                    else:
                        operations.append(('type', element_name, False))
                        logger.debug(f"  ↳ 定位器 {locator} 失败，尝试下一个...")
                except Exception as e:
                    last_error = e
                    logger.debug(f"  ↳ 定位器 {locator} 异常: {e}，尝试下一个...")
                    continue

            if not op_done:
                tried = ", ".join(f"{l['type']}={l['value']}" for l in sorted_locations)
                if last_error:
                    raise DriverError(f"元素 '{element_name}' 所有定位器均失败 [{tried}]: {last_error}")
                raise DriverError(f"元素 '{element_name}' 所有定位器均失败 [{tried}]")

        failed_ops = [op for op in operations if not op[2]]
        if failed_ops:
            failed_names = [op[1] for op in failed_ops]
            raise DriverError(f"批量输入失败: {', '.join(failed_names)}")

        self.store_return(resolved_values)

        if self.model_parser:
            ac_fields = self.model_parser.get_auto_capture(model_name, 'type')
            if ac_fields:
                capture = self._run_auto_capture_ui(model_name, ac_fields)
                self.store_return(capture)

        return True

    def _run_auto_capture_ui(self, model_name: str, fields: list) -> dict:
        result = {}
        for f in fields:
            loc_type = f.get('type', 'id')
            loc_value = f.get('value', '')
            name = f['name']
            try:
                if loc_type == 'id':
                    locator = f"#{loc_value}"
                elif loc_type == 'css':
                    locator = loc_value
                else:
                    locator = f"{loc_type}={loc_value}"
                text = self.driver.get_text_locator(locator) if hasattr(self.driver, 'get_text_locator') else self.driver.get_text(locator)
                result[name] = text
            except Exception as e:
                raise AutoCaptureError(field=name, source=f"{loc_type}={loc_value}", reason=str(e))
        return result

    def _run_auto_capture_send(self, response: dict, fields: list) -> dict:
        result = {}
        for f in fields:
            name = f['name']
            path = f.get('path', name)
            try:
                value = self._get_nested_return(response, path)
                if value is None:
                    raise KeyError(f"path '{path}' not found")
                result[name] = value
            except Exception as e:
                raise AutoCaptureError(field=name, source=path, reason=str(e))
        return result

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
        if self.model_parser.get_model_type(model_name) != MODEL_TYPE_INTERFACE:
            raise InvalidParameterError(
                keyword="send",
                param_name="model",
                reason=f"send 仅支持接口模型: '{model_name}'"
            )
        return self._batch_send(model_name, data_ref)

    @staticmethod
    def _try_parse_json_value(value: str):
        """尝试将字符串解析为 JSON 对象/数组，失败则返回原始字符串"""
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if stripped and stripped[0] in ('[', '{'):
            try:
                import json
                return json.loads(stripped)
            except (ValueError, TypeError):
                pass
        return value

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

        if '.' in data_id:
            raise InvalidParameterError(
                keyword="send", param_name="data",
                reason=f"data 只能是 DataID（如 'D001'），不能包含表名前缀，错误值: '{data_id}'"
            )

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
            if element_name.startswith('__'):
                continue
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
                    # 自动解析 JSON 格式的值（数组或对象）
                    body[element_name] = self._try_parse_json_value(value)

        if not url:
            raise InvalidParameterError(
                keyword="send", param_name="_url",
                reason="接口模型或数据中缺少 _url（请求地址）"
            )

        try:
            from ..api.rest_helper import RestHelper
        except ImportError:
            from api.rest_helper import RestHelper

        # 从浏览器获取 cookies 以共享登录态
        browser_cookies = None
        if hasattr(self.driver, 'get_cookies'):
            browser_cookies = self.driver.get_cookies()
            if browser_cookies:
                logger.debug(f"携带 {len(browser_cookies)} 个浏览器 cookies")

        try:
            if method in ('POST', 'PUT', 'PATCH'):
                response = RestHelper.send_request(
                    method=method, url=url,
                    headers=headers or None,
                    body=body if body else None,
                    cookies=browser_cookies,
                )
            else:
                if body:
                    from urllib.parse import urlencode
                    sep = '&' if '?' in url else '?'
                    url = f"{url}{sep}{urlencode(body)}"
                response = RestHelper.send_request(
                    method=method, url=url,
                    headers=headers or None,
                    cookies=browser_cookies,
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
            logger.debug(f"响应体: {json_body}")
        except (ValueError, TypeError):
            result_data["body"] = response.text
            logger.debug(f"响应文本(前500字): {response.text[:500]}")

        self.store_return(result_data)

        # Auto Capture
        if self.model_parser and model_name:
            ac_fields = self.model_parser.get_auto_capture(model_name, 'send')
            if ac_fields:
                capture = self._run_auto_capture_send(result_data, ac_fields)
                result_data['_capture'] = capture
                self._context.history[-1] = result_data

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
        self.store_return(True)
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
        self.store_return(True)
        return result

    def _kw_launch(self, params: Dict) -> bool:
        """启动应用或打开页面

        Web 模型: 等同于 navigate，打开 URL
        Desktop 模型: 启动桌面应用
        """
        model_name = params.get("model", "")
        data_ref = params.get("data", "")

        # 批量模式: launch ModelName DataID
        if model_type == MODEL_TYPE_INTERFACE:
            raise InvalidParameterError(
                keyword="launch",
                param_name="model",
                reason=f"launch 不支持接口模型: '{model_name}'"
            )
        driver_type = self.model_parser.get_model_driver_type(model_name) if self.model_parser else LEGACY_DRIVER_TYPE_WEB
        target_driver = self._get_driver_for_type(driver_type)
        if driver_type == LEGACY_DRIVER_TYPE_WEB:
            result = self._execute_navigate(model_name, data_ref)
        else:
            result = self._execute_desktop_launch(model_name, data_ref, target_driver)
        self.store_return(True)
        return result

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
            result = self.driver.navigate(target)
        else:
            logger.info(f"启动应用: {target}")
            result = self.driver.launch(app_path=target)
        self.store_return(True)
        return result

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

    def _execute_desktop_launch(self, model_name: str, data_ref: str, driver: Optional[BaseDriver] = None) -> bool:
        """执行 Desktop 应用启动"""
        if not self.data_manager:
            raise DriverError("data_manager 未初始化")
        data = self.data_manager.get_data(model_name, data_ref)
        app_path = data.get("app_path", "")
        app_name = data.get("app_name", "")
        if not app_path and not app_name:
            raise InvalidParameterError("launch", "app_path/app_name", "数据中缺少 app_path 或 app_name 字段")
        logger.info(f"启动应用: {app_path or app_name}")
        target_driver = driver or self.driver
        return target_driver.launch(app_path=app_path or None, app_name=app_name or None)

    def _kw_screenshot(self, params: Dict) -> bool:
        """截图"""
        path = params.get("path", "") or params.get("data", "") or "screenshot.png"
        # 解析相对路径：相对于 module_dir（与 assert 关键字一致）
        if self._module_dir:
            path_obj = Path(path)
            if not path_obj.is_absolute():
                path = str(self._module_dir / path)
        logger.info(f"截图: {path}")
        return self.driver.screenshot(path)

    def _kw_assert(self, params: Dict) -> bool:
        """图片/视频视觉断言

        支持两种数据格式：
        1. 直接格式（assert 关键字直接携带参数）:
           assert[type=image,reference=img/expected_modal.png,threshold=0.85]

        2. 数据引用格式（通过数据表间接引用）:
           assert[type=video,reference=img/expected_frame.png,threshold=0.85,video_source=recording,position=middle]

        参数说明（type=image）:
        - type: 断言类型，image 或 video
        - reference: 预期图片路径（相对于 images/assert/ 或绝对路径）
        - threshold: 匹配度阈值，默认 0.8
        - scope: 断言范围，full（全屏）或 element（元素区域），默认 full
        - wait: 等待秒数，0=立即断言，>0=轮询等待，默认 0
        - element_bbox: 元素区域，scope=element 时格式 x,y,w,h

        参数说明（type=video）:
        - type: 断言类型，固定为 video
        - reference: 预期图片路径
        - threshold: 匹配度阈值，默认 0.8
        - video_source: 视频源，recording（内置录屏）或文件路径，默认 recording
        - position: 关键帧位置，start/middle/end/any，默认 any
        - time_range: 时间范围，start,end 格式（秒）
        - wait: 等待秒数，0=立即断言，>0=轮询等待，默认 0
        """
        # 1. 获取断言参数字符串
        raw_data = params.get("data", "") or params.get("assert_params", "")
        if not raw_data:
            raise InvalidParameterError(
                keyword="assert",
                param_name="data",
                reason="assert 缺少参数，格式: assert[type=image,reference=...,threshold=...]"
            )

        # 2. 解析参数字符串
        inner = raw_data.strip()
        if inner.startswith("assert[") and inner.endswith("]"):
            inner = inner[7:-1]  # 去掉 assert[...] 包装

        parsed = self._parse_kv_args(inner)

        # 3. 提取参数
        assert_type = parsed.get("type", "image")

        # 获取公共参数
        reference = parsed.get("reference", "")
        threshold = float(parsed.get("threshold", "0.8"))
        scope = parsed.get("scope", "full")
        wait = int(parsed.get("wait", "0"))
        element_bbox_str = parsed.get("element_bbox", "")

        # 解析 element_bbox
        element_bbox = None
        if scope == "element" and element_bbox_str:
            parts = element_bbox_str.split(",")
            if len(parts) == 4:
                element_bbox = {
                    "x": int(parts[0].strip()),
                    "y": int(parts[1].strip()),
                    "w": int(parts[2].strip()),
                    "h": int(parts[3].strip()),
                }

        # 解析 reference 路径
        module_dir = self._module_dir or (
            self._case_file.parent.parent if self._case_file else None
        )
        if module_dir is None:
            raise DriverError(
                "assert 需要知道模块目录（module_dir）以定位 images/assert/ 目录"
            )
        module_dir = Path(module_dir)

        ref_path = ImageMatcher.resolve_reference_path(Path(reference), module_dir)
        if not ref_path.exists():
            raise FileNotFoundError(f"预期图片不存在: {ref_path}")

        # ── type=image ────────────────────────────────────────────
        if assert_type == "image":
            if not reference:
                raise InvalidParameterError(
                    keyword="assert",
                    param_name="reference",
                    reason="assert[type=image] 缺少必需参数: reference"
                )

            logger.info(
                f"视觉断言: type={assert_type}, reference={reference}, "
                f"threshold={threshold}, scope={scope}, wait={wait}"
            )
            screenshot_path = self.driver.take_screenshot()
            if screenshot_path is None:
                raise DriverError("截图失败，无法执行视觉断言")
            screenshot = cv2.imread(screenshot_path)
            if screenshot is None:
                raise DriverError(f"无法读取截图文件: {screenshot_path}")

            matcher = ImageMatcher()
            result = matcher.match(
                screenshot=screenshot,
                reference=ref_path,
                threshold=threshold,
                scope=scope,
                wait=wait,
                element_bbox=element_bbox,
            )

            result["screenshot"] = None

            if not result["matched"]:
                saved_path = ImageMatcher.save_failure_screenshot(
                    screenshot,
                    Path(reference).name,
                    failures_dir=module_dir / "images" / "assert" / "failures",
                )
                result["failure_screenshot"] = saved_path
                logger.warning(
                    f"图片断言失败: similarity={result['similarity']} < "
                    f"threshold={threshold}, reference={reference}"
                )
                if saved_path:
                    logger.info(f"失败截图已保存: {saved_path}")

            self.store_return(result)
            return result["matched"]

        # ── type=video ─────────────────────────────────────────────
        elif assert_type == "video":
            if not reference:
                raise InvalidParameterError(
                    keyword="assert",
                    param_name="reference",
                    reason="assert[type=video] 缺少必需参数: reference"
                )

            video_source = parsed.get("video_source", "recording")
            resolved_video_source = self._current_recording_path if video_source == "recording" and self._current_recording_path else video_source
            position = parsed.get("position", "any")
            time_range_str = parsed.get("time_range", "")

            # 解析 time_range: start,end 格式
            time_range = None
            if time_range_str:
                parts = time_range_str.split(",")
                if len(parts) == 2:
                    time_range = {
                        "start": float(parts[0].strip()),
                        "end": float(parts[1].strip()),
                    }

            logger.info(
                f"视频断言: type={assert_type}, reference={reference}, "
                f"threshold={threshold}, video_source={video_source}, "
                f"resolved_video_source={resolved_video_source}, "
                f"position={position}, wait={wait}"
            )

            analyzer = VideoAnalyzer()
            result = analyzer.match(
                video_source=resolved_video_source,
                reference=ref_path,
                threshold=threshold,
                position=position,
                time_range=time_range,
                scope=scope,
                element_bbox=element_bbox,
                wait=wait,
            )

            if not result["matched"]:
                recording_path = self._current_recording_path if video_source == "recording" else None

                logger.warning(
                    f"视频断言失败: similarity={result['similarity']} < "
                    f"threshold={threshold}, reference={reference}, "
                    f"frames_checked={result['total_frames_checked']}"
                )
                result["failure_recording"] = recording_path

            self.store_return(result)
            return result["matched"]

        else:
            raise InvalidParameterError(
                keyword="assert",
                param_name="type",
                reason=f"暂不支持的断言类型: {assert_type}，目前仅支持 type=image 和 type=video"
            )

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
        - 数据表名 = ModelName_verify（自动拼接，若已含 _verify 则不重复拼接）
        - data_ref 直接就是 DataID
        """
        table_name = f"{model_name}_verify" if not model_name.endswith("_verify") else model_name
        data_id = data_ref

        if '.' in data_id:
            raise InvalidParameterError(
                keyword="verify", param_name="data",
                reason=f"data 只能是 DataID（如 'V001'），不能包含表名前缀，错误值: '{data_id}'"
            )

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
        model_type = self.model_parser.get_model_type(model_name)
        target_driver = self._get_driver_for_type(self.model_parser.get_model_driver_type(model_name))

        for element_name, element_info in model.items():
            if element_name.startswith('__'):
                continue
            if element_name not in data_row:
                continue

            raw_expected = str(data_row[element_name])

            # 自引用检测：非 UI 模型的 verify 数据中不应使用 ${Return[-1]}
            if model_type != MODEL_TYPE_UI and '${Return[-1]}' in raw_expected:
                logger.warning(
                    f"[空校验警告] {element_name}: 期望值 '{raw_expected}' "
                    f"引用了 Return[-1]，但 verify 在接口/DB 模式下实际值也取自 "
                    f"Return[-1]，这会导致自己跟自己比较，断言永远通过。"
                    f"请改为具体的期望字面值。"
                )

            expected = raw_expected
            if self.data_resolver:
                expected = self.data_resolver.resolve_with_return(expected)

            expected_upper = expected.strip().upper()

            # BLANK: UI 跳过该字段不验证, 接口期望空字符串
            if expected_upper == 'BLANK':
                if model_type == MODEL_TYPE_UI:
                    logger.debug(f"{element_name}: BLANK → 跳过验证")
                    continue
                expected = ''

            # NULL → 接口期望 "null"; NONE → 接口期望 "none"; UI 均跳过
            if expected_upper in ('NULL', 'NONE'):
                if model_type == MODEL_TYPE_UI:
                    logger.debug(f"{element_name}: {expected_upper} → 跳过验证")
                    continue
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

            locator_type = element_info['locator_type']
            locator_value = element_info['locator_value']
            locator = f"{locator_type}={locator_value}"

            if model_type == MODEL_TYPE_UI:
                if hasattr(target_driver, 'get_text_locator'):
                    if locator_type == 'id':
                        actual = target_driver.get_text_locator(f"#{locator_value}")
                    elif locator_type == 'css':
                        actual = target_driver.get_text_locator(locator_value)
                    else:
                        actual = target_driver.get_text_locator(locator)
                else:
                    actual = target_driver.get_text(locator)
                actual_str = str(actual) if actual is not None else ""
            else:
                last_return = self.get_return(-1)
                if isinstance(last_return, dict):
                    actual_val = self._get_nested_return(last_return, locator_value or element_name)
                    actual_str = str(actual_val) if actual_val is not None else ""
                else:
                    actual_str = str(last_return) if last_return is not None else ""

            results[element_name] = actual_str
            matched = actual_str == expected
            logger.debug(f"{element_name}: 实际='{actual_str}', 期望='{expected}' → {'OK' if matched else 'FAIL'}")

            if not matched:
                mismatches.append({
                    'element': element_name,
                    'expected': expected,
                    'actual': actual_str,
                })

        if mismatches:
            failure_payload = dict(results)
            failure_payload['_verify_passed'] = False
            failure_payload['passed'] = False
            failure_payload['_verify_mismatches'] = mismatches
            self.store_return(failure_payload)

            detail = "; ".join(
                f"{m['element']}(期望='{m['expected']}', 实际='{m['actual']}')"
                for m in mismatches
            )
            logger.error(f"批量验证失败: {detail}")
            raise AssertionFailedError(
                message=f"批量验证失败: {detail}",
                details={'mismatches': mismatches},
            )

        success_payload = dict(results)
        success_payload['_verify_passed'] = True
        success_payload['passed'] = True
        self.store_return(success_payload)
        logger.info(f"批量验证通过: {len(results)} 个字段全部匹配")
        return True

    # 选择器前缀：含这些前缀的 data 视为 UI 选择器模式
    _SELECTOR_PREFIXES = ("#", ".", "//", "css=", "xpath=", "id=", "text=")

    def _kw_get(self, params: Dict) -> bool:
        """三模式取值关键字

        模式判断（按 model/data 格式）:
        1. model 非空 + data 为 DataID → 模型模式：按模型元素定位读取文本，返回 dict
        2. model 空 + data 含选择器前缀 → UI 选择器模式（低级补充）：直接读取元素文本
        3. model 空 + data 为普通标识符 → 命名访问模式：从 context.named 读取
        三种模式均写入 history。
        """
        model_name = params.get("model", "")
        data = params.get("data", "") or params.get("locator", "")

        # 模式 1: 模型模式
        if model_name and data and self.model_parser and self.data_manager:
            return self._get_model_mode(model_name, data)

        # 模式 2: UI 选择器模式
        if data and any(data.startswith(p) for p in self._SELECTOR_PREFIXES):
            return self._get_selector_mode(data, params.get("var_name", ""))

        # 模式 3: 命名访问模式
        if data:
            return self._get_named_mode(data)

        raise InvalidParameterError(keyword="get", param_name="data", reason="缺少必需参数")

    def _get_model_mode(self, model_name: str, data_ref: str) -> bool:
        """模型模式：按模型元素定位，读取各元素文本，返回 dict"""
        if self.model_parser.get_model_type(model_name) != MODEL_TYPE_UI:
            raise InvalidParameterError(keyword="get", param_name="model", reason=f"get 模型模式仅支持 UI 模型: '{model_name}'")
        model = self.model_parser.get_model(model_name) or {}
        result = {}
        for name, elem in model.items():
            if name.startswith('__'):
                continue
            locator_type = elem.get("locator_type", "")
            locator_value = elem.get("locator_value", "")
            try:
                if hasattr(self.driver, "get_text_locator"):
                    if locator_type == 'id':
                        text = self.driver.get_text_locator(f"#{locator_value}")
                    elif locator_type == 'css':
                        text = self.driver.get_text_locator(locator_value)
                    else:
                        text = self.driver.get_text_locator(f"{locator_type}={locator_value}")
                else:
                    text = self.driver.get_text(f"{locator_type}={locator_value}")
                result[name] = text
            except Exception as e:
                logger.warning(f"get 模型模式: 元素 {name} 读取失败: {e}")
                result[name] = None
        logger.info(f"get 模型模式: {model_name} -> {result}")
        self.store_return(result)
        return True

    def _get_selector_mode(self, locator: str, var_name: str = "") -> bool:
        """UI 选择器模式（低级补充）：直接用选择器读取元素文本"""
        logger.info(f"get UI选择器: {locator}")
        text = self.driver.get_text_locator(locator) if hasattr(self.driver, "get_text_locator") else self.driver.get_text(locator)
        if var_name:
            self._variables[var_name] = text
        self.store_return(text)
        return True

    def _get_named_mode(self, key: str) -> bool:
        """命名访问模式：从 context.named 读取"""
        if key not in self._context.named:
            raise InvalidParameterError(keyword="get", param_name="data", reason=f"命名变量 '{key}' 不存在，请先用 set 写入")
        value = self._context.named[key]
        logger.info(f"get 命名访问: {key} = '{value}'")
        self.store_return(value)
        return True

    def _kw_clear(self, params: Dict) -> bool:
        """清空输入框"""
        locator = params.get("locator", "") or params.get("data", "")
        logger.info(f"清空: {locator}")
        result = self.driver.clear(locator)
        if not result:
            raise DriverError(f"清空失败: {locator}")
        self.store_return(True)
        return result

    def _kw_get_text(self, params: Dict) -> bool:
        """[已废弃] 请改用 get 关键字"""
        import warnings
        warnings.warn("get_text 已废弃，请改用 get 关键字", DeprecationWarning, stacklevel=2)
        logger.warning("get_text 已废弃，请改用 get 关键字")
        return self._kw_get(params)

    def _kw_evaluate(self, params: Dict) -> bool:
        """在浏览器中执行 JavaScript 表达式并存储返回值

        用法: evaluate | javascript_expression
        表达式结果会自动 store_return，后续步骤通过 ${Return[-N]} 引用。
        """
        expression = params.get("expression", "") or params.get("data", "")
        if not expression:
            raise InvalidParameterError(
                keyword="evaluate",
                param_name="expression",
                reason="缺少 JavaScript 表达式"
            )

        # 先解析表达式中的 Return 引用
        if self.data_resolver:
            expression = self.data_resolver.resolve_with_return(expression)

        logger.info(f"执行 JS: {expression[:200]}")

        try:
            from ..drivers.playwright_driver import PlaywrightDriver
        except ImportError:
            from drivers.playwright_driver import PlaywrightDriver
        if not isinstance(self.driver, PlaywrightDriver):
            raise DriverError("evaluate 仅支持 Web 浏览器驱动（PlaywrightDriver）")

        try:
            result = self.driver.page.evaluate(expression)
        except Exception as e:
            raise DriverError(f"JavaScript 执行失败: {e}")

        logger.info(f"JS 结果: {str(result)[:200]}")
        self.store_return(result)
        return True

    def _kw_upload_file(self, params: Dict) -> bool:
        """上传文件"""
        locator = params.get("locator", "") or params.get("model", "")
        file_path = params.get("file_path", "") or params.get("data", "")
        logger.info(f"上传文件: {file_path} -> {locator}")
        result = self.driver.upload_file(locator, file_path)
        if not result:
            raise DriverError(f"上传文件失败: {file_path}")
        self.store_return(True)
        return result

    # ── 高级关键字 ─────────────────────────────────────────────────

    def _kw_set(self, params: Dict) -> bool:
        """写入命名变量到 context.named，并写入 history

        格式: set | key=value_expr
        value_expr 支持 ${Return[-1].field} 等已解析模板（由 data_resolver 在上游处理）
        """
        data = params.get("data", "") or params.get("value", "")
        if not data or "=" not in data:
            raise InvalidParameterError(keyword="set", param_name="data", reason="格式应为 key=value")
        key, value = data.split("=", 1)
        key = key.strip()
        if not key:
            raise InvalidParameterError(keyword="set", param_name="data", reason="key 不能为空")
        if self.data_resolver:
            value = self.data_resolver.resolve_with_return(value)
        logger.info(f"set: {key} = '{value}'")
        self._context.named[key] = value
        self.store_return(value)
        return True

    def _kw_run(self, params: Dict) -> bool:
        """执行代码 - 支持内置函数和外部脚本

        优先级:
        1. 内置函数：data 匹配 "函数名(参数...)" 格式时，查 BUILTIN_REGISTRY
        2. 外部脚本：未匹配内置函数时，走 fun/ 目录脚本逻辑

        内置函数格式: run | | mock_route('/api/users', status=200, body='[]')
        外部脚本格式: run | 工程名 | 代码文件路径

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

        # ── 内置函数查找 ──────────────────────────────────────────
        if code_path and not project_name:
            builtin_result = self._try_builtin_call(code_path)
            if builtin_result is not None:
                return builtin_result

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
            parts = code_path.split(None, 1)
            script_file = parts[0]
            script_args = parts[1].split() if len(parts) > 1 else []
            script_path = (project_dir / script_file).resolve()
        else:
            parts = code_path.split(None, 1)
            script_file = parts[0]
            script_args = parts[1].split() if len(parts) > 1 else []
            project_dir = fun_dir.resolve()
            script_path = (fun_dir / script_file).resolve()

        if not script_path.exists():
            raise InvalidParameterError(
                keyword="run", param_name="data",
                reason=f"代码文件不存在: {script_path}"
            )

        logger.info(f"执行代码: {script_path}")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)] + script_args,
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

    @staticmethod
    def _parse_builtin_call(expr: str) -> Optional[tuple]:
        """解析内置函数调用表达式

        支持格式: 函数名(参数1, key=value, ...)

        Args:
            expr: 表达式字符串

        Returns:
            (函数名, args列表, kwargs字典) 或 None（不是函数调用格式）
        """
        expr = expr.strip()
        paren_start = expr.find('(')
        if paren_start == -1 or not expr.endswith(')'):
            return None

        func_name = expr[:paren_start].strip()
        if not func_name or not func_name.isidentifier():
            return None

        args_str = expr[paren_start + 1:-1].strip()
        if not args_str:
            return (func_name, [], {})

        # 解析参数：支持字符串引号、嵌套括号
        args = []
        kwargs = {}
        current = ""
        depth = 0
        in_str = None  # None / "'" / '"'

        for ch in args_str:
            if in_str:
                current += ch
                if ch == in_str:
                    in_str = None
                continue
            if ch in ("'", '"'):
                in_str = ch
                current += ch
                continue
            if ch in ('(', '[', '{'):
                depth += 1
                current += ch
                continue
            if ch in (')', ']', '}'):
                depth -= 1
                current += ch
                continue
            if ch == ',' and depth == 0:
                _add_parsed_arg(current.strip(), args, kwargs)
                current = ""
                continue
            current += ch

        if current.strip():
            _add_parsed_arg(current.strip(), args, kwargs)

        return (func_name, args, kwargs)

    def _try_builtin_call(self, expr: str) -> Optional[bool]:
        """尝试将 data 作为内置函数调用

        Args:
            expr: data 列的值

        Returns:
            True（调用成功）/ None（非内置函数格式或未注册）
        """
        parsed = self._parse_builtin_call(expr)
        if parsed is None:
            return None

        func_name, args, kwargs = parsed

        try:
            from ..builtin_ops import get_builtin
        except ImportError:
            try:
                from builtin_ops import get_builtin
            except ImportError:
                return None

        func = get_builtin(func_name)
        if func is None:
            return None

        # 注入运行时上下文
        kwargs["_context"] = {
            "driver": self.driver,
            "context": self._context,
            "global_vars": self._global_vars,
        }

        logger.info(f"调用内置函数: {func_name}")

        try:
            result = func(*args, **kwargs)
            self.store_return(result)
            logger.info(f"内置函数 {func_name} 执行成功")
            return True
        except Exception as e:
            logger.error(f"内置函数 {func_name} 执行失败: {e}")
            raise

    def _kw_db(self, params: Dict) -> bool:
        """数据库操作 - v5.0 新语法

        新语法格式: DB | 模型名 | 数据行ID

        执行流程:
        1. model 字段 = 数据模型名称 (如 OrderQuery)
        2. data 字段 = 数据行 ID (如 Q001)
        3. 从模型读取 connection 属性和 query 定义
        4. 从数据表读取 query 名称和参数
        5. 替换 SQL 中的 :param 占位符
        6. 执行 SQL → 截断处理 → store_return 保存结果

        ⚠️ 破坏性更新: 不兼容旧语法 (model=连接名, data=TableName.DataID)
        """
        model_name = params.get("model", "")
        data_id = params.get("data", "")

        if not model_name:
            raise InvalidParameterError(
                keyword="DB",
                param_name="model",
                reason="缺少模型名称。新语法: action='DB' model='模型名' data='数据ID'"
            )

        if not data_id:
            raise InvalidParameterError(
                keyword="DB",
                param_name="data",
                reason="缺少数据行 ID"
            )

        # 检测旧语法并报错
        if '.' in data_id:
            raise InvalidParameterError(
                keyword="DB",
                param_name="data",
                reason=(
                    f"检测到旧语法格式 '{data_id}'。\n"
                    f"v5.0+ 不再支持旧语法，请迁移到新语法:\n"
                    f"  旧: <test_step action='DB' model='sqlite_db' data='QuerySQL.Q001'/>\n"
                    f"  新: <test_step action='DB' model='OrderQuery' data='Q001'/>\n"
                    f"详见迁移文档: .pb/specs/db_keyword_design_v2.md"
                )
            )

        # 1. 从 model_parser 读取模型
        if not self.model_parser:
            raise DriverError("ModelParser 未初始化")

        db_model = self.model_parser.get_database_model(model_name)
        if not db_model:
            model_type = self.model_parser.get_model_type(model_name)
            if model_type and model_type != 'database':
                raise InvalidParameterError(
                    keyword="DB",
                    param_name="model",
                    reason=f"模型 '{model_name}' 的类型是 '{model_type}'，不是 'database'。DB 关键字只能使用 type='database' 的模型。"
                )
            raise InvalidParameterError(
                keyword="DB",
                param_name="model",
                reason=f"模型 '{model_name}' 不存在或不是 database 类型"
            )

        connection_name = db_model.get('connection', '')
        if not connection_name:
            raise InvalidParameterError(
                keyword="DB",
                param_name="model",
                reason=f"模型 '{model_name}' 缺少 connection 属性"
            )

        queries = db_model.get('queries', {})

        # 2. 从数据表读取数据
        if not self.data_manager:
            raise DriverError("DataManager 未初始化")

        row_data = self.data_manager.get_data(model_name, data_id)
        if not row_data:
            raise InvalidParameterError(
                keyword="DB",
                param_name="data",
                reason=f"数据表 '{model_name}' 中未找到数据行 '{data_id}'"
            )

        # 3. 获取 SQL（支持两种模式）
        sql = None
        operation = 'query'

        # 模式1: 数据表中直接写 SQL
        if 'sql' in row_data or 'SQL' in row_data:
            sql = str(row_data.get('sql', '') or row_data.get('SQL', '')).strip()
            operation = str(row_data.get('operation', '') or row_data.get('Operation', 'query')).strip().lower()

        # 模式2: 数据表引用模型中的 query
        elif 'query' in row_data:
            query_name = str(row_data.get('query', '')).strip()
            if not query_name:
                raise InvalidParameterError(
                    keyword="DB",
                    param_name="data",
                    reason=f"数据行 '{data_id}' 的 query 字段为空"
                )

            if query_name not in queries:
                raise InvalidParameterError(
                    keyword="DB",
                    param_name="data",
                    reason=f"模型 '{model_name}' 中未定义查询 '{query_name}'。可用查询: {list(queries.keys())}"
                )

            sql = queries[query_name]['sql']
            # 根据 SQL 类型自动判断 operation
            operation = 'query' if sql.strip().upper().startswith('SELECT') else 'execute'

        if not sql:
            raise InvalidParameterError(
                keyword="DB",
                param_name="data",
                reason=f"数据行 '{data_id}' 中未找到 'sql' 或 'query' 字段"
            )

        # 4. 替换参数化查询中的 :param
        sql = self._replace_sql_params(sql, row_data)

        logger.info(f"DB {operation}: {sql[:80]}{'...' if len(sql) > 80 else ''}")

        # 5. 获取数据库连接
        connection = self._get_db_connection(connection_name)
        if not connection:
            raise DriverError(f"数据库连接失败: 连接配置 '{connection_name}' 未配置或连接失败")

        # 6. 执行 SQL
        try:
            result = self._execute_db_sql(connection, operation, sql)

            # 7. 大数据量截断处理
            if operation == 'query' and isinstance(result, list):
                result = self._truncate_result(result)

            self.store_return(result)
            logger.info(f"DB 操作成功 ({operation})")
            return True
        except Exception as e:
            logger.error(f"SQL 执行失败: {e}")
            self.store_return(None)
            raise DriverError(f"SQL 执行失败: {e}")

    def _replace_sql_params(self, sql: str, params: Dict[str, Any]) -> str:
        """替换 SQL 中的 :param 占位符

        Args:
            sql: SQL 语句，包含 :param 占位符
            params: 参数字典

        Returns:
            替换后的 SQL

        示例:
            sql = "SELECT * FROM orders WHERE status = :status LIMIT :limit"
            params = {"status": "completed", "limit": 10}
            返回: "SELECT * FROM orders WHERE status = 'completed' LIMIT 10"
        """
        import re

        def replace_param(match):
            param_name = match.group(1)
            if param_name not in params:
                raise InvalidParameterError(
                    keyword="DB",
                    param_name=param_name,
                    reason=f"SQL 中引用了参数 ':{param_name}'，但数据表中未提供该参数"
                )

            value = params[param_name]

            # None → NULL
            if value is None or str(value).upper() == 'NULL':
                return 'NULL'

            # 数字类型不加引号
            if isinstance(value, (int, float)):
                return str(value)

            # 字符串类型加单引号，并转义单引号
            value_str = str(value).replace("'", "''")
            return f"'{value_str}'"

        # 匹配 :param_name 格式（参数名只能是字母、数字、下划线）
        pattern = r':(\w+)'
        result = re.sub(pattern, replace_param, sql)

        return result

    def _truncate_result(self, result: List[Dict], limit: int = 1000) -> Union[List[Dict], Dict]:
        """截断查询结果

        Args:
            result: 查询结果列表
            limit: 最大行数，默认 1000

        Returns:
            如果未超过限制，返回原结果
            如果超过限制，返回截断后的结果（包含 _truncated 标记）
        """
        if not isinstance(result, list):
            return result

        total_rows = len(result)
        if total_rows <= limit:
            return result

        # 截断并添加标记
        logger.warning(f"查询结果超过 {limit} 行（实际 {total_rows} 行），已自动截断")

        truncated_result = result[:limit]
        # 添加元数据（作为特殊字段）
        return {
            '_truncated': True,
            '_total_rows': total_rows,
            '_limit': limit,
            'data': truncated_result
        }

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
