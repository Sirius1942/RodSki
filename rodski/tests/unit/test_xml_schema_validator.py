"""RodskiXmlValidator 与 XmlSchemaValidationError 单元测试

测试 core/xml_schema_validator.py 中的 XML Schema 校验器。
覆盖：schemas 目录存在性、case.xsd（有效/缺少 test_case）、
      data.xsd（无效根元素）、model.xsd（UI/接口/数据库模型、
      无效 type、无效 locator、缺少 name）、
      globalvalue.xsd（有效/空/无效根/缺少 name/缺少 value/重复 group）、
      result.xsd（有效 element）、未知 kind 类型错误。
"""
from pathlib import Path

from core.exceptions import XmlSchemaValidationError
from core.xml_schema_validator import RodskiXmlValidator, SCHEMA_FILES, schemas_directory
from core.test_runner import assert_raises, assert_raises_match


class TestSchemasDirectory:
    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_schemas_dir_exists(self):
        d = schemas_directory()
        assert d.is_dir()
        assert (d / "case.xsd").is_file()


class TestValidateFileCase:
    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_valid_case_passes(self, tmp_path):
        p = tmp_path / "ok.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<cases>\n'
            '  <case execute="是" id="x" title="t">\n'
            '    <test_case>\n'
            '      <test_step action="wait" model="" data="1"/>\n'
            '    </test_case>\n'
            '  </case>\n'
            '</cases>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_CASE)

    def test_invalid_case_missing_test_case_raises(self, tmp_path):
        p = tmp_path / "bad.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<cases>\n'
            '  <case execute="是" id="x" title="t">\n'
            '  </case>\n'
            '</cases>',
            encoding="utf-8",
        )
        exc = assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_CASE,
        )
        assert "case.xsd" in str(exc) or SCHEMA_FILES["case"] in str(exc)
        assert exc.details.get("document_kind") == "case"


class TestValidateFileData:
    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_invalid_root_element_raises(self, tmp_path):
        p = tmp_path / "bad.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<wrong/>',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_DATA,
        )


class TestValidateElement:
    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_result_tree(self):
        import xml.etree.ElementTree as ET

        root = ET.Element("testresult")
        sum_el = ET.SubElement(root, "summary")
        for k, v in [
            ("total", "1"),
            ("passed", "1"),
            ("failed", "0"),
            ("skipped", "0"),
            ("errors", "0"),
        ]:
            sum_el.set(k, v)
        res = ET.SubElement(root, "results")
        r = ET.SubElement(res, "result")
        r.set("case_id", "c1")
        r.set("status", "PASS")
        RodskiXmlValidator.validate_element(root, RodskiXmlValidator.KIND_RESULT)


class TestValidateFileModel:
    """model.xsd 验证测试"""

    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_valid_ui_model(self, tmp_path):
        """有效的 UI 模型文件应通过验证"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="Login" type="ui">\n'
            '    <element name="username" type="id" value="uname"/>\n'
            '    <element name="password" type="css" value="#pwd"/>\n'
            '  </model>\n'
            '</models>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_MODEL)

    def test_valid_interface_model(self, tmp_path):
        """有效的接口模型文件应通过验证"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="LoginAPI" type="interface">\n'
            '    <element name="_method" type="static" value="POST"/>\n'
            '    <element name="_url" type="static" value="http://api.example.com/login"/>\n'
            '    <element name="username" type="field" value="username"/>\n'
            '  </model>\n'
            '</models>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_MODEL)

    def test_valid_database_model(self, tmp_path):
        """有效的数据库模型文件应通过验证"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="UserDB" type="database" connection="testdb">\n'
            '    <query name="list_users"><sql>SELECT * FROM users</sql></query>\n'
            '  </model>\n'
            '</models>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_MODEL)

    def test_invalid_model_type_raises(self, tmp_path):
        """model type 不在枚举值内应校验失败"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="Bad" type="invalid_type">\n'
            '    <element name="x" type="id" value="x"/>\n'
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

    def test_invalid_locator_type_raises(self, tmp_path):
        """element 的 location type 不在枚举值内应校验失败"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model name="Page" type="ui">\n'
            '    <element name="btn">\n'
            '      <location type="invalid_locator">value</location>\n'
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

    def test_model_missing_name_raises(self, tmp_path):
        """model 缺少 name 属性应校验失败"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models>\n'
            '  <model type="ui">\n'
            '    <element name="x" type="id" value="x"/>\n'
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

    def test_empty_models(self, tmp_path):
        """空 models 文件应通过验证"""
        p = tmp_path / "model.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<models/>\n',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_MODEL)


class TestValidateFileGlobalValue:
    """globalvalue.xsd 验证测试"""

    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_valid_globalvalue(self, tmp_path):
        """有效的 globalvalue 文件应通过验证"""
        p = tmp_path / "globalvalue.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<globalvalue>\n'
            '  <group name="DefaultValue">\n'
            '    <var name="URL" value="https://example.com"/>\n'
            '    <var name="BrowserType" value="chrome"/>\n'
            '    <var name="WaitTime" value="0"/>\n'
            '  </group>\n'
            '  <group name="testdb">\n'
            '    <var name="type" value="sqlite"/>\n'
            '    <var name="database" value="/tmp/test.db"/>\n'
            '  </group>\n'
            '</globalvalue>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_GLOBALVALUE)

    def test_empty_globalvalue(self, tmp_path):
        """空 globalvalue 文件应通过验证"""
        p = tmp_path / "globalvalue.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<globalvalue/>\n',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_GLOBALVALUE)

    def test_invalid_root_element_raises(self, tmp_path):
        """根元素不是 globalvalue 应校验失败"""
        p = tmp_path / "globalvalue.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<wrong_root/>\n',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_GLOBALVALUE,
        )

    def test_group_missing_name_raises(self, tmp_path):
        """group 缺少 name 属性应校验失败"""
        p = tmp_path / "globalvalue.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<globalvalue>\n'
            '  <group>\n'
            '    <var name="k" value="v"/>\n'
            '  </group>\n'
            '</globalvalue>',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_GLOBALVALUE,
        )

    def test_var_missing_value_raises(self, tmp_path):
        """var 缺少 value 属性应校验失败"""
        p = tmp_path / "globalvalue.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<globalvalue>\n'
            '  <group name="g1">\n'
            '    <var name="k"/>\n'
            '  </group>\n'
            '</globalvalue>',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_GLOBALVALUE,
        )

    def test_duplicate_group_name_raises(self, tmp_path):
        """group name 重复应校验失败（unique 约束）"""
        p = tmp_path / "globalvalue.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<globalvalue>\n'
            '  <group name="dup">\n'
            '    <var name="a" value="1"/>\n'
            '  </group>\n'
            '  <group name="dup">\n'
            '    <var name="b" value="2"/>\n'
            '  </group>\n'
            '</globalvalue>',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_GLOBALVALUE,
        )


class TestKindInvalid:
    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_unknown_kind(self, tmp_path):
        p = tmp_path / "a.xml"
        p.write_text("<a/>")
        assert_raises_match(
            ValueError,
            "不支持的 document_kind",
            RodskiXmlValidator.validate_file,
            p,
            "unknown",
        )
