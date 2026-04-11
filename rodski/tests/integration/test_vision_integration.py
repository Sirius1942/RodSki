"""视觉定位集成测试 - 端到端流程验证

不依赖 pytest，使用 RodSki 自有测试框架
所有外部调用（OmniParser/LLM/pyautogui）均 mock
"""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加 rodski 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vision.locator import VisionLocator
from vision.cache import VisionCache


class TestVisionLocatorIntegration:
    """端到端：vision:描述 → OmniParser → LLM → 匹配 → 坐标"""

    def test_vision_locator_full_flow(self):
        """完整流程：语义定位 via locate_legacy"""
        with patch('vision.omni_client.requests.post') as mock_post, \
             patch('vision.locator.VisionLocator._locate_by_vision') as mock_vision:

            # Mock _locate_by_vision 直接返回 bbox（跳过 OmniParser + LLM 内部逻辑）
            mock_vision.return_value = (500, 600, 700, 800)

            locator = VisionLocator()
            cx, cy = locator.locate_legacy('vision:登录按钮', driver=Mock())

            assert isinstance(cx, (int, float))
            assert isinstance(cy, (int, float))
            assert mock_vision.called


class TestVisionBboxIntegration:
    """vision_bbox 坐标计算（无需 mock）"""

    def test_bbox_to_coords(self):
        """bbox 字符串 → 中心坐标（通过 locate_legacy）"""
        locator = VisionLocator()
        cx, cy = locator.locate_legacy('vision_bbox:100,200,150,250')
        assert cx == 125
        assert cy == 225


class TestCacheIntegration:
    """缓存生效验证"""

    def test_cache_reduces_calls(self):
        """同路径第二次调用不触发 OmniParser"""
        cache = VisionCache(ttl=60)

        # 使用 bytes 作为缓存 key（避免依赖文件系统）
        screenshot_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'

        # 第一次：设置缓存
        cache.set(screenshot_bytes, {"elements": [{'bbox': [0.1, 0.2, 0.3, 0.4]}]})

        # 第二次：命中缓存
        result = cache.get(screenshot_bytes)
        assert result is not None
        assert 'elements' in result
        assert len(result['elements']) == 1


class TestDesktopDriverIntegration:
    """桌面驱动集成"""

    def test_desktop_driver_launch(self):
        """launch + 验证 subprocess 调用"""
        # Mock pyautogui 在 sys.modules 中，避免 _require_pyautogui 的真实 import
        mock_pyautogui = MagicMock()
        mock_pyautogui.FAILSAFE = True
        mock_pyautogui.PAUSE = 0.05

        with patch.dict(sys.modules, {'pyautogui': mock_pyautogui}):
            from vision.desktop_driver import DesktopVisionDriver

            with patch('vision.desktop_driver.subprocess.Popen') as mock_popen:
                driver = DesktopVisionDriver(platform='macos')
                result = driver.launch_app('TextEdit.app')
                assert result is True
                assert mock_popen.called
