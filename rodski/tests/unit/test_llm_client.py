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
