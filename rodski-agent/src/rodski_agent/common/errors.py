"""错误分类体系 — 为 rodski-agent 提供结构化的错误类型。

所有 Agent 层异常继承自 ``AgentError``，携带：
  - code: 机器可读的错误码（如 "E_CONFIG_MISSING"）
  - category: ErrorCategory 枚举
  - message: 人类可读描述
  - details: 可选附加上下文
  - suggestion: 可选修复建议

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCategory(Enum):
    """错误分类枚举。"""

    CONFIG_ERROR = "config_error"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    PARSE_ERROR = "parse_error"
    LLM_ERROR = "llm_error"
    TIMEOUT_ERROR = "timeout_error"
    INTERNAL_ERROR = "internal_error"


class AgentError(Exception):
    """rodski-agent 统一异常基类。

    Parameters
    ----------
    code : str
        机器可读错误码，如 ``"E_CONFIG_MISSING"``。
    category : ErrorCategory
        错误分类。
    message : str
        人类可读的错误描述。
    details : dict | None
        可选的附加上下文。
    suggestion : str | None
        可选的修复建议。
    """

    def __init__(
        self,
        code: str,
        category: ErrorCategory,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.category = category
        self.message = message
        self.details = details
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 化的字典。"""
        d: Dict[str, Any] = {
            "code": self.code,
            "category": self.category.value,
            "message": self.message,
        }
        if self.details is not None:
            d["details"] = self.details
        if self.suggestion is not None:
            d["suggestion"] = self.suggestion
        return d


# ============================================================
# 具体子类
# ============================================================


class ConfigError(AgentError):
    """配置相关错误（文件缺失、格式错误、值非法等）。"""

    def __init__(
        self,
        message: str,
        code: str = "E_CONFIG",
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(
            code=code,
            category=ErrorCategory.CONFIG_ERROR,
            message=message,
            details=details,
            suggestion=suggestion,
        )


class ValidationError(AgentError):
    """输入校验错误（路径不存在、目录结构不完整等）。"""

    def __init__(
        self,
        message: str,
        code: str = "E_VALIDATION",
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(
            code=code,
            category=ErrorCategory.VALIDATION_ERROR,
            message=message,
            details=details,
            suggestion=suggestion,
        )


class ExecutionError(AgentError):
    """测试执行过程中的错误（rodski 调用失败、非预期退出码等）。"""

    def __init__(
        self,
        message: str,
        code: str = "E_EXECUTION",
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(
            code=code,
            category=ErrorCategory.EXECUTION_ERROR,
            message=message,
            details=details,
            suggestion=suggestion,
        )


class ParseError(AgentError):
    """结果解析错误（XML/JSON 格式异常、字段缺失等）。"""

    def __init__(
        self,
        message: str,
        code: str = "E_PARSE",
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(
            code=code,
            category=ErrorCategory.PARSE_ERROR,
            message=message,
            details=details,
            suggestion=suggestion,
        )


class LLMError(AgentError):
    """LLM 调用相关错误（API 超时、模型不可用等）。"""

    def __init__(
        self,
        message: str,
        code: str = "E_LLM",
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(
            code=code,
            category=ErrorCategory.LLM_ERROR,
            message=message,
            details=details,
            suggestion=suggestion,
        )


class TimeoutError_(AgentError):
    """超时错误（执行超时、等待超时等）。

    名称带下划线以避免与内置 ``TimeoutError`` 冲突。
    """

    def __init__(
        self,
        message: str,
        code: str = "E_TIMEOUT",
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(
            code=code,
            category=ErrorCategory.TIMEOUT_ERROR,
            message=message,
            details=details,
            suggestion=suggestion,
        )


class InternalError(AgentError):
    """内部错误（未预期的异常、编程错误等）。"""

    def __init__(
        self,
        message: str,
        code: str = "E_INTERNAL",
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(
            code=code,
            category=ErrorCategory.INTERNAL_ERROR,
            message=message,
            details=details,
            suggestion=suggestion,
        )
