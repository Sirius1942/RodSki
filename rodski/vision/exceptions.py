"""视觉定位专用异常类型

继承自 core.exceptions 的 SKIError 基类，提供视觉模块专用错误层级：

  VisionError (基类, SKI500)
  ├── ElementNotFoundError  (SKI501) 元素未找到
  ├── OmniParserError       (SKI502) OmniParser 服务异常
  ├── LLMAnalysisError      (SKI503) LLM 调用失败
  ├── CoordinateError       (SKI504) 坐标无效或超出屏幕范围
  └── VisionTimeoutError    (SKI505) 视觉定位超时
"""
from typing import Optional

try:
    from rodski.core.exceptions import SKIError
    _BASE = SKIError
except ImportError:
    # 降级：直接继承 Exception，保持模块独立可用
    _BASE = Exception  # type: ignore


class VisionError(_BASE):
    """视觉定位基础异常"""

    error_code: str = "SKI500"
    error_level: str = "ERROR"

    def __init__(self, message: str, **kwargs):
        if _BASE is Exception:
            super().__init__(message)
            self.message = message
            self.details = {}
            self.cause = None
        else:
            super().__init__(message, **kwargs)

    def __str__(self) -> str:
        return self.args[0] if self.args else self.message


class ElementNotFoundError(VisionError):
    """目标元素在截图中未找到

    建议：
    1. 确认页面已完全加载后再重试
    2. 检查目标描述是否准确（如语言、措辞）
    3. 适当增加等待时间或重试次数
    """

    error_code = "SKI501"

    def __init__(
        self,
        target: str,
        screenshot_path: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ):
        self.target = target
        self.screenshot_path = screenshot_path
        msg = message or (
            f"未找到目标元素 '{target}'" +
            (f"，截图路径：{screenshot_path}" if screenshot_path else "") +
            "。建议：确认页面已完全加载，检查目标描述是否准确。"
        )
        super().__init__(msg, **kwargs)

    def __str__(self) -> str:
        return (
            f"[SKI501] ElementNotFoundError: 目标='{self.target}'"
            + (f", 截图={self.screenshot_path}" if self.screenshot_path else "")
            + " | 建议：确认页面已加载，核对元素描述文字，可适当增加重试次数。"
        )


class OmniParserError(VisionError):
    """OmniParser 服务调用异常

    建议：
    1. 检查 OmniParser 服务是否正常运行
    2. 确认服务 URL 和端口配置正确
    3. 查看服务端日志排查具体错误
    """

    error_code = "SKI502"

    def __init__(
        self,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        message: Optional[str] = None,
        **kwargs,
    ):
        self.url = url
        self.status_code = status_code
        msg = message or (
            "OmniParser 服务异常"
            + (f"，请求地址：{url}" if url else "")
            + (f"，HTTP 状态码：{status_code}" if status_code is not None else "")
            + "。建议：检查服务是否运行、网络是否可达。"
        )
        super().__init__(msg, **kwargs)

    def __str__(self) -> str:
        parts = ["[SKI502] OmniParserError"]
        if self.url:
            parts.append(f"url={self.url}")
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        parts.append("| 建议：确认 OmniParser 服务正常运行，检查 URL 和端口配置。")
        return ", ".join(parts[:1]) + ": " + ", ".join(parts[1:])


class LLMAnalysisError(VisionError):
    """LLM 调用或响应解析失败

    建议：
    1. 检查 LLM API Key 是否有效
    2. 确认网络连接正常
    3. 检查模型名称配置是否正确
    4. 查看原始响应内容定位解析失败原因
    """

    error_code = "SKI503"

    def __init__(
        self,
        model: Optional[str] = None,
        raw_response: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ):
        self.model = model
        self.raw_response = raw_response
        msg = message or (
            "LLM 分析调用失败"
            + (f"，模型：{model}" if model else "")
            + "。建议：检查 API Key 和网络连接，确认模型名称配置正确。"
        )
        super().__init__(msg, **kwargs)

    def __str__(self) -> str:
        parts = ["[SKI503] LLMAnalysisError"]
        if self.model:
            parts.append(f"model={self.model}")
        if self.raw_response:
            preview = self.raw_response[:120].replace("\n", " ")
            parts.append(f"response_preview='{preview}'")
        parts.append("| 建议：检查 API Key、网络连接及模型名称配置。")
        return ": ".join([parts[0], ", ".join(parts[1:])])


class CoordinateError(VisionError):
    """坐标无效或超出屏幕范围

    建议：
    1. 确认坐标值为非负整数
    2. 检查屏幕分辨率与坐标是否匹配
    3. 在多显示器环境下确认目标屏幕
    """

    error_code = "SKI504"

    def __init__(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        screen_size: Optional[tuple] = None,
        message: Optional[str] = None,
        **kwargs,
    ):
        self.x = x
        self.y = y
        self.screen_size = screen_size
        coord_str = f"({x}, {y})" if x is not None and y is not None else "未知坐标"
        size_str = f"，屏幕尺寸：{screen_size}" if screen_size else ""
        msg = message or (
            f"无效坐标 {coord_str}{size_str}。"
            "建议：确认坐标为非负整数且未超出屏幕范围，多显示器环境请确认目标屏幕。"
        )
        super().__init__(msg, **kwargs)

    def __str__(self) -> str:
        coord = f"({self.x}, {self.y})" if self.x is not None else "unknown"
        size = f", screen={self.screen_size}" if self.screen_size else ""
        return (
            f"[SKI504] CoordinateError: coord={coord}{size}"
            " | 建议：确认坐标为非负整数且在屏幕范围内，多显示器请确认目标屏幕。"
        )


class VisionTimeoutError(VisionError):
    """视觉定位操作超时

    建议：
    1. 适当增加 timeout 参数值
    2. 确认目标页面加载完成后再触发定位
    3. 检查系统性能，避免 CPU/内存过载导致超时
    """

    error_code = "SKI505"

    def __init__(
        self,
        timeout: Optional[float] = None,
        target: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ):
        self.timeout = timeout
        self.target = target
        msg = message or (
            "视觉定位超时"
            + (f"，超时阈值：{timeout}s" if timeout is not None else "")
            + (f"，目标：'{target}'" if target else "")
            + "。建议：增大 timeout 参数，确认页面已完全加载。"
        )
        super().__init__(msg, **kwargs)

    def __str__(self) -> str:
        parts = ["[SKI505] VisionTimeoutError"]
        if self.timeout is not None:
            parts.append(f"timeout={self.timeout}s")
        if self.target:
            parts.append(f"target='{self.target}'")
        parts.append("| 建议：增大 timeout 参数，确认页面已完全加载，检查系统性能。")
        return ": ".join([parts[0], ", ".join(parts[1:])])
