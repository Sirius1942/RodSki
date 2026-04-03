"""Provider 抽象基类"""
from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "")
        self.timeout = config.get("timeout", 10)
        self.max_tokens = config.get("max_tokens", 1024)

    @abstractmethod
    def call_vision(self, image_base64: str, prompt: str, **kwargs) -> str:
        """调用多模态 API

        Args:
            image_base64: Base64 编码的图片
            prompt: 提示词

        Returns:
            LLM 响应文本
        """
        pass
