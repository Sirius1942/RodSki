"""Unit tests for CaseParser nested-case support (v11.5.0)"""
import pytest
from pathlib import Path
from rodski.core.case_parser import CaseParser
from rodski.core.exceptions import DuplicateCaseIdInFileError


# 最小合法 case XML 模板（符合 case.xsd）
MINIMAL_CASE_XML = """
<cases>
  <case id="{case_id}" title="Test" execute="{execute}">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
</cases>
"""


class TestCaseParserCaseFileField:
    """测试 CaseParser 为用例字典添加 case_file/case_uid 字段"""

    def test_case_file_for_nested_structure(self, tmp_path):
        """嵌套结构下的 case_file 为相对 case/ 的 POSIX 路径"""
        module_dir = tmp_path / "module"
        case_file = module_dir / "case" / "order" / "refund" / "apply.xml"
        case_file.parent.mkdir(parents=True)
        case_file.write_text(MINIMAL_CASE_XML.format(case_id="TC001", execute="是"))

        parser = CaseParser(str(case_file))
        cases = parser.parse_cases()

        assert len(cases) == 1
        assert cases[0]["case_file"] == "order/refund/apply.xml"
        assert cases[0]["case_uid"] == "order/refund/apply.xml::TC001"

    def test_case_file_for_root_level(self, tmp_path):
        """case/ 根目录下的文件，case_file 为文件名"""
        module_dir = tmp_path / "module"
        case_file = module_dir / "case" / "smoke.xml"
        case_file.parent.mkdir(parents=True)
        case_file.write_text(MINIMAL_CASE_XML.format(case_id="TC001", execute="是"))

        parser = CaseParser(str(case_file))
        cases = parser.parse_cases()

        assert cases[0]["case_file"] == "smoke.xml"
        assert cases[0]["case_uid"] == "smoke.xml::TC001"

    def test_case_file_graceful_fallback_for_temp_path(self, tmp_path):
        """单元测试场景：不在真实模块结构下，退化为文件名"""
        # 旧测试常直接在 tmp_path 下写文件，不构造 module/case/ 结构
        case_file = tmp_path / "test_case.xml"
        case_file.write_text(MINIMAL_CASE_XML.format(case_id="TC001", execute="是"))

        parser = CaseParser(str(case_file))
        cases = parser.parse_cases()

        # 退化为文件名，不报错
        assert cases[0]["case_file"] == "test_case.xml"
        assert cases[0]["case_uid"] == "test_case.xml::TC001"

    def test_directory_input_all_files_get_case_file(self, tmp_path):
        """目录输入：每个文件的用例都有正确的 case_file"""
        module_dir = tmp_path / "module"
        case_dir = module_dir / "case"
        (case_dir / "order").mkdir(parents=True)

        (case_dir / "smoke.xml").write_text(MINIMAL_CASE_XML.format(case_id="TC001", execute="是"))
        (case_dir / "order" / "basic.xml").write_text(MINIMAL_CASE_XML.format(case_id="TC002", execute="是"))

        parser = CaseParser(str(case_dir))
        cases = parser.parse_cases()

        case_files = {c["case_id"]: c["case_file"] for c in cases}
        assert case_files == {
            "TC001": "smoke.xml",
            "TC002": "order/basic.xml",
        }


class TestDuplicateCaseIdInFile:
    """测试同一文件内 case@id 重复检测（SKI205）"""

    def test_duplicate_id_execute_yes(self, tmp_path):
        """同一文件内两个 execute=是 的用例 ID 重复"""
        case_file = tmp_path / "dup.xml"
        case_file.write_text("""
<cases>
  <case id="TC001" title="A" execute="是">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
  <case id="TC001" title="B" execute="是">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
</cases>
""")

        parser = CaseParser(str(case_file))
        with pytest.raises(DuplicateCaseIdInFileError) as exc_info:
            parser.parse_cases()

        assert exc_info.value.error_code == "SKI205"
        assert exc_info.value.case_id == "TC001"
        assert exc_info.value.case_file == "dup.xml"

    def test_duplicate_id_one_disabled(self, tmp_path):
        """一个 execute=是，一个 execute=否，仍然算重复"""
        case_file = tmp_path / "dup.xml"
        case_file.write_text("""
<cases>
  <case id="TC001" title="A" execute="是">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
  <case id="TC001" title="B" execute="否">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
</cases>
""")

        parser = CaseParser(str(case_file))
        with pytest.raises(DuplicateCaseIdInFileError) as exc_info:
            parser.parse_cases()

        assert exc_info.value.error_code == "SKI205"
        assert exc_info.value.case_id == "TC001"

    def test_duplicate_id_both_disabled(self, tmp_path):
        """两个 execute=否 的用例 ID 重复也报错"""
        case_file = tmp_path / "dup.xml"
        case_file.write_text("""
<cases>
  <case id="TC001" title="A" execute="否">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
  <case id="TC001" title="B" execute="否">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
</cases>
""")

        parser = CaseParser(str(case_file))
        with pytest.raises(DuplicateCaseIdInFileError):
            parser.parse_cases()

    def test_same_id_different_files_allowed(self, tmp_path):
        """跨文件同 ID 合法（v11.5.0 新规则）"""
        module_dir = tmp_path / "module"
        case_dir = module_dir / "case"
        case_dir.mkdir(parents=True)

        (case_dir / "a.xml").write_text(MINIMAL_CASE_XML.format(case_id="TC001", execute="是"))
        (case_dir / "b.xml").write_text(MINIMAL_CASE_XML.format(case_id="TC001", execute="是"))

        parser = CaseParser(str(case_dir))
        cases = parser.parse_cases()

        # 不报错，两个用例都被解析
        assert len(cases) == 2
        uids = {c["case_uid"] for c in cases}
        assert uids == {"a.xml::TC001", "b.xml::TC001"}

    def test_unique_ids_no_error(self, tmp_path):
        """同一文件内 ID 不重复时正常"""
        case_file = tmp_path / "ok.xml"
        case_file.write_text("""
<cases>
  <case id="TC001" title="A" execute="是">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
  <case id="TC002" title="B" execute="否">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
  <case id="TC003" title="C" execute="是">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
</cases>
""")

        parser = CaseParser(str(case_file))
        cases = parser.parse_cases()

        # 只有 execute=是 的被解析
        assert len(cases) == 2
        ids = {c["case_id"] for c in cases}
        assert ids == {"TC001", "TC003"}

    def test_error_message_contains_file_and_id(self, tmp_path):
        """SKI205 错误消息包含文件路径与 ID"""
        module_dir = tmp_path / "module"
        case_file = module_dir / "case" / "order" / "dup.xml"
        case_file.parent.mkdir(parents=True)
        case_file.write_text("""
<cases>
  <case id="DUPLICATE" title="A" execute="是">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
  <case id="DUPLICATE" title="B" execute="是">
    <test_case>
      <test_step action="assert" model="" data="1==1"/>
    </test_case>
  </case>
</cases>
""")

        parser = CaseParser(str(case_file))
        with pytest.raises(DuplicateCaseIdInFileError) as exc_info:
            parser.parse_cases()

        error_msg = str(exc_info.value)
        assert "order/dup.xml" in error_msg
        assert "DUPLICATE" in error_msg

