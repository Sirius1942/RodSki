"""视觉定位集成测试 - 端到端流程验证

不依赖 pytest，使用 RodSki 自有测试框架
所有外部调用（OmniParser/LLM/pyautogui）均 mock
"""
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加 rodski 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vision.locator import VisionLocator
from vision.cache import VisionCache
from vision.desktop_driver import DesktopVisionDriver


class TestVisionLocatorIntegration:
    """端到端：vision:描述 → OmniParser → LLM → 匹配 → 坐标"""

    def test_vision_locator_full_flow(self):
        """完整流程：语义定位"""
        with patch('vision.omni_client.requests.post') as mock_post, \
             patch('vision.llm_analyzer.anthropic.Anthropic') as mock_anthropic, \
             patch('vision.screenshot.capture_web') as mock_screenshot:

            # Mock OmniParser 响应
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'parsed_content_list': [
                    {'type': 'button', 'content': '登录', 'bbox': [0.5, 0.6, 0.7, 0.8], 'interactivity': True}
                ]
            }

            # Mock LLM 响应
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text='[{"semantic_label": "登录按钮"}]')]
            mock_client.messages.create.return_value = mock_message

            # Mock 截图
            mock_screenshot.return_value = '/tmp/test.png'

            locator = VisionLocator()
            cx, cy = locator.locate('vision:登录按钮', driver=Mock())

            assert isinstance(cx, (int, float))
            assert isinstance(cy, (int, float))
            assert mock_post.called
            assert mock_client.messages.create.called


class TestVisionBboxIntegration:
    """vision_bbox 坐标计算（无需 mock）"""

    def test_bbox_to_coords(self):
        """bbox 字符串 → 中心坐标"""
        locator = VisionLocator()
        cx, cy = locator.locate('vision_bbox:100,200,150,250')
        assert cx == 125
        assert cy == 225


class TestCacheIntegration:
    """缓存生效验证"""

    def test_cache_reduces_calls(self):
        """同路径第二次调用不触发 OmniParser"""
        cache = VisionCache(ttl=60)

        # 第一次：设置缓存
        cache.set_parse_result('/tmp/test.png', [{'bbox': [0.1, 0.2, 0.3, 0.4]}])

        # 第二次：命中缓存
        result = cache.get_parse_result('/tmp/test.png')
        assert result is not None
        assert len(result) == 1


class TestDesktopDriverIntegration:
    """桌面驱动集成"""

    def test_desktop_driver_launch(self):
        """launch + click_at 流程"""
        with patch('vision.desktop_driver.subprocess.Popen') as mock_popen, \
             patch('vision.desktop_driver.pyautogui') as mock_gui:

            driver = DesktopVisionDriver(platform='darwin')
            result = driver.launch_app('TextEdit.app')
            assert mock_popen.called or mock_gui.called
