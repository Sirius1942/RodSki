"""OCRLocator 单元测试 (v7.1.0 重构后)

测试 vision/ocr_locator.py 中的 OCR 文字定位器。

v7.1.0 起 OCRLocator 不再依赖 OmniClient，改为接受任意实现
``parse(screenshot, box_threshold, iou_threshold)`` 的 provider；
未注入 provider 时调用 ``locate_text`` 会抛清晰的 ``RuntimeError``。

覆盖：
  - 注入 mock provider 后的 locate_text / locate_all_text / get_all_text_elements
  - _prepare_screenshot 各种输入
  - _text_matches 静态方法
  - 未注入 provider 时调用应抛 RuntimeError 指引升级
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from vision.ocr_locator import OCRLocator


@pytest.fixture
def mock_ocr_provider():
    """创建 mock OCR provider，返回预设的文字元素列表"""
    provider = MagicMock()
    provider.parse.return_value = [
        {"type": "text", "content": "用户名", "bbox": [0.1, 0.2, 0.3, 0.25], "confidence": 0.95},
        {"type": "text", "content": "密码", "bbox": [0.1, 0.3, 0.3, 0.35], "confidence": 0.92},
        {"type": "text", "content": "登录按钮", "bbox": [0.4, 0.5, 0.6, 0.55], "confidence": 0.98},
        {"type": "icon", "content": "logo", "bbox": [0.0, 0.0, 0.1, 0.1]},  # 非 text 类型
    ]
    return provider


@pytest.fixture
def locator(mock_ocr_provider):
    """创建 OCRLocator 实例（注入 mock provider）"""
    return OCRLocator(provider=mock_ocr_provider)


@pytest.fixture
def screenshot_file(tmp_path):
    """创建一个临时截图文件"""
    f = tmp_path / "screenshot.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # minimal PNG header
    return str(f)


# =====================================================================
# _text_matches 静态方法
# =====================================================================
class TestTextMatches:
    """_text_matches —— 文本匹配逻辑"""

    def test_exact_match_true(self):
        """精确匹配：完全相等时返回 True"""
        assert OCRLocator._text_matches("登录", "登录", exact=True) is True

    def test_exact_match_false(self):
        """精确匹配：不完全相等时返回 False"""
        assert OCRLocator._text_matches("登录", "登录按钮", exact=True) is False

    def test_fuzzy_match_contains(self):
        """模糊匹配：目标文字包含在内容中"""
        assert OCRLocator._text_matches("登录", "登录按钮", exact=False) is True

    def test_fuzzy_match_not_found(self):
        """模糊匹配：目标文字不在内容中"""
        assert OCRLocator._text_matches("注册", "登录按钮", exact=False) is False

    def test_empty_target(self):
        """空目标：空字符串应匹配所有内容（模糊）"""
        assert OCRLocator._text_matches("", "任意内容", exact=False) is True

    def test_empty_content(self):
        """空内容：非空目标不匹配空内容"""
        assert OCRLocator._text_matches("登录", "", exact=False) is False


# =====================================================================
# locate_text
# =====================================================================
class TestLocateText:
    """locate_text —— 定位单个文字"""

    @patch.object(OCRLocator, '_get_image_size', return_value=(1920, 1080))
    def test_locate_found_fuzzy(self, mock_size, locator, screenshot_file):
        """模糊匹配找到文字时返回 bbox（像素坐标）"""
        bbox = locator.locate_text("登录", screenshot_file, exact=False)
        # "登录按钮" 包含 "登录"，应匹配第 3 个元素
        assert bbox is not None
        # bbox 应为 (x1, y1, x2, y2) 整数坐标
        assert len(bbox) == 4
        assert all(isinstance(v, int) for v in bbox)

    @patch.object(OCRLocator, '_get_image_size', return_value=(1920, 1080))
    def test_locate_found_exact(self, mock_size, locator, screenshot_file):
        """精确匹配找到文字"""
        bbox = locator.locate_text("用户名", screenshot_file, exact=True)
        assert bbox is not None

    @patch.object(OCRLocator, '_get_image_size', return_value=(1920, 1080))
    def test_locate_not_found(self, mock_size, locator, screenshot_file):
        """文字不存在时返回 None"""
        bbox = locator.locate_text("不存在的文字", screenshot_file, exact=True)
        assert bbox is None

    def test_locate_file_not_found(self, locator):
        """截图文件不存在时应抛 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            locator.locate_text("test", "/nonexistent/path.png")


# =====================================================================
# locate_all_text
# =====================================================================
class TestLocateAllText:
    """locate_all_text —— 定位所有匹配文字"""

    @patch.object(OCRLocator, '_get_image_size', return_value=(1920, 1080))
    def test_locate_all_multiple_matches(self, mock_size, mock_ocr_provider, screenshot_file):
        """多个元素匹配时返回所有 bbox"""
        # 设置两个包含 "名" 的元素
        mock_ocr_provider.parse.return_value = [
            {"type": "text", "content": "用户名", "bbox": [0.1, 0.2, 0.3, 0.25]},
            {"type": "text", "content": "文件名", "bbox": [0.5, 0.6, 0.7, 0.65]},
            {"type": "text", "content": "密码", "bbox": [0.1, 0.3, 0.3, 0.35]},
        ]
        locator = OCRLocator(provider=mock_ocr_provider)
        bboxes = locator.locate_all_text("名", screenshot_file)
        # "用户名" 和 "文件名" 都包含 "名"
        assert len(bboxes) == 2

    @patch.object(OCRLocator, '_get_image_size', return_value=(1920, 1080))
    def test_locate_all_no_match(self, mock_size, locator, screenshot_file):
        """无匹配时返回空列表"""
        bboxes = locator.locate_all_text("不存在", screenshot_file)
        assert bboxes == []


# =====================================================================
# get_all_text_elements
# =====================================================================
class TestGetAllTextElements:
    """get_all_text_elements —— 获取所有文字元素"""

    @patch.object(OCRLocator, '_get_image_size', return_value=(1920, 1080))
    def test_filters_text_type_only(self, mock_size, locator, screenshot_file):
        """应仅返回 type='text' 的元素，过滤掉 icon 等"""
        elements = locator.get_all_text_elements(screenshot_file)
        # 原始数据有 3 个 text + 1 个 icon，应返回 3 个
        assert len(elements) == 3
        assert all(e["type"] == "text" for e in elements)

    @patch.object(OCRLocator, '_get_image_size', return_value=(1920, 1080))
    def test_coordinates_converted_to_pixels(self, mock_size, locator, screenshot_file):
        """归一化坐标应被转换为像素坐标"""
        elements = locator.get_all_text_elements(screenshot_file)
        # 第一个元素：bbox=[0.1, 0.2, 0.3, 0.25] → (192, 216, 576, 270) on 1920x1080
        first = elements[0]
        assert first["bbox"][0] == int(0.1 * 1920)   # x1 = 192
        assert first["bbox"][1] == int(0.2 * 1080)   # y1 = 216

    @patch.object(OCRLocator, '_get_image_size', return_value=(1920, 1080))
    def test_element_structure(self, mock_size, locator, screenshot_file):
        """每个元素应包含 content, bbox, type, confidence 字段"""
        elements = locator.get_all_text_elements(screenshot_file)
        for elem in elements:
            assert "content" in elem
            assert "bbox" in elem
            assert "type" in elem
            assert len(elem["bbox"]) == 4


# =====================================================================
# _prepare_screenshot
# =====================================================================
class TestPrepareScreenshot:
    """_prepare_screenshot —— 截图输入格式处理"""

    def test_path_string(self, locator, screenshot_file):
        """字符串路径应直接返回"""
        path, cleanup = locator._prepare_screenshot(screenshot_file)
        assert path == screenshot_file
        assert cleanup is False  # 不需要清理

    def test_path_object(self, locator, tmp_path):
        """pathlib.Path 对象应转为字符串"""
        f = tmp_path / "test.png"
        f.write_bytes(b"\x89PNG" + b"\x00" * 10)
        path, cleanup = locator._prepare_screenshot(f)
        assert path == str(f)
        assert cleanup is False

    def test_bytes_input(self, locator):
        """bytes 输入应保存到临时文件"""
        path, cleanup = locator._prepare_screenshot(b"\x89PNG" + b"\x00" * 50)
        assert Path(path).exists()
        assert cleanup is True  # 需要清理临时文件
        # 清理
        Path(path).unlink()

    def test_invalid_type_raises(self, locator):
        """不支持的类型应抛 TypeError"""
        with pytest.raises(TypeError, match="Unsupported screenshot type"):
            locator._prepare_screenshot(12345)

    def test_nonexistent_file_raises(self, locator):
        """不存在的文件路径应抛 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            locator._prepare_screenshot("/nonexistent/file.png")


# =====================================================================
# 初始化参数
# =====================================================================
class TestOCRLocatorInit:
    """OCRLocator 初始化参数"""

    def test_default_thresholds(self):
        """默认阈值应为 box=0.18, iou=0.7"""
        provider = MagicMock()
        locator = OCRLocator(provider=provider)
        assert locator._box_threshold == 0.18
        assert locator._iou_threshold == 0.7

    def test_custom_thresholds(self):
        """自定义阈值"""
        provider = MagicMock()
        locator = OCRLocator(provider=provider, box_threshold=0.3, iou_threshold=0.5)
        assert locator._box_threshold == 0.3
        assert locator._iou_threshold == 0.5

    def test_omni_client_kwarg_back_compat(self):
        """旧的 ``omni_client=`` 形参向后兼容（v7.1.0 起 deprecated）。"""
        provider = MagicMock()
        locator = OCRLocator(omni_client=provider)
        assert locator._provider is provider

    def test_missing_provider_raises_on_call(self, tmp_path):
        """未注入 provider → 调用 locate_text 报清晰 RuntimeError。"""
        png = tmp_path / "s.png"
        png.write_bytes(b"\x89PNG" + b"\x00" * 10)
        locator = OCRLocator()  # 完全无 provider
        with pytest.raises(RuntimeError, match="OCR provider 未配置"):
            locator.locate_text("x", str(png))
