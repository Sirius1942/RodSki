"""Claude Provider"""
import json
import logging
from .base import BaseProvider
from ..exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseProvider):
    """Anthropic Claude Provider"""

    def __init__(self, config: dict, api_key: str):
        super().__init__(config)
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                import anthropic
                kwargs = {"api_key": self.api_key}
                if self.config.get("base_url"):
                    kwargs["base_url"] = self.config["base_url"]
                self._client = anthropic.Anthropic(**kwargs)
            except ImportError:
                raise LLMProviderError("anthropic library not installed")
        return self._client

    def call_vision(self, image_base64: str, prompt: str, **kwargs) -> str:
        """调用 Claude 多模态 API"""
        client = self._get_client()

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise LLMProviderError(f"Claude API error: {e}")
