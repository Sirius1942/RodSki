"""CaseParser 单元测试 - XML 版本（三阶段多 test_step）

使用 RodSki 自有测试执行器，不依赖 pytest。
"""
from pathlib import Path
from unittest.mock import patch
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


# ============================================================
# Scenario 解析测试（v6.3.0）
# ============================================================

SCENARIO_XML = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="sc001" title="场景测试">
    <test_case>
      <scenario id="s1" title="登录场景" group="auth" tag="smoke,login" depends="s0,setup">
        <test_step action="type" model="Login" data="L001"/>
        <test_step action="click" model="Login" data="submit"/>
      </scenario>
      <scenario id="s2" title="验证场景">
        <test_step action="verify" model="Home" data="V001"/>
      </scenario>
    </test_case>
  </case>
</cases>'''

SCENARIO_MINIMAL_XML = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="sc002" title="最小场景">
    <test_case>
      <scenario id="s_min">
        <test_step action="wait" model="" data="1"/>
      </scenario>
    </test_case>
  </case>
</cases>'''

SCENARIO_MIXED_XML = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="sc003" title="混合步骤">
    <test_case>
      <test_step action="navigate" model="" data="http://localhost"/>
      <scenario id="s_mix" title="中间场景" tag="regression">
        <test_step action="type" model="Form" data="F001"/>
      </scenario>
      <test_step action="close" model="" data=""/>
    </test_case>
  </case>
</cases>'''


def _write_xml(tmp_path: Path, content: str) -> str:
    f = tmp_path / "scenario_case.xml"
    f.write_text(content, encoding="utf-8")
    return str(f)


class TestCaseParserScenario:
    """测试 scenario 元素解析"""

    @patch('core.case_parser.RodskiXmlValidator.validate_file')
    def test_scenario_basic_attributes(self, mock_validate, tmp_path):
        """测试 scenario 属性正确提取（id, title, group, tag, depends）"""
        case_xml = _write_xml(tmp_path, SCENARIO_XML)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        assert len(cases) == 1
        case = cases[0]

        # has_scenarios 标记
        assert case['has_scenarios'] is True

        # scenarios 列表
        assert len(case['scenarios']) == 2

        s1 = case['scenarios'][0]
        assert s1['type'] == 'scenario'
        assert s1['id'] == 's1'
        assert s1['title'] == '登录场景'
        assert s1['group'] == 'auth'
        assert s1['tag'] == ['smoke', 'login']
        assert s1['depends'] == ['s0', 'setup']

        s2 = case['scenarios'][1]
        assert s2['id'] == 's2'
        assert s2['title'] == '验证场景'
        assert s2['group'] == ''
        assert s2['tag'] == []
        assert s2['depends'] == []

    @patch('core.case_parser.RodskiXmlValidator.validate_file')
    def test_scenario_inner_steps(self, mock_validate, tmp_path):
        """测试 scenario 内步骤正确解析"""
        case_xml = _write_xml(tmp_path, SCENARIO_XML)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        s1 = cases[0]['scenarios'][0]

        assert len(s1['steps']) == 2
        assert s1['steps'][0] == {'action': 'type', 'model': 'Login', 'data': 'L001'}
        assert s1['steps'][1] == {'action': 'click', 'model': 'Login', 'data': 'submit'}

        s2 = cases[0]['scenarios'][1]
        assert len(s2['steps']) == 1
        assert s2['steps'][0]['action'] == 'verify'

    @patch('core.case_parser.RodskiXmlValidator.validate_file')
    def test_scenario_minimal_defaults(self, mock_validate, tmp_path):
        """测试最小 scenario（仅 id），可选字段默认值"""
        case_xml = _write_xml(tmp_path, SCENARIO_MINIMAL_XML)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        s = cases[0]['scenarios'][0]

        assert s['id'] == 's_min'
        assert s['title'] == ''
        assert s['group'] == ''
        assert s['tag'] == []
        assert s['depends'] == []
        assert len(s['steps']) == 1

    @patch('core.case_parser.RodskiXmlValidator.validate_file')
    def test_scenario_mixed_with_bare_steps(self, mock_validate, tmp_path):
        """测试 scenario 与裸 test_step 混合"""
        case_xml = _write_xml(tmp_path, SCENARIO_MIXED_XML)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        case = cases[0]

        # test_case 阶段有 3 个元素：bare step, scenario, bare step
        tc = case['test_case']
        assert len(tc) == 3
        assert tc[0] == {'action': 'navigate', 'model': '', 'data': 'http://localhost'}
        assert tc[1]['type'] == 'scenario'
        assert tc[1]['id'] == 's_mix'
        assert tc[1]['tag'] == ['regression']
        assert tc[2] == {'action': 'close', 'model': '', 'data': ''}

        # scenarios 列表只包含 scenario 类型
        assert len(case['scenarios']) == 1
        assert case['scenarios'][0]['id'] == 's_mix'
        assert case['has_scenarios'] is True

    @patch('core.case_parser.RodskiXmlValidator.validate_file')
    def test_no_scenario_backward_compat(self, mock_validate, tmp_path):
        """测试旧格式（无 scenario）兼容 - has_scenarios=False, scenarios=[]"""
        case_xml = _write_xml(tmp_path, '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="old001" title="旧格式">
    <test_case>
      <test_step action="type" model="Login" data="L001"/>
    </test_case>
  </case>
</cases>''')
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        case = cases[0]

        assert case['has_scenarios'] is False
        assert case['scenarios'] == []
        assert len(case['test_case']) == 1
        assert case['test_case'][0]['action'] == 'type'

    @patch('core.case_parser.RodskiXmlValidator.validate_file')
    def test_scenario_in_test_case_phase_steps(self, mock_validate, tmp_path):
        """测试 scenario 出现在 test_case 的 steps 列表中"""
        case_xml = _write_xml(tmp_path, SCENARIO_XML)
        parser = CaseParser(case_xml)
        cases = parser.parse_cases()
        tc = cases[0]['test_case']

        # test_case 阶段应包含 2 个 scenario 元素
        assert len(tc) == 2

    @patch('core.case_parser.RodskiXmlValidator.validate_file')
    def test_collect_scenario_metadata_effective_tags(self, mock_validate, tmp_path):
        """测试 scenario 元数据索引合并文件级 tags 与 scenario tags。"""
        case_xml = _write_xml(tmp_path, '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases tags="suite,smoke">
  <case execute="是" id="sc004" title="标签合并" priority="P1">
    <test_case>
      <scenario id="s_tag" group="auth" tag="login,smoke">
        <test_step action="wait" model="" data="1"/>
      </scenario>
    </test_case>
  </case>
</cases>''')
        parser = CaseParser(case_xml)
        parser.parse_cases()

        metadata = parser.collect_scenario_metadata()

        assert metadata == [{
            'case_id': 'sc004',
            'case_priority': 'P1',
            'file_tags': ['suite', 'smoke'],
            'scenario_id': 's_tag',
            'scenario_group': 'auth',
            'scenario_tags': ['login', 'smoke'],
            'effective_tags': ['suite', 'smoke', 'login'],
        }]
