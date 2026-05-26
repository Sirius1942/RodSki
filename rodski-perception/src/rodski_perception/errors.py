"""rodski-perception 异常层级。"""

from __future__ import annotations


class PerceptionError(RuntimeError):
    """rodski-perception 抛出的所有异常基类。"""


class OllamaUnreachableError(PerceptionError):
    """ollama 服务不可达 / 网络错误。

    触发场景：
        - ``ollama serve`` 未启动
        - 网络断开 / 防火墙阻塞
        - 错误的 ``ollama_host`` 配置

    CLI 看到此异常应退出码 ``3``；rodski 侧将其转换为 ``PerceptionUnavailableError``。
    """


class ModelNotFoundError(PerceptionError):
    """请求的 VLM 模型未在 ollama 中安装。

    用户解决方法：``ollama pull qwen3-vl:2b``。CLI 看到此异常退出码 ``4``。
    """


class InvalidResponseError(PerceptionError):
    """ollama 返回了无法解析为 bbox 的响应。

    CLI 看到此异常退出码 ``1``，并把原始响应写入 stderr 供调试。
    """


__all__ = [
    "PerceptionError",
    "OllamaUnreachableError",
    "ModelNotFoundError",
    "InvalidResponseError",
]
