"""测试图片 base64 转换功能"""
import pytest
from pathlib import Path
from rodski.utils.image_utils import image_to_base64, convert_img_to_base64


def test_image_to_base64_success(tmp_path):
    """测试图片转 base64 成功"""
    # 创建一个简单的 1x1 PNG 图片
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

    img_path = tmp_path / "test.png"
    img_path.write_bytes(png_data)

    result = image_to_base64(str(img_path))
    assert result is not None
    assert result.startswith("data:image/png;base64,")


def test_image_to_base64_not_found():
    """测试图片不存在"""
    result = image_to_base64("/nonexistent/image.png")
    assert result is None


def test_convert_img_to_base64(tmp_path):
    """测试 HTML 中图片转换"""
    # 创建测试图片
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    img_path = tmp_path / "test.png"
    img_path.write_bytes(png_data)

    # HTML 包含相对路径图片
    html = f'<img src="test.png" alt="test">'
    result = convert_img_to_base64(html, str(tmp_path))

    assert "data:image/png;base64," in result
    assert "test.png" not in result  # 原路径应被替换


def test_convert_img_skips_data_uri():
    """测试跳过已经是 data URI 的图片"""
    html = '<img src="data:image/png;base64,iVBORw0KG...">'
    result = convert_img_to_base64(html)
    assert result == html  # 不变


def test_convert_img_skips_http_url():
    """测试跳过 HTTP URL"""
    html = '<img src="http://example.com/image.png">'
    result = convert_img_to_base64(html)
    assert result == html  # 不变
