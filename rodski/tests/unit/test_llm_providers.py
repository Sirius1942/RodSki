"""测试 LLM Providers"""
import pytest
from unittest.mock import MagicMock, patch
from rodski.llm.providers import ClaudeProvider, OpenAIProvider
from rodski.llm.exceptions import LLMProviderError


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


def test_claude_call_text():
    """测试 Claude Provider call_text"""
    config = {"model": "claude-opus-4-6", "timeout": 10, "max_tokens": 1024}
    provider = ClaudeProvider(config, "test-key")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="hello from claude")]
    mock_client.messages.create.return_value = mock_response
    provider._client = mock_client

    result = provider.call_text("say hello")
    assert result == "hello from claude"
    mock_client.messages.create.assert_called_once_with(
        model="claude-opus-4-6",
        max_tokens=1024,
        timeout=10,
        temperature=None,
        messages=[{"role": "user", "content": "say hello"}],
    )


def test_claude_call_text_with_kwargs():
    """测试 Claude Provider call_text 支持 kwargs 覆盖"""
    config = {"model": "claude-opus-4-6", "timeout": 10, "max_tokens": 1024}
    provider = ClaudeProvider(config, "test-key")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="response")]
    mock_client.messages.create.return_value = mock_response
    provider._client = mock_client

    result = provider.call_text("prompt", temperature=0.5, max_tokens=2048)
    assert result == "response"
    mock_client.messages.create.assert_called_once_with(
        model="claude-opus-4-6",
        max_tokens=2048,
        timeout=10,
        temperature=0.5,
        messages=[{"role": "user", "content": "prompt"}],
    )


def test_claude_call_text_error():
    """测试 Claude Provider call_text 异常处理"""
    config = {"model": "claude-opus-4-6", "timeout": 10, "max_tokens": 1024}
    provider = ClaudeProvider(config, "test-key")

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API error")
    provider._client = mock_client

    with pytest.raises(LLMProviderError, match="Claude API error"):
        provider.call_text("say hello")


def test_openai_call_text():
    """测试 OpenAI Provider call_text"""
    config = {"model": "gpt-4o", "timeout": 10, "max_tokens": 1024}
    provider = OpenAIProvider(config, "test-key")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="hello from openai"))]
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client

    result = provider.call_text("say hello")
    assert result == "hello from openai"
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        max_tokens=1024,
        timeout=10,
        temperature=None,
        messages=[{"role": "user", "content": "say hello"}],
    )


def test_openai_call_text_with_kwargs():
    """测试 OpenAI Provider call_text 支持 kwargs 覆盖"""
    config = {"model": "gpt-4o", "timeout": 10, "max_tokens": 1024}
    provider = OpenAIProvider(config, "test-key")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
    mock_client.chat.completions.create.return_value = mock_response
    provider._client = mock_client

    result = provider.call_text("prompt", temperature=0.7, max_tokens=4096)
    assert result == "response"
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        max_tokens=4096,
        timeout=10,
        temperature=0.7,
        messages=[{"role": "user", "content": "prompt"}],
    )


def test_openai_call_text_error():
    """测试 OpenAI Provider call_text 异常处理"""
    config = {"model": "gpt-4o", "timeout": 10, "max_tokens": 1024}
    provider = OpenAIProvider(config, "test-key")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API error")
    provider._client = mock_client

    with pytest.raises(LLMProviderError, match="OpenAI API error"):
        provider.call_text("say hello")

