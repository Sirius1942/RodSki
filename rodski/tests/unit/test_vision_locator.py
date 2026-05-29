"""VisionLocator 单元测试（v7.1.0 重构后）

覆盖:
  - VisionLocator.is_vision_locator（legacy）
  - VisionLocator.locate: 新 API (vision/vision_image/ocr/vision_bbox)
  - VisionLocator.locate_legacy: 旧 API 向后兼容
  - PerceptionUnavailableError 在 vision 定位无 backend 时抛出
  - 注入 stub backend 后 vision 定位走 PerceptionRegistry

v7.1.0 起 OmniClient 已删除，原 ``test_image_matcher_lazy_load``
（断言 ``ImageMatcher`` ImportError）一并清理；``image_matcher``
属性现在解析为 ``ImageTemplateMatcher``，应当能正常加载。
"""
from __future__ import annotations

import base64
import pathlib
import pytest
from unittest.mock import MagicMock, patch

from rodski.core.test_runner import assert_raises
from rodski.vision.locator import VisionLocator
from rodski.vision.exceptions import InvalidBBoxError
from rodski.vision.perception_interface import (
    PerceptionBackend,
    PerceptionResult,
    PerceptionUnavailableError,
)
from rodski.vision.registry import PerceptionRegistry


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _tiny_png_bytes() -> bytes:
    """1×1 白色 PNG 字节串。"""
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )


def _make_tmp_png(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "screen.png"
    p.write_bytes(_tiny_png_bytes())
    return p


class _StubBackend(PerceptionBackend):
    """测试用 PerceptionBackend：返回固定 bbox 或可控失败。"""

    name = "stub"
    capabilities = {"locate"}

    def __init__(self, bbox=(100, 100, 200, 200), available=True, **kwargs):
        self._bbox = bbox
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def locate(self, image_path, description, element_type=None):
        if self._bbox is None:
            return None
        x1, y1, x2, y2 = self._bbox
        return PerceptionResult(
            bbox=self._bbox,
            coordinates=((x1 + x2) // 2, (y1 + y2) // 2),
            target_description=description,
            confidence=0.9,
        )


@pytest.fixture(autouse=True)
def _clean_registry():
    """每个测试前后重置 Registry 缓存，避免互相干扰。"""
    PerceptionRegistry.reset()
    yield
    PerceptionRegistry.reset()


# ═══════════════════════════════════════════════════════════════
# TestIsVisionLocator
# ═══════════════════════════════════════════════════════════════

class TestIsVisionLocator:

    def setup_method(self):
        self.loc = VisionLocator()

    def test_vision_prefix(self):
        assert self.loc.is_vision_locator("vision:登录按钮") is True

    def test_ocr_prefix(self):
        assert self.loc.is_vision_locator("ocr:登录") is True

    def test_vision_bbox_prefix(self):
        assert self.loc.is_vision_locator("vision_bbox:100,200,300,400") is True

    def test_xpath_not_vision(self):
        assert self.loc.is_vision_locator("//button[@id='login']") is False

    def test_empty_string(self):
        assert self.loc.is_vision_locator("") is False

    def test_whitespace_vision(self):
        assert self.loc.is_vision_locator("  vision:btn") is True


# ═══════════════════════════════════════════════════════════════
# TestLocateNewAPI
# ═══════════════════════════════════════════════════════════════

class TestLocateNewAPI:

    def setup_method(self):
        self.loc = VisionLocator()

    def test_vision_bbox_returns_bbox(self):
        bbox = self.loc.locate("vision_bbox", "100,200,300,400", None)
        assert bbox == (100, 200, 300, 400)

    def test_vision_bbox_with_spaces(self):
        bbox = self.loc.locate("vision_bbox", "100, 200, 300, 400", None)
        assert bbox == (100, 200, 300, 400)

    def test_invalid_locator_type_raises(self):
        assert_raises(ValueError, self.loc.locate, "invalid", "value", None)

    def test_empty_locator_type_raises(self):
        assert_raises(ValueError, self.loc.locate, "", "value", None)

    def test_empty_locator_value_raises(self):
        assert_raises(ValueError, self.loc.locate, "vision_bbox", "", None)

    def test_locator_type_case_insensitive(self):
        bbox = self.loc.locate("VISION_BBOX", "100,200,300,400", None)
        assert bbox == (100, 200, 300, 400)


# ═══════════════════════════════════════════════════════════════
# TestLocateBbox - legacy
# ═══════════════════════════════════════════════════════════════

class TestLocateBbox:

    def setup_method(self):
        self.loc = VisionLocator()

    def test_center_calculation(self):
        cx, cy = self.loc.locate_legacy("vision_bbox:100,200,300,400")
        assert cx == 200
        assert cy == 300

    def test_invalid_bbox_raises(self):
        assert_raises(InvalidBBoxError, self.loc.locate_legacy, "vision_bbox:100,200,300")

    def test_non_numeric_raises(self):
        assert_raises(InvalidBBoxError, self.loc.locate_legacy, "vision_bbox:a,b,c,d")


# ═══════════════════════════════════════════════════════════════
# TestVisionViaBackend — vision 走 PerceptionRegistry
# ═══════════════════════════════════════════════════════════════

class TestVisionViaBackend:
    """``locate('vision', ...)`` 通过 PerceptionRegistry 取 backend。"""

    def test_vision_no_backend_raises_unavailable(self, tmp_path, monkeypatch):
        """未注册任何 backend → PerceptionUnavailableError，含安装指引。"""
        def _no_backend(cls, config=None):
            raise PerceptionUnavailableError()

        monkeypatch.setattr(
            PerceptionRegistry, "get_backend", classmethod(_no_backend)
        )
        png = _make_tmp_png(tmp_path)
        loc = VisionLocator()
        with pytest.raises(PerceptionUnavailableError) as exc_info:
            loc.locate("vision", "登录按钮", str(png))
        msg = str(exc_info.value)
        assert "pip install rodski[perception]" in msg
        assert "ollama pull" in msg

    def test_vision_with_stub_backend(self, tmp_path):
        """注册 stub backend 后，vision 定位通过它。"""
        png = _make_tmp_png(tmp_path)
        PerceptionRegistry.register("local", _StubBackend)
        loc = VisionLocator()
        bbox = loc.locate("vision", "登录按钮", str(png))
        assert bbox == (100, 100, 200, 200)

    def test_vision_backend_returns_none(self, tmp_path):
        """backend 未找到目标 → 返回 None（不抛错）。"""
        png = _make_tmp_png(tmp_path)

        class _MissBackend(_StubBackend):
            def locate(self, image_path, description, element_type=None):
                return None

        PerceptionRegistry.register("local", _MissBackend)
        loc = VisionLocator()
        assert loc.locate("vision", "不存在", str(png)) is None


# ═══════════════════════════════════════════════════════════════
# TestVisionImageLocator
# ═══════════════════════════════════════════════════════════════

class TestVisionImageLocator:
    """``vision_image`` 通过 VisionLocator 走 ImageTemplateMatcher。"""

    def test_vision_image_property_resolves(self):
        """``image_matcher`` 属性现在解析为 ImageTemplateMatcher（54a 收尾）。"""
        from rodski.vision.image_matcher import ImageTemplateMatcher
        loc = VisionLocator()
        assert isinstance(loc.image_matcher, ImageTemplateMatcher)


# ═══════════════════════════════════════════════════════════════
# TestLocateEdgeCases
# ═══════════════════════════════════════════════════════════════

class TestLocateEdgeCases:

    def setup_method(self):
        self.loc = VisionLocator()

    def test_empty_locator_raises(self):
        assert_raises(ValueError, self.loc.locate_legacy, "")

    def test_unknown_prefix_raises(self):
        assert_raises(ValueError, self.loc.locate_legacy, "xpath://button")


# ═══════════════════════════════════════════════════════════════
# TestVisionLocatorLazyInit
# ═══════════════════════════════════════════════════════════════

class TestVisionLocatorLazyInit:
    """组件延迟初始化。"""

    def test_external_ocr_provider_respected(self):
        mock = MagicMock()
        loc = VisionLocator(ocr_provider=mock)
        assert loc._ocr_provider is mock
        assert loc.ocr_locator._provider is mock

    def test_cache_param_stored(self):
        sentinel = object()
        loc = VisionLocator(cache=sentinel)
        assert loc._cache is sentinel

    def test_image_matcher_lazy_load(self):
        """ImageTemplateMatcher 延迟加载（54b 修复了 54a 留下的 stale 引用）。"""
        from rodski.vision.image_matcher import ImageTemplateMatcher
        loc = VisionLocator()
        assert loc._image_matcher is None
        m = loc.image_matcher
        assert isinstance(m, ImageTemplateMatcher)
        assert loc._image_matcher is m  # 缓存复用

    def test_bbox_locator_lazy_load(self):
        loc = VisionLocator()
        assert loc._bbox_locator is None
        _ = loc.bbox_locator
        assert loc._bbox_locator is not None

    def test_ocr_locator_lazy_load_without_provider(self, tmp_path):
        """无 provider 时 ocr_locator 也能创建（实际调用 locate_text 才报错）。"""
        loc = VisionLocator()
        assert loc._ocr_locator is None
        ocr = loc.ocr_locator
        assert ocr is not None
        # 真正调用时报清晰错误（v7.1.0 OCR provider 缺失契约）
        png = _make_tmp_png(tmp_path)
        with pytest.raises(RuntimeError, match="OCR provider 未配置"):
            ocr.locate_text("x", str(png))

    def test_omni_client_kwarg_deprecated(self):
        """v7.1.0 传 omni_client= 应当发 DeprecationWarning。"""
        with pytest.warns(DeprecationWarning, match="omni_client"):
            VisionLocator(omni_client=MagicMock())
