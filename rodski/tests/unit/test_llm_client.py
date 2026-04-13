"""测试 LLM Client"""
import pytest
from unittest.mock import MagicMock, patch
from rodski.llm import LLMClient
from rodski.llm.exceptions import LLMConfigError


@patch('rodski.llm.client.resolve_api_key')
def test_client_init(mock_resolve):
    """测试客户端初始化"""
    mock_resolve.return_value = "test-key"
    client = LLMClient()
    assert client._config is not None


@patch('rodski.llm.client.resolve_api_key')
def test_get_capability(mock_resolve):
    """测试获取能力"""
    mock_resolve.return_value = "test-key"
    client = LLMClient()
    capability = client.get_capability('vision_locator')
    assert capability is not None


@patch('rodski.llm.client.resolve_api_key')
def test_get_unknown_capability(mock_resolve):
    """测试获取未知能力"""
    mock_resolve.return_value = "test-key"
    client = LLMClient()
    with pytest.raises(LLMConfigError):
        client.get_capability('unknown')


@patch('rodski.llm.client.resolve_api_key')
def test_client_call_text(mock_resolve):
    """测试客户端 call_text 代理到 provider"""
    mock_resolve.return_value = "test-key"
    client = LLMClient()

    mock_provider = MagicMock()
    mock_provider.call_text.return_value = "response text"
    client._provider = mock_provider

    result = client.call_text("hello")
    assert result == "response text"
    mock_provider.call_text.assert_called_once_with("hello")


@patch('rodski.llm.client.resolve_api_key')
def test_client_call_text_with_kwargs(mock_resolve):
    """测试客户端 call_text 传递 kwargs"""
    mock_resolve.return_value = "test-key"
    client = LLMClient()

    mock_provider = MagicMock()
    mock_provider.call_text.return_value = "response"
    client._provider = mock_provider

    result = client.call_text("hello", temperature=0.5, max_tokens=2048)
    assert result == "response"
    mock_provider.call_text.assert_called_once_with(
        "hello", temperature=0.5, max_tokens=2048
    )
