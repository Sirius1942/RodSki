import pytest
import tempfile
import os
from pathlib import Path
from core.model_parser import (
    ModelParser,
    VALID_LOCATOR_TYPES,
    VISION_LOCATOR_TYPES,
    MODEL_TYPE_UI,
    MODEL_TYPE_INTERFACE,
)


@pytest.fixture
def model_parser():
    xml_path = Path(__file__).parent.parent / "examples" / "product" / "DEMO" / "demo_site" / "model" / "model.xml"
    return ModelParser(str(xml_path))


# === 常量测试 ===

def test_valid_locator_types():
    assert "id" in VALID_LOCATOR_TYPES
    assert "xpath" in VALID_LOCATOR_TYPES
    assert "css" in VALID_LOCATOR_TYPES
    assert "vision" in VALID_LOCATOR_TYPES
    assert "ocr" in VALID_LOCATOR_TYPES
    assert "vision_bbox" in VALID_LOCATOR_TYPES


def test_vision_locator_types():
    assert "vision" in VISION_LOCATOR_TYPES
    assert "ocr" in VISION_LOCATOR_TYPES
    assert "vision_bbox" in VISION_LOCATOR_TYPES
    assert "id" not in VISION_LOCATOR_TYPES


def test_is_vision_locator():
    assert ModelParser.is_vision_locator("vision") is True
    assert ModelParser.is_vision_locator("ocr") is True
    assert ModelParser.is_vision_locator("vision_bbox") is True
    assert ModelParser.is_vision_locator("id") is False
    assert ModelParser.is_vision_locator("xpath") is False


# === 解析测试 ===

def test_get_element_with_id(model_parser):
    result = model_parser.get_element("Login.username")
    assert result['locator_type'] == 'id'
    assert result['locator_value'] == 'username'
    assert result['model_type'] == MODEL_TYPE_UI
    assert result['element_type'] == 'input'


def test_get_element_with_xpath(model_parser):
    result = model_parser.get_element("HomePage.logoutBtn")
    assert result['locator_type'] == 'xpath'
    assert result['locator_value'] == "//a[text()='Logout']"
    assert result['element_type'] == 'link'


def test_get_model(model_parser):
    model = model_parser.get_model("Login")
    assert model is not None
    assert "username" in model
    assert "password" in model
    assert "loginBtn" in model
    assert model['__model_type__'] == MODEL_TYPE_UI


def test_get_model_type(model_parser):
    assert model_parser.get_model_type("Login") == MODEL_TYPE_UI
    assert model_parser.get_model_type("LoginAPI") == MODEL_TYPE_INTERFACE


def test_get_model_driver_type_desktop(tmp_path):
    xml = tmp_path / "model.xml"
    xml.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="DesktopPage" type="ui" driver_type="macos">
    <element name="textArea" type="input">
      <location type="vision_bbox">100,100,200,200</location>
    </element>
  </model>
</models>''', encoding='utf-8')
    parser = ModelParser(str(xml))
    assert parser.get_model_driver_type("DesktopPage") == "macos"


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
    assert model["_method"]["element_type"] == "http_method"
    assert model["username"]["model_type"] == MODEL_TYPE_INTERFACE


# === locations 字段测试 ===

def test_get_element_returns_locations(model_parser):
    result = model_parser.get_element("Login.username")
    assert "locations" in result
    assert isinstance(result["locations"], list)
    assert len(result["locations"]) == 1
    assert result["locations"][0]["type"] == "id"
    assert result["locations"][0]["value"] == "username"
    assert result["locations"][0]["priority"] == 1


def test_get_locations_method(model_parser):
    locations = model_parser.get_locations("Login.username")
    assert len(locations) == 1
    assert locations[0]["type"] == "id"
    assert locations[0]["priority"] == 1


def test_get_locations_not_found(model_parser):
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
    if vision_model_parser is None:
        pytest.skip("vision_web model not found")
    result = vision_model_parser.get_element("SearchPage.searchInput")
    assert result["locator_type"] == "vision"
    assert result["locator_value"] == "搜索输入框"
    assert ModelParser.is_vision_locator(result["locator_type"])


# === 多定位器测试 ===

MULTI_LOCATOR_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginPage" type="ui">
    <element name="username" type="input">
      <location type="id" priority="1">username</location>
      <location type="css" priority="2">input[name="username"]</location>
      <location type="ocr" priority="3">用户名</location>
    </element>
    <element name="loginBtn" type="button">
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
    result = multi_locator_parser.get_element("LoginPage.username")
    assert len(result["locations"]) == 3
    priorities = [loc["priority"] for loc in result["locations"]]
    assert priorities == [1, 2, 3]
    types = [loc["type"] for loc in result["locations"]]
    assert types == ["id", "css", "ocr"]


def test_multi_locator_priority_sorting(multi_locator_parser):
    result = multi_locator_parser.get_element("LoginPage.loginBtn")
    priorities = [loc["priority"] for loc in result["locations"]]
    assert priorities == [1, 2]
    assert result["locations"][0]["type"] == "ocr"
    assert result["locations"][1]["type"] == "id"


def test_multi_locator_primary_locator(multi_locator_parser):
    result = multi_locator_parser.get_element("LoginPage.loginBtn")
    assert result["locator_type"] == "ocr"
    assert result["locator_value"] == "登录"


def test_legacy_simplified_format_is_no_longer_supported(tmp_path):
    """旧版简化格式 type="id" value="xxx" 已移除，应返回 None。"""
    xml = tmp_path / "model.xml"
    xml.write_text(
        '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="Legacy">
    <element name="username" type="id" value="userName"/>
  </model>
</models>''',
        encoding='utf-8'
    )
    parser = ModelParser(str(xml))
    result = parser.get_element("Legacy.username")
    assert result is None


def test_locator_attribute_format_is_no_longer_supported(tmp_path):
    """旧版 locator="type:value" 属性格式已移除，应返回 None。"""
    xml = tmp_path / "model.xml"
    xml.write_text(
        '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="Legacy">
    <element name="searchBtn" locator="vision:搜索按钮"/>
  </model>
</models>''',
        encoding='utf-8'
    )
    parser = ModelParser(str(xml))
    result = parser.get_element("Legacy.searchBtn")
    assert result is None


def test_location_element_format_works(tmp_path):
    """唯一支持的格式：<location> 子元素。"""
    xml = tmp_path / "model.xml"
    xml.write_text(
        '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="TestPage">
    <element name="username">
      <location type="id">userName</location>
    </element>
  </model>
</models>''',
        encoding='utf-8'
    )
    parser = ModelParser(str(xml))
    result = parser.get_element("TestPage.username")
    assert result["locator_type"] == "id"
    assert result["locator_value"] == "userName"
    assert result["model_type"] == MODEL_TYPE_UI
