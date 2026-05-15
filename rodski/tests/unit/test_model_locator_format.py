"""模型定位器格式验证测试 (T41-004)

验证 model.xsd 和 ModelParser 拒绝旧版 value/locator 属性格式，
仅接受 <location type="...">value</location> 子元素格式。

参考：CORE_DESIGN_CONSTRAINTS.md 2.5.3
"""
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path

from core.exceptions import ModelParseError, XmlSchemaValidationError
from core.xml_schema_validator import RodskiXmlValidator
from core.model_parser import ModelParser
from core.test_runner import assert_raises


class TestModelXsdRejectsOldFormat:
    """model.xsd 应拒绝旧版定位器格式"""

    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_xsd_rejects_element_with_value_attribute(self, tmp_path):
        """element 使用 value 属性应被 XSD 拒绝"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="Login" type="ui">\n'
            '    <element name="username" type="id" value="uname"/>\n'
            '  </model>\n'
            '</models>',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_MODEL,
        )

    def test_xsd_rejects_element_with_locator_attribute(self, tmp_path):
        """element 使用 locator 属性应被 XSD 拒绝"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="Login" type="ui">\n'
            '    <element name="username" locator="id=uname">\n'
            '      <location type="id">uname</location>\n'
            '    </element>\n'
            '  </model>\n'
            '</models>',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_MODEL,
        )

    def test_xsd_accepts_proper_location_child(self, tmp_path):
        """element 使用 <location> 子元素应通过 XSD 验证"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="Login" type="ui">\n'
            '    <element name="username">\n'
            '      <location type="id">usernameInput</location>\n'
            '    </element>\n'
            '    <element name="password">\n'
            '      <location type="css" priority="1">#pwd</location>\n'
            '      <location type="xpath" priority="2">//input[@name="pwd"]</location>\n'
            '    </element>\n'
            '  </model>\n'
            '</models>',
            encoding="utf-8",
        )
        # 不应抛出异常
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_MODEL)

    def test_xsd_accepts_interface_model_with_location(self, tmp_path):
        """接口模型使用 <location type="static/field"> 应通过验证"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="LoginAPI" type="interface">\n'
            '    <element name="_method">\n'
            '      <location type="static">POST</location>\n'
            '    </element>\n'
            '    <element name="_url">\n'
            '      <location type="static">http://api.example.com/login</location>\n'
            '    </element>\n'
            '    <element name="username">\n'
            '      <location type="field">username</location>\n'
            '    </element>\n'
            '  </model>\n'
            '</models>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_MODEL)

    def test_xsd_rejects_element_without_location(self, tmp_path):
        """element 缺少 location 子元素应被 XSD 拒绝（minOccurs=1）"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="Login" type="ui">\n'
            '    <element name="username" type="id"/>\n'
            '  </model>\n'
            '</models>',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_MODEL,
        )


class TestModelParserRejectsOldFormat:
    """ModelParser 应在遇到旧格式时抛出 ModelParseError"""

    def _write_model_xml(self, tmp_path, content):
        """写入模型 XML 并返回路径（跳过 XSD 校验以测试 parser 逻辑）"""
        p = tmp_path / "model.xml"
        p.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n{content}',
            encoding="utf-8",
        )
        return p

    def test_parser_raises_on_value_attribute(self, tmp_path, monkeypatch):
        """ModelParser 遇到 value 属性应抛出 ModelParseError"""
        p = self._write_model_xml(tmp_path,
            '<models>\n'
            '  <model name="Login" type="ui">\n'
            '    <element name="username" type="id" value="uname"/>\n'
            '  </model>\n'
            '</models>'
        )
        # 跳过 XSD 校验以直接测试 parser 逻辑
        monkeypatch.setattr(RodskiXmlValidator, 'validate_file', lambda *a, **kw: None)
        with pytest.raises(ModelParseError) as exc_info:
            ModelParser(str(p))
        assert "username" in str(exc_info.value)
        assert "已废弃" in str(exc_info.value)
        assert "value" in str(exc_info.value)

    def test_parser_raises_on_locator_attribute(self, tmp_path, monkeypatch):
        """ModelParser 遇到 locator 属性应抛出 ModelParseError"""
        p = self._write_model_xml(tmp_path,
            '<models>\n'
            '  <model name="Login" type="ui">\n'
            '    <element name="btn" locator="id=submitBtn">\n'
            '      <location type="id">submitBtn</location>\n'
            '    </element>\n'
            '  </model>\n'
            '</models>'
        )
        monkeypatch.setattr(RodskiXmlValidator, 'validate_file', lambda *a, **kw: None)
        with pytest.raises(ModelParseError) as exc_info:
            ModelParser(str(p))
        assert "btn" in str(exc_info.value)
        assert "已废弃" in str(exc_info.value)
        assert "locator" in str(exc_info.value)

    def test_parser_accepts_new_format(self, tmp_path, monkeypatch):
        """ModelParser 正确解析 <location> 子元素格式"""
        p = self._write_model_xml(tmp_path,
            '<models>\n'
            '  <model name="Login" type="ui">\n'
            '    <element name="username">\n'
            '      <location type="id">usernameInput</location>\n'
            '    </element>\n'
            '    <element name="submit">\n'
            '      <location type="css" priority="1">#submit</location>\n'
            '      <location type="xpath" priority="2">//button[@type="submit"]</location>\n'
            '    </element>\n'
            '  </model>\n'
            '</models>'
        )
        monkeypatch.setattr(RodskiXmlValidator, 'validate_file', lambda *a, **kw: None)
        parser = ModelParser(str(p))
        login_model = parser.models["Login"]
        # 验证 username 元素
        assert login_model["username"]["locator_type"] == "id"
        assert login_model["username"]["locator_value"] == "usernameInput"
        # 验证 submit 元素（多定位器，按 priority 排序）
        assert login_model["submit"]["locator_type"] == "css"
        assert login_model["submit"]["locator_value"] == "#submit"
        assert len(login_model["submit"]["locations"]) == 2
        assert login_model["submit"]["locations"][1]["type"] == "xpath"

    def test_parser_accepts_interface_model(self, tmp_path, monkeypatch):
        """ModelParser 正确解析接口模型的 static/field 定位"""
        p = self._write_model_xml(tmp_path,
            '<models>\n'
            '  <model name="API" type="interface">\n'
            '    <element name="_method">\n'
            '      <location type="static">GET</location>\n'
            '    </element>\n'
            '    <element name="_url">\n'
            '      <location type="static">http://example.com/api</location>\n'
            '    </element>\n'
            '  </model>\n'
            '</models>'
        )
        monkeypatch.setattr(RodskiXmlValidator, 'validate_file', lambda *a, **kw: None)
        parser = ModelParser(str(p))
        api_model = parser.models["API"]
        assert api_model["_method"]["locator_type"] == "static"
        assert api_model["_method"]["locator_value"] == "GET"
        assert api_model["_url"]["locator_value"] == "http://example.com/api"
