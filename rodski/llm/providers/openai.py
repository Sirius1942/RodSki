"""OpenAI Provider（支持 OpenAI 和 Qwen）"""
import logging
from .base import BaseProvider
from ..exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI/Qwen Provider"""

    def __init__(self, config: dict, api_key: str):
        super().__init__(config)
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                import openai
                kwargs = {"api_key": self.api_key}
                if self.config.get("base_url"):
                    kwargs["base_url"] = self.config["base_url"]
                self._client = openai.OpenAI(**kwargs)
            except ImportError:
                raise LLMProviderError("openai library not installed")
        return self._client

    def call_text(self, prompt: str, **kwargs) -> str:
        """调用 OpenAI 纯文本 API"""
        client = self._get_client()

        try:
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                timeout=self.timeout,
                temperature=kwargs.get("temperature"),
                messages=[{
                    "role": "user",
                    "content": prompt,
                }],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise LLMProviderError(f"OpenAI API error: {e}")

    def call_vision(self, image_base64: str, prompt: str, **kwargs) -> str:
        """调用 OpenAI 多模态 API"""
        client = self._get_client()

        try:
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                        },
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise LLMProviderError(f"OpenAI API error: {e}")
