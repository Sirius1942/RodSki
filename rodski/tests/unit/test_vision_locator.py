"""视觉定位器集成层单元测试

覆盖:
  - VisionLocator.is_vision_locator
  - VisionLocator.locate: 新 API（vision/ocr/vision_bbox）
  - VisionLocator.locate_legacy: 旧 API 向后兼容
  - 异常路径：空字符串、未知前缀、无匹配、无效 bbox

全部外部调用（OmniClient、LLMAnalyzer、screenshot）通过 unittest.mock 隔离。
不依赖 pytest，使用 RodSki 自有测试基础设施（assert_raises / assert_raises_match）。
"""
from __future__ import annotations

import base64
import pathlib
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from rodski.core.test_runner import assert_raises, assert_raises_match
from rodski.vision.locator import VisionLocator
from rodski.vision.exceptions import InvalidBBoxError


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _tiny_png_bytes() -> bytes:
    """1×1 白色 PNG 字节串（最小合法 PNG）。"""
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )


def _make_tmp_png(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "screen.png"
    p.write_bytes(_tiny_png_bytes())
    return p


def _elements_with_labels(*labels: str) -> list[dict]:
    """构造已带 semantic_label 的元素列表（模拟 LLMAnalyzer 输出）。"""
    return [
        {
            "type": "text",
            "content": lbl,
            "semantic_label": lbl,
            "bbox": [0.1, 0.2, 0.3, 0.4],
            "interactivity": True,
        }
        for lbl in labels
    ]


# ═══════════════════════════════════════════════════════════════
# TestIsVisionLocator
# ═══════════════════════════════════════════════════════════════

class TestIsVisionLocator:
    """VisionLocator.is_vision_locator 各种输入。"""

    def setup_method(self):
        self.loc = VisionLocator(
            omni_client=MagicMock(),
            llm_analyzer=MagicMock(),
            matcher=MagicMock(),
        )

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

    def test_none_like_empty(self):
        assert self.loc.is_vision_locator("") is False

    def test_whitespace_vision(self):
        # 前导空格后仍以 vision: 开头
        assert self.loc.is_vision_locator("  vision:btn") is True


# ═══════════════════════════════════════════════════════════════
# TestLocateNewAPI - 新 API 测试
# ═══════════════════════════════════════════════════════════════

class TestLocateNewAPI:
    """新 API: locate(locator_type, locator_value, screenshot) -> (x1, y1, x2, y2)"""

    def setup_method(self):
        self.loc = VisionLocator(
            omni_client=MagicMock(),
            llm_analyzer=MagicMock(),
            matcher=MagicMock(),
        )

    def test_vision_bbox_returns_bbox(self):
        """vision_bbox 类型返回边界框坐标。"""
        bbox = self.loc.locate("vision_bbox", "100,200,300,400", None)
        assert bbox == (100, 200, 300, 400)

    def test_vision_bbox_with_spaces(self):
        """支持带空格的坐标字符串。"""
        bbox = self.loc.locate("vision_bbox", "100, 200, 300, 400", None)
        assert bbox == (100, 200, 300, 400)

    def test_invalid_locator_type_raises(self):
        """不支持的定位器类型抛出 ValueError。"""
        assert_raises(ValueError, self.loc.locate, "invalid", "value", None)

    def test_empty_locator_type_raises(self):
        """空的定位器类型抛出 ValueError。"""
        assert_raises(ValueError, self.loc.locate, "", "value", None)

    def test_empty_locator_value_raises(self):
        """空的定位器值抛出 ValueError。"""
        assert_raises(ValueError, self.loc.locate, "vision_bbox", "", None)

    def test_locator_type_case_insensitive(self):
        """定位器类型不区分大小写。"""
        bbox = self.loc.locate("VISION_BBOX", "100,200,300,400", None)
        assert bbox == (100, 200, 300, 400)


# ═══════════════════════════════════════════════════════════════
# TestLocateBbox - 旧 API 向后兼容
# ═══════════════════════════════════════════════════════════════

class TestLocateBbox:
    """vision_bbox 分支：无网络调用，直接计算中心坐标（旧 API）。"""

    def setup_method(self):
        self.loc = VisionLocator(
            omni_client=MagicMock(),
            llm_analyzer=MagicMock(),
            matcher=MagicMock(),
        )

    def test_center_calculation(self):
        cx, cy = self.loc.locate_legacy("vision_bbox:100,200,300,400")
        assert cx == 200
        assert cy == 300

    def test_small_bbox(self):
        cx, cy = self.loc.locate_legacy("vision_bbox:1850,50,1900,100")
        assert cx == 1875
        assert cy == 75

    def test_float_coords(self):
        cx, cy = self.loc.locate_legacy("vision_bbox:0,0,100,100")
        assert cx == 50
        assert cy == 50

    def test_invalid_bbox_raises(self):
        assert_raises(InvalidBBoxError, self.loc.locate_legacy, "vision_bbox:100,200,300")

    def test_non_numeric_raises(self):
        assert_raises(InvalidBBoxError, self.loc.locate_legacy, "vision_bbox:a,b,c,d")


# ═══════════════════════════════════════════════════════════════
# TestLocateVision — 全链路 mock
# ═══════════════════════════════════════════════════════════════

class TestLocateVision:
    """vision: 分支，OmniClient / LLMAnalyzer / screenshot 全部 mock。"""

    def _make_locator(self, elements: list[dict], tmp_png: pathlib.Path):
        """构造一个注入了 mock 组件的 VisionLocator。"""
        omni = MagicMock()
        omni.parse.return_value = elements

        analyzer = MagicMock()
        analyzer.analyze.return_value = elements  # passthrough

        matcher_real = None  # 使用真实 VisionMatcher 验证匹配逻辑
        from vision.matcher import VisionMatcher
        matcher_real = VisionMatcher()

        locator = VisionLocator(
            omni_client=omni,
            llm_analyzer=analyzer,
            matcher=matcher_real,
        )
        # patch 截图和图像尺寸
        locator._take_screenshot = MagicMock(return_value=str(tmp_png))
        locator._get_image_size = MagicMock(return_value=(1920, 1080))
        locator._cleanup_tmp = MagicMock()
        return locator

    def test_exact_match_returns_center(self, tmp_path):
        png = _make_tmp_png(tmp_path)
        elements = _elements_with_labels("登录按钮")
        loc = self._make_locator(elements, png)
        cx, cy = loc.locate_legacy("vision:登录按钮")
        # bbox=[0.1,0.2,0.3,0.4], size=1920x1080
        # x1=192,y1=216,x2=576,y2=432 -> cx=384, cy=324
        assert cx == 384
        assert cy == 324

    def test_substring_match(self, tmp_path):
        png = _make_tmp_png(tmp_path)
        elements = _elements_with_labels("用户登录按钮")
        loc = self._make_locator(elements, png)
        cx, cy = loc.locate_legacy("vision:登录")
        assert isinstance(cx, int)
        assert isinstance(cy, int)

    def test_no_match_raises_runtime_error(self, tmp_path):
        png = _make_tmp_png(tmp_path)
        elements = _elements_with_labels("关闭")
        loc = self._make_locator(elements, png)
        assert_raises(RuntimeError, loc.locate_legacy, "vision:确认支付按钮")

    def test_empty_elements_raises(self, tmp_path):
        png = _make_tmp_png(tmp_path)
        loc = self._make_locator([], png)
        assert_raises(RuntimeError, loc.locate_legacy, "vision:任意元素")

    def test_screenshot_called_with_driver(self, tmp_path):
        png = _make_tmp_png(tmp_path)
        elements = _elements_with_labels("Submit")
        loc = self._make_locator(elements, png)
        fake_driver = MagicMock()
        loc.locate_legacy("vision:Submit", driver=fake_driver)
        loc._take_screenshot.assert_called_once_with(fake_driver)

    def test_omni_parse_called_once(self, tmp_path):
        png = _make_tmp_png(tmp_path)
        elements = _elements_with_labels("登录")
        loc = self._make_locator(elements, png)
        loc.locate_legacy("vision:登录")
        loc._omni_client.parse.assert_called_once()

    def test_llm_analyze_called_once(self, tmp_path):
        png = _make_tmp_png(tmp_path)
        elements = _elements_with_labels("登录")
        loc = self._make_locator(elements, png)
        loc.locate_legacy("vision:登录")
        loc._llm_analyzer.analyze.assert_called_once()

    def test_cleanup_called_after_locate(self, tmp_path):
        png = _make_tmp_png(tmp_path)
        elements = _elements_with_labels("登录")
        loc = self._make_locator(elements, png)
        loc.locate_legacy("vision:登录")
        loc._cleanup_tmp.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# TestLocateEdgeCases
# ═══════════════════════════════════════════════════════════════

class TestLocateEdgeCases:
    """异常路径和边界条件。"""

    def setup_method(self):
        self.loc = VisionLocator(
            omni_client=MagicMock(),
            llm_analyzer=MagicMock(),
            matcher=MagicMock(),
        )

    def test_empty_locator_raises(self):
        assert_raises(ValueError, self.loc.locate_legacy, "")

    def test_unknown_prefix_raises(self):
        assert_raises(ValueError, self.loc.locate_legacy, "xpath://button")

    def test_vision_empty_description_raises(self):
        # "vision:" 后面空描述 → locate() 检查 locator_value 为空抛 ValueError
        self.loc._take_screenshot = MagicMock(return_value="/tmp/fake.png")
        assert_raises(ValueError, self.loc.locate_legacy, "vision:")

    def test_vision_whitespace_description_raises(self):
        # "vision:   " 空白描述 → locate() 检查 strip 后 locator_value 为空抛 ValueError
        self.loc._take_screenshot = MagicMock(return_value="/tmp/fake.png")
        assert_raises(ValueError, self.loc.locate_legacy, "vision:   ")


# ═══════════════════════════════════════════════════════════════
# TestVisionLocatorLazyInit
# ═══════════════════════════════════════════════════════════════

class TestVisionLocatorLazyInit:
    """验证组件延迟初始化逻辑。"""

    def test_omni_client_created_lazily(self):
        loc = VisionLocator()  # 不注入任何依赖
        assert loc._omni_client is None  # 尚未创建
        with patch("vision.locator.VisionLocator._get_omni_client") as m:
            m.return_value = MagicMock()
            # 仅验证属性为 None 直到首次调用
        assert loc._omni_client is None

    def test_external_injection_respected(self):
        mock_client = MagicMock()
        loc = VisionLocator(omni_client=mock_client)
        assert loc._get_omni_client() is mock_client

    def test_cache_param_stored(self):
        sentinel = object()
        loc = VisionLocator(cache=sentinel)
        assert loc._cache is sentinel

    def test_image_matcher_lazy_load(self):
        """ImageMatcher 延迟加载 — 模块尚未实现时抛出 ModuleNotFoundError。"""
        loc = VisionLocator()
        assert loc._image_matcher is None
        # image_matcher 模块不存在，访问属性时应抛出 ModuleNotFoundError
        with pytest.raises(ModuleNotFoundError):
            _ = loc.image_matcher

    def test_bbox_locator_lazy_load(self):
        """BBoxLocator 延迟加载。"""
        loc = VisionLocator()
        assert loc._bbox_locator is None
        _ = loc.bbox_locator
        assert loc._bbox_locator is not None

    def test_ocr_locator_lazy_load(self):
        """OCRLocator 延迟加载（需要 omni_client）。"""
        loc = VisionLocator()
        assert loc._ocr_locator is None
        # 注意：访问 ocr_locator 会触发 omni_client 创建
        _ = loc.ocr_locator
        assert loc._ocr_locator is not None

