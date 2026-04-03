"""测试 LLM Providers"""
import pytest
from unittest.mock import MagicMock
from rodski.llm.providers import ClaudeProvider, OpenAIProvider


def test_claude_provider_init():
    """测试 Claude Provider 初始化"""
    config = {"model": "claude-opus-4-6", "timeout": 10}
    provider = ClaudeProvider(config, "test-key")
    assert provider.model == "claude-opus-4-6"
    assert provider.api_key == "test-key"


def test_openai_provider_init():
    """测试 OpenAI Provider 初始化"""
    config = {"model": "gpt-4o", "timeout": 10}
    provider = OpenAIProvider(config, "test-key")
    assert provider.model == "gpt-4o"

