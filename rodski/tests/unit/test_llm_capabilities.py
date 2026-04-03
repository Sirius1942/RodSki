"""测试 LLM Capabilities"""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from rodski.llm.capabilities import VisionLocatorCapability


def test_vision_locator_execute():
    """测试 Vision Locator 执行"""
    mock_client = MagicMock()
    mock_client.call_vision.return_value = '[{"index": 0, "semantic_label": "登录按钮"}]'

    capability = VisionLocatorCapability(mock_client)
    elements = [{"content": "登录", "type": "text"}]

    with patch('builtins.open', mock_open(read_data=b'fake_image')):
        result = capability.execute("test.png", elements)

    assert len(result) == 1
    assert result[0].get("semantic_label") == "登录按钮"


def test_vision_locator_error_handling():
    """测试错误处理"""
    mock_client = MagicMock()
    mock_client.call_vision.side_effect = Exception("API error")

    capability = VisionLocatorCapability(mock_client)
    elements = [{"content": "test"}]

    with patch('builtins.open', mock_open(read_data=b'fake')):
        result = capability.execute("test.png", elements)

    # 降级：返回原始元素
    assert result == elements
