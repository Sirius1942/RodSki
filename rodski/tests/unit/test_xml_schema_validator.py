"""RodskiXmlValidator 与 XmlSchemaValidationError 单元测试

使用 RodSki 自有测试执行器，不依赖 pytest。
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
