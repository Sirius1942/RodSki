import pytest
import tempfile
import os
from pathlib import Path
from core.model_parser import ModelParser, VALID_LOCATOR_TYPES, VISION_LOCATOR_TYPES


@pytest.fixture
def model_parser():
    xml_path = Path(__file__).parent.parent / "examples" / "product" / "DEMO" / "demo_site" / "model" / "model.xml"
    return ModelParser(str(xml_path))


# === 常量测试 ===

def test_valid_locator_types():
    """测试定位器类型常量包含传统和视觉定位器"""
    # 传统定位器
    assert "id" in VALID_LOCATOR_TYPES
    assert "xpath" in VALID_LOCATOR_TYPES
    assert "css" in VALID_LOCATOR_TYPES
    # 视觉定位器
    assert "vision" in VALID_LOCATOR_TYPES
    assert "ocr" in VALID_LOCATOR_TYPES
    assert "vision_bbox" in VALID_LOCATOR_TYPES


def test_vision_locator_types():
    """测试视觉定位器类型集合"""
    assert "vision" in VISION_LOCATOR_TYPES
    assert "ocr" in VISION_LOCATOR_TYPES
    assert "vision_bbox" in VISION_LOCATOR_TYPES
    assert "id" not in VISION_LOCATOR_TYPES


def test_is_vision_locator():
    """测试视觉定位器判断方法"""
    assert ModelParser.is_vision_locator("vision") is True
    assert ModelParser.is_vision_locator("ocr") is True
    assert ModelParser.is_vision_locator("vision_bbox") is True
    assert ModelParser.is_vision_locator("id") is False
    assert ModelParser.is_vision_locator("xpath") is False


# === 向后兼容测试 ===

def test_get_element_with_id(model_parser):
    result = model_parser.get_element("Login.username")
    assert result['locator_type'] == 'id'
    assert result['locator_value'] == 'username'
    assert result['driver_type'] == 'web'


def test_get_element_with_xpath(model_parser):
    result = model_parser.get_element("HomePage.logoutBtn")
    assert result['locator_type'] == 'xpath'
    assert result['locator_value'] == "//a[text()='Logout']"


def test_get_model(model_parser):
    model = model_parser.get_model("Login")
    assert model is not None
    assert "username" in model
    assert "password" in model
    assert "loginBtn" in model


def test_get_model_driver_type(model_parser):
    assert model_parser.get_model_driver_type("Login") == "web"
    assert model_parser.get_model_driver_type("LoginAPI") == "interface"


def test_get_element_not_found(model_parser):
    result = model_parser.get_element("Login.NonExistent")
    assert result is None


def test_get_element_model_not_found(model_parser):
    result = model_parser.get_element("NonExistentPage.Element")
    assert result is None


def test_get_element_invalid_format(model_parser):
    result = model_parser.get_element("InvalidFormat")
    assert result is None


def test_interface_model(model_parser):
    model = model_parser.get_model("LoginAPI")
    assert model is not None
    assert "_method" in model
    assert "_url" in model
    assert "username" in model
    assert model["_method"]["driver_type"] == "interface"


# === locations 字段测试 ===

def test_get_element_returns_locations(model_parser):
    """测试 get_element 返回 locations 字段"""
    result = model_parser.get_element("Login.username")
    assert "locations" in result
    assert isinstance(result["locations"], list)
    assert len(result["locations"]) == 1
    assert result["locations"][0]["type"] == "id"
    assert result["locations"][0]["value"] == "username"
    assert result["locations"][0]["priority"] == 1


def test_get_locations_method(model_parser):
    """测试 get_locations 方法"""
    locations = model_parser.get_locations("Login.username")
    assert len(locations) == 1
    assert locations[0]["type"] == "id"
    assert locations[0]["priority"] == 1


def test_get_locations_not_found(model_parser):
    """测试 get_locations 元素不存在时返回空列表"""
    locations = model_parser.get_locations("NonExistent.Element")
    assert locations == []


# === 视觉定位器测试 ===

@pytest.fixture
def vision_model_parser():
    xml_path = Path(__file__).parent.parent.parent / "demo" / "DEMO" / "vision_web" / "model" / "model.xml"
    if xml_path.exists():
        return ModelParser(str(xml_path))
    return None


def test_vision_locator_parsing(vision_model_parser):
    """测试 vision 定位器解析"""
    if vision_model_parser is None:
        pytest.skip("vision_web model not found")
    result = vision_model_parser.get_element("SearchPage.searchInput")
    assert result["locator_type"] == "vision"
    assert result["locator_value"] == "搜索输入框"
    assert ModelParser.is_vision_locator(result["locator_type"])


def test_vision_bbox_locator_parsing():
    """测试 vision_bbox 定位器解析"""
    xml_path = Path(__file__).parent.parent.parent / "demo" / "DEMO" / "vision_desktop" / "model" / "model.xml"
    if not xml_path.exists():
        pytest.skip("vision_desktop model not found")
    parser = ModelParser(str(xml_path))
    result = parser.get_element("NotepadPage.menuFile")
    assert result["locator_type"] == "vision_bbox"
    assert result["locator_value"] == "0,0,50,25"
    assert ModelParser.is_vision_locator(result["locator_type"])


# === 多定位器测试 ===

MULTI_LOCATOR_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginPage">
    <element name="username" type="web">
      <type>input</type>
      <location type="id" priority="1">username</location>
      <location type="css" priority="2">input[name="username"]</location>
      <location type="ocr" priority="3">用户名</location>
    </element>
    <element name="loginBtn" type="web">
      <type>button</type>
      <location type="ocr" priority="1">登录</location>
      <location type="id" priority="2">loginBtn</location>
    </element>
  </model>
</models>'''


@pytest.fixture
def multi_locator_parser():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(MULTI_LOCATOR_XML)
        temp_path = f.name
    parser = ModelParser(temp_path)
    yield parser
    os.unlink(temp_path)


def test_multi_locator_parsing(multi_locator_parser):
    """测试多定位器解析"""
    result = multi_locator_parser.get_element("LoginPage.username")
    assert len(result["locations"]) == 3

    # 验证排序
    priorities = [loc["priority"] for loc in result["locations"]]
    assert priorities == [1, 2, 3]

    # 验证类型
    types = [loc["type"] for loc in result["locations"]]
    assert types == ["id", "css", "ocr"]


def test_multi_locator_priority_sorting(multi_locator_parser):
    """测试 priority 排序（非顺序定义）"""
    result = multi_locator_parser.get_element("LoginPage.loginBtn")
    priorities = [loc["priority"] for loc in result["locations"]]
    assert priorities == [1, 2], "定位器应按 priority 从小到大排序"

    # ocr 应该是第一个（priority=1）
    assert result["locations"][0]["type"] == "ocr"
    assert result["locations"][1]["type"] == "id"


def test_multi_locator_primary_locator(multi_locator_parser):
    """测试主定位器（第一个）"""
    result = multi_locator_parser.get_element("LoginPage.loginBtn")
    # 主定位器应该是 priority 最小的那个
    assert result["locator_type"] == "ocr"
    assert result["locator_value"] == "登录"


def test_multi_locator_with_vision_types(multi_locator_parser):
    """测试多定位器中包含视觉定位器类型"""
    result = multi_locator_parser.get_element("LoginPage.username")
    ocr_locator = next((loc for loc in result["locations"] if loc["type"] == "ocr"), None)
    assert ocr_locator is not None
    assert ocr_locator["value"] == "用户名"
    assert ModelParser.is_vision_locator("ocr")
