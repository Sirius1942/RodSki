"""SKI 框架统一异常类型体系

异常层级:
  SKIError (基类)
  ├── ConfigurationError (配置错误)
  ├── ParseError (解析错误)
  │   ├── CaseParseError (用例解析错误)
  │   ├── ModelParseError (模型解析错误)
  │   └── DataParseError (数据解析错误)
  ├── ExecutionError (执行错误)
  │   ├── KeywordError (关键字错误)
  │   │   ├── UnknownKeywordError (未知关键字)
  │   │   ├── InvalidParameterError (参数错误)
  │   │   └── RetryExhaustedError (重试耗尽)
  │   ├── DriverError (驱动错误)
  │   │   ├── ElementNotFoundError (元素未找到)
  │   │   ├── TimeoutError (超时)
  │   │   └── StaleElementError (元素失效)
  │   └── AssertionError (断言失败)
  └── ConnectionError (连接错误)
      ├── DatabaseConnectionError (数据库连接错误)
      └── APIConnectionError (API连接错误)
"""
from typing import Optional, Dict, Any


class SKIError(Exception):
    """SKI 框架基础异常类"""
    
    error_code: str = "SKI000"
    error_level: str = "ERROR"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.details:
            for key, value in self.details.items():
                parts.append(f"  {key}: {value}")
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于日志和报告"""
        return {
            "error_code": self.error_code,
            "error_level": self.error_level,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


# ── 配置错误 ──────────────────────────────────────────────────

class ConfigurationError(SKIError):
    """配置错误"""
    error_code = "SKI001"


class ConfigFileNotFoundError(ConfigurationError):
    """配置文件未找到"""
    error_code = "SKI101"


class InvalidConfigError(ConfigurationError):
    """无效配置"""
    error_code = "SKI102"


# ── 解析错误 ──────────────────────────────────────────────────

class ParseError(SKIError):
    """解析错误基类"""
    error_code = "SKI200"


class CaseParseError(ParseError):
    """用例解析错误"""
    error_code = "SKI201"
    
    def __init__(
        self, 
        message: str, 
        case_file: Optional[str] = None,
        case_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if case_file:
            details["case_file"] = case_file
        if case_id:
            details["case_id"] = case_id
        super().__init__(message, details=details, **kwargs)


class ModelParseError(ParseError):
    """模型解析错误"""
    error_code = "SKI202"
    
    def __init__(
        self, 
        message: str, 
        model_file: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if model_file:
            details["model_file"] = model_file
        if model_name:
            details["model_name"] = model_name
        super().__init__(message, details=details, **kwargs)


class DataParseError(ParseError):
    """数据解析错误"""
    error_code = "SKI203"


# ── 执行错误 ──────────────────────────────────────────────────

class ExecutionError(SKIError):
    """执行错误基类"""
    error_code = "SKI300"


class KeywordError(ExecutionError):
    """关键字错误基类"""
    error_code = "SKI301"
    
    def __init__(
        self, 
        message: str, 
        keyword: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if keyword:
            details["keyword"] = keyword
        super().__init__(message, details=details, **kwargs)


class UnknownKeywordError(KeywordError):
    """未知关键字"""
    error_code = "SKI311"
    
    def __init__(self, keyword: str, supported: list, **kwargs):
        message = f"未知关键字: '{keyword}'。支持的关键字: {', '.join(supported[:10])}..."
        super().__init__(message, keyword=keyword, **kwargs)
        self.supported = supported


class InvalidParameterError(KeywordError):
    """无效参数"""
    error_code = "SKI312"
    
    def __init__(
        self, 
        keyword: str, 
        param_name: str,
        reason: str = "缺少必需参数",
        **kwargs
    ):
        message = f"关键字 '{keyword}' 参数错误: {param_name} - {reason}"
        super().__init__(message, keyword=keyword, **kwargs)
        self.param_name = param_name
        self.reason = reason


class RetryExhaustedError(KeywordError):
    """重试次数耗尽"""
    error_code = "SKI313"
    
    def __init__(
        self, 
        keyword: str, 
        attempts: int,
        last_error: Exception,
        **kwargs
    ):
        message = f"关键字 '{keyword}' 重试 {attempts} 次后仍失败: {last_error}"
        super().__init__(message, keyword=keyword, **kwargs)
        self.attempts = attempts
        self.last_error = last_error


class DriverError(ExecutionError):
    """驱动错误基类"""
    error_code = "SKI302"
    
    def __init__(
        self, 
        message: str, 
        locator: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if locator:
            details["locator"] = locator
        super().__init__(message, details=details, **kwargs)


class ElementNotFoundError(DriverError):
    """元素未找到"""
    error_code = "SKI321"
    error_level = "WARNING"


class TimeoutError(DriverError):
    """超时错误"""
    error_code = "SKI322"
    error_level = "WARNING"


class StaleElementError(DriverError):
    """元素失效"""
    error_code = "SKI323"
    error_level = "WARNING"


class DriverStoppedError(DriverError):
    """驱动已停止"""
    error_code = "SKI324"
    error_level = "CRITICAL"
    
    def __init__(
        self, 
        message: str = "驱动已停止，无法继续执行操作",
        driver_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if driver_type:
            details["driver_type"] = driver_type
        super().__init__(message, **kwargs)
        self.driver_type = driver_type


class AssertionFailedError(ExecutionError):
    """断言失败"""
    error_code = "SKI331"
    
    def __init__(
        self, 
        message: str,
        expected: Any = None,
        actual: Any = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if expected is not None:
            details["expected"] = str(expected)
        if actual is not None:
            details["actual"] = str(actual)
        super().__init__(message, details=details, **kwargs)
        self.expected = expected
        self.actual = actual


# ── 连接错误 ──────────────────────────────────────────────────

class ConnectionError(SKIError):
    """连接错误基类"""
    error_code = "SKI400"


class DatabaseConnectionError(ConnectionError):
    """数据库连接错误"""
    error_code = "SKI401"
    
    def __init__(
        self, 
        message: str, 
        db_name: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if db_name:
            details["database"] = db_name
        super().__init__(message, details=details, **kwargs)


class APIConnectionError(ConnectionError):
    """API连接错误"""
    error_code = "SKI402"
    
    def __init__(
        self, 
        message: str, 
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if url:
            details["url"] = url
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details=details, **kwargs)


# ── 错误码映射 ──────────────────────────────────────────────────

ERROR_CODE_MAP = {
    "SKI000": SKIError,
    "SKI001": ConfigurationError,
    "SKI101": ConfigFileNotFoundError,
    "SKI102": InvalidConfigError,
    "SKI200": ParseError,
    "SKI201": CaseParseError,
    "SKI202": ModelParseError,
    "SKI203": DataParseError,
    "SKI300": ExecutionError,
    "SKI301": KeywordError,
    "SKI311": UnknownKeywordError,
    "SKI312": InvalidParameterError,
    "SKI313": RetryExhaustedError,
    "SKI302": DriverError,
    "SKI321": ElementNotFoundError,
    "SKI322": TimeoutError,
    "SKI323": StaleElementError,
    "SKI324": DriverStoppedError,
    "SKI331": AssertionFailedError,
    "SKI400": ConnectionError,
    "SKI401": DatabaseConnectionError,
    "SKI402": APIConnectionError,
}


def get_error_by_code(code: str) -> Optional[type]:
    """根据错误码获取异常类型"""
    return ERROR_CODE_MAP.get(code)


def is_retryable_error(error: Exception) -> bool:
    """判断错误是否可重试"""
    retryable_codes = ["SKI321", "SKI322", "SKI323"]  # ElementNotFound, Timeout, StaleElement
    if isinstance(error, SKIError):
        return error.error_code in retryable_codes
    return False


def is_critical_error(error: Exception) -> bool:
    """判断是否为严重错误（不可恢复）"""
    critical_codes = ["SKI324"]  # DriverStopped
    if isinstance(error, SKIError):
        return error.error_code in critical_codes
    # 检查常见的严重错误消息
    error_msg = str(error).lower()
    critical_patterns = [
        "event loop is closed",
        "playwright already stopped",
        "browser has been closed",
        "target closed",
        "session closed",
    ]
    return any(pattern in error_msg for pattern in critical_patterns)