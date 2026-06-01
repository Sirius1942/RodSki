"""视觉定位集成测试 - 端到端流程验证 (v7.1.0 重构后)

不依赖 pytest 的固有断言，使用 RodSki 自有测试框架。
所有外部调用（PerceptionBackend / pyautogui）均 mock。

v7.1.0 起：OmniClient 已删除，``vision`` 走 PerceptionRegistry +
backend；本集成测试通过 Registry.register 注入 stub backend 验证链路。
"""
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加 rodski 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from vision.locator import VisionLocator
from vision.cache import VisionCache
from vision.perception_interface import (
    PerceptionBackend,
    PerceptionResult,
    PerceptionUnavailableError,
)
from vision.registry import PerceptionRegistry


class _IntegrationStubBackend(PerceptionBackend):
    name = "local"
    capabilities = {"locate"}

    def __init__(self, **kwargs):
        pass

    def is_available(self):
        return True

    def locate(self, image_path, description, element_type=None):
        return PerceptionResult(
            bbox=(500, 600, 700, 800),
            coordinates=(600, 700),
            target_description=description,
            confidence=0.9,
        )


class TestVisionLocatorIntegration:
    """端到端：vision:描述 → PerceptionRegistry → backend → 坐标"""

    def test_vision_locator_with_stub_backend(self, tmp_path):
        """注入 stub backend → vision 定位返回 backend 给出的坐标。"""
        PerceptionRegistry.reset()
        PerceptionRegistry.register("local", _IntegrationStubBackend)
        try:
            png = tmp_path / "s.png"
            png.write_bytes(b"\x89PNG" + b"\x00" * 10)
            locator = VisionLocator()
            bbox = locator.locate("vision", "登录按钮", str(png))
            assert bbox == (500, 600, 700, 800)
        finally:
            PerceptionRegistry.reset()

    def test_vision_no_backend_raises(self, tmp_path):
        """无任何 backend → PerceptionUnavailableError，含安装指引。"""
        PerceptionRegistry.reset()
        png = tmp_path / "s.png"
        png.write_bytes(b"\x89PNG" + b"\x00" * 10)
        locator = VisionLocator()
        # mock discover 返回空，模拟未安装任何 perception backend 的环境
        with patch.object(PerceptionRegistry, "discover", return_value={}):
            try:
                locator.locate("vision", "登录按钮", str(png))
                assert False, "expected PerceptionUnavailableError"
            except PerceptionUnavailableError as exc:
                assert "pip install rodski[perception]" in str(exc)


class TestVisionBboxIntegration:
    """vision_bbox 坐标计算（无需任何 backend）"""

    def test_bbox_to_coords(self):
        locator = VisionLocator()
        cx, cy = locator.locate_legacy('vision_bbox:100,200,150,250')
        assert cx == 125
        assert cy == 225


class TestCacheIntegration:
    """缓存生效验证"""

    def test_cache_reduces_calls(self):
        cache = VisionCache(ttl=60)
        screenshot_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        cache.set(screenshot_bytes, {"elements": [{'bbox': [0.1, 0.2, 0.3, 0.4]}]})
        result = cache.get(screenshot_bytes)
        assert result is not None
        assert 'elements' in result
        assert len(result['elements']) == 1


class TestDesktopDriverIntegration:
    """桌面驱动集成"""

    def test_desktop_driver_launch(self):
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
