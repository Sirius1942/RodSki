"""CaseParser 单元测试 - XML 版本（三阶段多 test_step）

使用 RodSki 自有测试执行器，不依赖 pytest。
"""
from pathlib import Path
from core.case_parser import CaseParser
from core.test_runner import assert_raises


CASE_XML_CONTENT = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="登录测试" description="验证登录" component_type="界面">
    <pre_process>
      <test_step action="navigate" model="" data="http://localhost/login"/>
    </pre_process>
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
      <test_step action="verify" model="Login" data="V001"/>
    </test_case>
    <post_process>
      <test_step action="close" model="" data=""/>
    </post_process>
  </case>
  <case execute="否" id="c002" title="跳过用例" description="不执行">
    <test_case>
      <test_step action="type" model="Login" data="L002"/>
    </test_case>
  </case>
  <case execute="是" id="c003" title="DB验证" component_type="数据库">
    <test_case>
      <test_step action="DB" model="demodb" data="QuerySQL.Q001"/>
    </test_case>
  </case>
</cases>'''


def _write_case_xml(tmp_path: Path) -> str:
    f = tmp_path / "test_case.xml"
    f.write_text(CASE_XML_CONTENT, encoding="utf-8")
    return str(f)


def _write_case_dir(tmp_path: Path) -> str:
    case_d = tmp_path / "case"
    case_d.mkdir()
    (case_d / "a_case.xml").write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="a001" title="文件1用例">
    <test_case>
      <test_step action="wait" model="" data="1"/>
    </test_case>
  </case>
</cases>''', encoding="utf-8")
    (case_d / "b_case.xml").write_text('''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="b001" title="文件2用例">
    <test_case>
      <test_step action="wait" model="" data="2"/>
    </test_case>
  </case>
</cases>''', encoding="utf-8")
    return str(case_d)


class TestCaseParserFile:
    def test_parse_filters_by_execute(self, tmp_path):
        case_xml = _write_case_xml(tmp_path)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        assert len(cases) == 2
        ids = [c['case_id'] for c in cases]
        assert 'c001' in ids
        assert 'c003' in ids
        assert 'c002' not in ids

    def test_parse_three_phases(self, tmp_path):
        case_xml = _write_case_xml(tmp_path)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        c001 = cases[0]
        assert len(c001['pre_process']) == 1
        assert c001['pre_process'][0]['action'] == 'navigate'
        assert len(c001['test_case']) == 2
        assert c001['test_case'][0]['action'] == 'type'
        assert c001['test_case'][1]['action'] == 'verify'
        assert len(c001['post_process']) == 1
        assert c001['post_process'][0]['action'] == 'close'

    def test_missing_optional_phases_empty_lists(self, tmp_path):
        case_xml = _write_case_xml(tmp_path)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        c003 = [c for c in cases if c['case_id'] == 'c003'][0]
        assert c003['pre_process'] == []
        assert c003['post_process'] == []
        assert len(c003['test_case']) == 1

    def test_attributes(self, tmp_path):
        case_xml = _write_case_xml(tmp_path)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        c001 = cases[0]
        assert c001['title'] == '登录测试'
        assert c001['description'] == '验证登录'
        assert c001['component_type'] == '界面'


class TestCaseParserDirectory:
    def test_parse_directory(self, tmp_path):
        case_dir = _write_case_dir(tmp_path)
        parser = CaseParser(case_dir)
        cases = parser.parse_cases()
        assert len(cases) == 2
        ids = [c['case_id'] for c in cases]
        assert 'a001' in ids
        assert 'b001' in ids

    def test_sorted_by_filename(self, tmp_path):
        case_dir = _write_case_dir(tmp_path)
        parser = CaseParser(case_dir)
        cases = parser.parse_cases()
        assert cases[0]['case_id'] == 'a001'
        assert cases[1]['case_id'] == 'b001'


class TestCaseParserErrors:
    def test_nonexistent_path(self):
        parser = CaseParser("/nonexistent/path.xml")
        assert_raises(FileNotFoundError, parser.parse_cases)

    def test_close_is_noop(self, tmp_path):
        case_xml = _write_case_xml(tmp_path)
        parser = CaseParser(case_xml)
        parser.close()
