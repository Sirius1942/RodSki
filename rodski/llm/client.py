"""LLM 统一客户端"""
import logging
from typing import Optional
from .config import load_config, resolve_api_key
from .providers import ClaudeProvider, OpenAIProvider
from .exceptions import LLMConfigError

logger = logging.getLogger(__name__)


class LLMClient:
    """统一 LLM 客户端"""

    def __init__(self, config: dict = None, global_vars: dict = None):
        self._config = load_config(config, global_vars)
        self._provider = None
        self._capabilities = {}

    def _get_provider(self):
        """延迟初始化 provider"""
        if self._provider is None:
            provider_name = self._config.get("provider", "claude")
            provider_config = self._config["providers"].get(provider_name)

            if not provider_config:
                raise LLMConfigError(f"Provider '{provider_name}' not configured")

            api_key = resolve_api_key(provider_config)
            if not api_key:
                raise LLMConfigError(f"API key not found for provider '{provider_name}'")

            if provider_name == "claude":
                self._provider = ClaudeProvider(provider_config, api_key)
            elif provider_name == "openai":
                self._provider = OpenAIProvider(provider_config, api_key)
            else:
                raise LLMConfigError(f"Unknown provider: {provider_name}")

        return self._provider

    def get_capability(self, name: str):
        """获取能力实例（延迟加载）"""
        if name not in self._capabilities:
            if name == "vision_locator":
                from .capabilities import VisionLocatorCapability
                self._capabilities[name] = VisionLocatorCapability(self)
            elif name == "screenshot_verifier":
                from .capabilities.screenshot_verifier import ScreenshotVerifierCapability
                self._capabilities[name] = ScreenshotVerifierCapability(self)
            elif name == "test_reviewer":
                from .capabilities.test_reviewer import TestReviewerCapability
                self._capabilities[name] = TestReviewerCapability(self)
            else:
                raise LLMConfigError(f"Unknown capability: {name}")

        return self._capabilities[name]

    def call_text(self, prompt: str, **kwargs) -> str:
        """调用纯文本 LLM API"""
        provider = self._get_provider()
        return provider.call_text(prompt, **kwargs)

    def call_vision(self, image_base64: str, prompt: str, **kwargs) -> str:
        """调用多模态 API"""
        provider = self._get_provider()
        return provider.call_vision(image_base64, prompt, **kwargs)
