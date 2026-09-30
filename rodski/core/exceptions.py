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
import xml.etree.ElementTree as _ET
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


class DuplicateCaseIdInFileError(ParseError):
    """同一用例文件内 case@id 重复（含 execute="否" 的用例）。

    v11.5.0 起：case 目录支持多级嵌套，用例 ID 只要求在**同一文件内**唯一；
    跨文件允许同 ID（内部用 ``{case_file}::{case_id}`` 作为完整标识）。
    """

    error_code = "SKI205"

    def __init__(self, case_file: str, case_id: str, **kwargs):
        self.case_file = case_file
        self.case_id = case_id
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"case_file": case_file, "case_id": case_id})
        super().__init__(
            f"用例文件内 ID 重复: file={case_file}, id={case_id}",
            details=details,
            **kwargs,
        )


class ReservedCaseSubdirNameError(ParseError):
    """case/ 下的子目录使用了保留名（case/model/fun/data/plan/result/business/perf/knowledge）。

    保留名保证「向上查找最近的 case 祖先」在任意嵌套深度下都能唯一推导模块目录。
    """

    error_code = "SKI206"

    def __init__(self, path: str, name: str, **kwargs):
        self.path = path
        self.name = name
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"path": path, "name": name})
        super().__init__(
            f"case/ 下的子目录不得使用保留名 '{name}': {path}",
            details=details,
            **kwargs,
        )


class XmlSchemaValidationError(ParseError):
    """XML 实例不符合对应 XSD Schema 约束"""

    error_code = "SKI204"

    def __init__(
        self,
        message: str,
        xml_path: Optional[str] = None,
        document_kind: Optional[str] = None,
        schema_path: Optional[str] = None,
        validation_errors: Optional[list] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if xml_path:
            details["xml_path"] = xml_path
        if document_kind:
            details["document_kind"] = document_kind
        if schema_path:
            details["schema_path"] = schema_path
        if validation_errors:
            details["validation_errors"] = validation_errors
        super().__init__(message, details=details, **kwargs)


class XmlSyntaxError(ParseError, _ET.ParseError):
    """v11.6.0 (C3)：XML 格式错误（非良构），附带修复提示。

    同时继承 ``xml.etree.ElementTree.ParseError``，存量 ``except ET.ParseError`` 仍能捕获。
    """

    error_code = "SKI200"

    def __init__(self, message: str, xml_path: Optional[str] = None,
                 line: Optional[int] = None, column: Optional[int] = None,
                 hint: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if xml_path:
            details["xml_path"] = xml_path
        if line is not None:
            details["line"] = line
        if column is not None:
            details["column"] = column
        if hint:
            details["hint"] = hint
        super().__init__(message, details=details, **kwargs)
        self.position = (line, column) if line is not None else None
        self.hint = hint


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
    "SKI204": XmlSchemaValidationError,
    "SKI205": DuplicateCaseIdInFileError,
    "SKI206": ReservedCaseSubdirNameError,
}


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
        # v11.6.0 C4：UI 原子动作误写为关键字时附带修复提示（CORE §1.2）
        ui_atomic = {"click", "double_click", "right_click", "hover", "select",
                     "key_press", "drag", "scroll", "switch_frame", "switch_window"}
        if str(keyword).lower() in ui_atomic:
            hint = ("click/hover/select 等是 type 数据表里的字段值，不是关键字（CORE §1.2）。"
                    "示例: action=\"type\" model=\"Login\" data=\"L001\"，数据表 loginBtn 字段填 click")
            message += f" 提示: {hint}"
            details = kwargs.pop("details", {}) or {}
            details["hint"] = hint
            kwargs["details"] = details
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
        # attempts 是总尝试次数；未配置步骤级重试时只执行了 1 次，不能写成"重试 1 次"（v11.7.0）
        if attempts <= 1:
            message = f"关键字 '{keyword}' 执行失败: {last_error}"
        else:
            message = f"关键字 '{keyword}' 共尝试 {attempts} 次（步骤级重试 {attempts - 1} 次）后仍失败: {last_error}"
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


class ElementNotInteractableError(DriverError):
    """v11.7.0：元素已找到但暂不可操作（不可见 / disabled / 被遮挡 / 动作单次超时），自动等待内重试"""
    error_code = "SKI327"
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


class UnexpectedDialogError(DriverError):
    """v11.6.0 (C1)：DialogPolicy=fail 时出现未注册处理器的原生弹窗（不重试）"""
    error_code = "SKI325"

    def __init__(self, dialog_text: str, keyword: Optional[str] = None, **kwargs):
        message = (
            f"出现未预期的弹窗: {dialog_text}（DialogPolicy=fail，已自动关闭）。"
            f"修复: 在 UI 模型中声明 <location type=\"page\">dialog</location> 元素并排在触发按钮之前，"
            f"type 数据行填 accept / dismiss / accept:输入文本；或设置 DefaultValue.DialogPolicy=accept|dismiss"
        )
        details = kwargs.pop("details", {})
        details["dialog_text"] = dialog_text
        if keyword:
            details["keyword"] = keyword
        super().__init__(message, details=details, **kwargs)
        self.dialog_text = dialog_text


class DiagnosisTimeoutError(ExecutionError):
    """诊断超时错误"""
    error_code = "SKI340"


class AutoCaptureError(ExecutionError):
    """自动返回值提取失败"""
    error_code = "SKI332"

    def __init__(self, field: str, source: str, reason: str):
        self.field = field
        self.source = source
        self.reason = reason
        super().__init__(f"AutoCapture 失败: field={field}, source={source}, reason={reason}")


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


ERROR_CODE_MAP.update({
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
    "SKI315": DiagnosisTimeoutError,
    "SKI316": AutoCaptureError,
    "SKI331": AssertionFailedError,
    "SKI400": ConnectionError,
    "SKI401": DatabaseConnectionError,
    "SKI402": APIConnectionError,
})


class PlanCaseFileRequiredError(ParseError):
    """多用例文件模块中 plan 的 <case> 省略了 file 属性。

    v11.5.0 起：plan 中 <case> 必须指定 file 属性（唯一例外：模块 case/ 下
    递归只有一个用例文件时可以省略，自动指向该文件）。
    """

    error_code = "SKI207"

    def __init__(self, case_id: str, candidates: list[str], **kwargs):
        self.case_id = case_id
        self.candidates = candidates
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"case_id": case_id, "candidates": candidates})
        candidates_str = "\n  - ".join(candidates) if candidates else "(无匹配文件)"
        example_file = candidates[0] if candidates else "<相对 case/ 的用例文件路径>"
        super().__init__(
            f"多用例文件模块中 plan case 引用必须指定 file 属性: id={case_id}\n"
            f"包含该 ID 的候选文件:\n  - {candidates_str}\n"
            f"请补充 file 属性，如: <case file=\"{example_file}\" id=\"{case_id}\"/>",
            details=details,
            **kwargs,
        )


class CaseIdRequiresFileError(ParseError):
    """--case-id 未与单个用例文件路径一起使用，或与 @plan_id 同用。

    v11.5.0 起：--case-id 必须与单个用例文件路径一起使用（避免跨文件同 ID 产生歧义），
    且与 @plan_id 固定互斥。
    """

    error_code = "SKI208"

    def __init__(self, reason: str, **kwargs):
        self.reason = reason
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"reason": reason})
        super().__init__(
            f"--case-id 使用错误: {reason}",
            details=details,
            **kwargs,
        )


class LoadModeUnsupportedError(SKIError):
    """在压测模式下调用了 UI 操作。"""
    error_code = "SKI601"

    def __init__(self, method_name: str = ""):
        msg = f"LoadDriver 不支持 UI 操作 '{method_name}'。压测计划只能包含 component_type='接口' 的 case。" if method_name else "LoadDriver 不支持 UI 操作。"
        super().__init__(msg)
        self.method_name = method_name


class LoadModeUnsupportedCaseError(SKIError):
    """压测计划（api 模式）引用了非接口类型的 case。"""
    error_code = "SKI602"


class LoadDependencyMissingError(SKIError):
    """压测依赖（locust）未安装。"""
    error_code = "SKI603"

    def __init__(self):
        super().__init__("压测功能需要安装 locust：\n  pip install rodski[load]")


class LoadBrowserModeUnsupportedCaseError(SKIError):
    """压测计划（browser 模式）引用了非界面类型的 case。"""
    error_code = "SKI604"


ERROR_CODE_MAP.update({
    "SKI601": LoadModeUnsupportedError,
    "SKI602": LoadModeUnsupportedCaseError,
    "SKI603": LoadDependencyMissingError,
    "SKI604": LoadBrowserModeUnsupportedCaseError,
})


class HookDeniedError(ExecutionError):
    """Hook 拦截了当前操作（before_keyword deny，或外部命令 hook 返回 exit code 2）。"""
    error_code = "SKI701"

    def __init__(self, event: str, reason: str, **kwargs):
        self.event = event
        self.reason = reason
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"event": event, "reason": reason})
        super().__init__(f"Hook 拒绝执行: event={event}, reason={reason}", details=details, **kwargs)


class HookTimeoutError(ExecutionError):
    """外部命令 hook 执行超时。"""
    error_code = "SKI702"
    error_level = "WARNING"

    def __init__(self, event: str, timeout: float, **kwargs):
        self.event = event
        self.timeout = timeout
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"event": event, "timeout": timeout})
        super().__init__(f"Hook 执行超时: event={event}, timeout={timeout}s", details=details, **kwargs)


class ComplianceCheckFailedError(ExecutionError):
    """on_run_start 内置合规检查未通过（未使用 --force-compliance）。"""
    error_code = "SKI703"

    def __init__(self, checks_failed: list, **kwargs):
        self.checks_failed = checks_failed
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"checks_failed": checks_failed})
        names = ", ".join(c.get("check_name", "") for c in checks_failed) if checks_failed else ""
        super().__init__(f"合规检查未通过: {names}", details=details, **kwargs)


ERROR_CODE_MAP.update({
    "SKI701": HookDeniedError,
    "SKI702": HookTimeoutError,
    "SKI703": ComplianceCheckFailedError,
})


class RoamCaseNotFoundError(ExecutionError):
    """定向漫游指定的用例不存在。"""

    error_code = "SKI801"

    def __init__(self, case_id: str, search_path: str = "", **kwargs):
        self.case_id = case_id
        details = dict(kwargs.pop("details", {}) or {})
        details["case_id"] = case_id
        if search_path:
            details["search_path"] = search_path
        super().__init__(f"未找到漫游用例: {case_id}", details=details, **kwargs)


class RoamNotEligibleError(ExecutionError):
    """定向漫游未满足三层开关。"""

    error_code = "SKI802"

    def __init__(self, case_id: str, reasons: list, **kwargs):
        self.case_id = case_id
        self.reasons = list(reasons)
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"case_id": case_id, "reasons": self.reasons})
        reason_text = "; ".join(str(reason) for reason in self.reasons)
        super().__init__(f"用例不满足漫游条件: {case_id}: {reason_text}", details=details, **kwargs)


class RoamUnsupportedCaseError(ExecutionError):
    """非界面用例声明了 roam=是。"""

    error_code = "SKI803"

    def __init__(self, case_id: str, component_type: str, **kwargs):
        self.case_id = case_id
        self.component_type = component_type
        details = dict(kwargs.pop("details", {}) or {})
        details.update({"case_id": case_id, "component_type": component_type})
        super().__init__(
            f"漫游测试仅支持界面用例: case={case_id}, component_type={component_type}",
            details=details,
            **kwargs,
        )


ERROR_CODE_MAP.update({
    "SKI801": RoamCaseNotFoundError,
    "SKI802": RoamNotEligibleError,
    "SKI803": RoamUnsupportedCaseError,
})


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
