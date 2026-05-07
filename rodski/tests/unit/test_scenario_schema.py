"""test_scenario_schema.py - scenario 元素 XSD 校验测试

验证 case.xsd 中新增的 <scenario> 元素定义：
- 新 fixture（含 scenario）通过校验
- 旧格式（无 scenario）仍通过校验
- scenario 缺少 id 时校验失败
- scenario 内可以包含 if/loop
"""
from pathlib import Path

from core.exceptions import XmlSchemaValidationError
from core.xml_schema_validator import RodskiXmlValidator
from core.test_runner import assert_raises


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestScenarioSchemaValid:
    """scenario 元素合法性校验"""

    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_fixture_with_scenario_passes(self):
        """包含 scenario 的 fixture 文件应通过 case.xsd 校验"""
        fixture = FIXTURES_DIR / "case_with_scenario.xml"
        assert fixture.is_file(), f"fixture not found: {fixture}"
        RodskiXmlValidator.validate_file(fixture, RodskiXmlValidator.KIND_CASE)

    def test_old_format_without_scenario_passes(self, tmp_path):
        """旧格式（无 scenario）仍应通过校验 - 向后兼容"""
        p = tmp_path / "old_format.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<cases>\n'
            '  <case execute="是" id="TC001" title="旧格式用例">\n'
            '    <test_case>\n'
            '      <test_step action="navigate" model="" data="https://example.com"/>\n'
            '      <test_step action="verify" model="Page.title" data="首页"/>\n'
            '    </test_case>\n'
            '  </case>\n'
            '</cases>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_CASE)

    def test_scenario_with_if_passes(self, tmp_path):
        """scenario 内包含 if 容器应通过校验"""
        p = tmp_path / "scenario_if.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<cases>\n'
            '  <case execute="是" id="TC002" title="scenario含if">\n'
            '    <test_case>\n'
            '      <scenario id="SC-IF" title="条件场景">\n'
            '        <test_step action="set" model="status" data="ok"/>\n'
            '        <if condition="$status==ok">\n'
            '          <test_step action="verify" model="Page.msg" data="成功"/>\n'
            '        </if>\n'
            '      </scenario>\n'
            '    </test_case>\n'
            '  </case>\n'
            '</cases>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_CASE)

    def test_scenario_with_loop_passes(self, tmp_path):
        """scenario 内包含 loop 容器应通过校验"""
        p = tmp_path / "scenario_loop.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<cases>\n'
            '  <case execute="是" id="TC003" title="scenario含loop">\n'
            '    <test_case>\n'
            '      <scenario id="SC-LOOP" title="循环场景">\n'
            '        <loop range="1-3" var="i">\n'
            '          <test_step action="wait" model="" data="1"/>\n'
            '        </loop>\n'
            '        <test_step action="verify" model="Page.count" data="3"/>\n'
            '      </scenario>\n'
            '    </test_case>\n'
            '  </case>\n'
            '</cases>',
            encoding="utf-8",
        )
        RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_CASE)


class TestScenarioSchemaInvalid:
    """scenario 元素非法情况校验"""

    def setup_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def teardown_method(self):
        RodskiXmlValidator.clear_schema_cache()

    def test_scenario_missing_id_fails(self, tmp_path):
        """scenario 缺少 required id 属性时应校验失败"""
        p = tmp_path / "no_id.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<cases>\n'
            '  <case execute="是" id="TC004" title="缺少id">\n'
            '    <test_case>\n'
            '      <scenario title="无id场景">\n'
            '        <test_step action="wait" model="" data="1"/>\n'
            '      </scenario>\n'
            '    </test_case>\n'
            '  </case>\n'
            '</cases>',
            encoding="utf-8",
        )
        assert_raises(
            XmlSchemaValidationError,
            RodskiXmlValidator.validate_file,
            p,
            RodskiXmlValidator.KIND_CASE,
        )
