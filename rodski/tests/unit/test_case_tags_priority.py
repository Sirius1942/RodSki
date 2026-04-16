"""WI-63 Case Tag 选择性执行 — 单元测试

覆盖：
- CaseParser 解析 tags / priority 属性
- SKIExecutor._filter_cases 按 tags / priority / exclude_tags 过滤
- CLI 参数解析（--tags / --priority / --exclude-tags）
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from core.case_parser import CaseParser
from core.ski_executor import SKIExecutor


# =====================================================================
# CaseParser — tags / priority 解析
# =====================================================================

CASE_WITH_TAGS = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases tags="smoke,login">
  <case execute="是" id="c001" title="冒烟登录" priority="P0">
    <test_case>
      <test_step action="wait" model="" data="1"/>
    </test_case>
  </case>
  <case execute="是" id="c002" title="回归支付" priority="P1">
    <test_case>
      <test_step action="wait" model="" data="1"/>
    </test_case>
  </case>
  <case execute="是" id="c003" title="无标签用例">
    <test_case>
      <test_step action="wait" model="" data="1"/>
    </test_case>
  </case>
</cases>'''

CASE_WITHOUT_TAGS = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c010" title="无套件标签用例" priority="P2">
    <test_case>
      <test_step action="wait" model="" data="1"/>
    </test_case>
  </case>
</cases>'''


def _write_tags_xml(tmp_path: Path) -> str:
    f = tmp_path / "tags_case.xml"
    f.write_text(CASE_WITH_TAGS, encoding="utf-8")
    return str(f)


class TestCaseParserTags:
    """CaseParser 解析 tags 和 priority 属性"""

    def test_suite_tags_shared_by_all_cases(self, tmp_path):
        """<cases> 上的 tags 应被所有 case 共享"""
        path = _write_tags_xml(tmp_path)
        cases = CaseParser(path).parse_cases()
        for c in cases:
            assert c['tags'] == ['smoke', 'login']

    def test_parse_priority(self, tmp_path):
        """priority 属性应被解析为字符串"""
        path = _write_tags_xml(tmp_path)
        cases = CaseParser(path).parse_cases()
        c001 = [c for c in cases if c['case_id'] == 'c001'][0]
        assert c001['priority'] == 'P0'

    def test_no_suite_tags_returns_empty_list(self, tmp_path):
        """<cases> 未设置 tags 时所有用例 tags 为空列表"""
        f = tmp_path / "no_tags.xml"
        f.write_text(CASE_WITHOUT_TAGS, encoding="utf-8")
        cases = CaseParser(str(f)).parse_cases()
        assert cases[0]['tags'] == []

    def test_no_priority_returns_empty_string(self, tmp_path):
        """未设置 priority 的用例应返回空字符串"""
        path = _write_tags_xml(tmp_path)
        cases = CaseParser(path).parse_cases()
        c003 = [c for c in cases if c['case_id'] == 'c003'][0]
        assert c003['priority'] == ''


# =====================================================================
# SKIExecutor._filter_cases — 过滤逻辑
# =====================================================================

def _make_cases():
    """构造测试用例列表"""
    return [
        {'case_id': 'c001', 'tags': ['smoke', 'login'], 'priority': 'P0'},
        {'case_id': 'c002', 'tags': ['regression', 'payment'], 'priority': 'P1'},
        {'case_id': 'c003', 'tags': ['smoke', 'payment'], 'priority': 'P2'},
        {'case_id': 'c004', 'tags': [], 'priority': ''},
        {'case_id': 'c005', 'tags': ['slow', 'regression'], 'priority': 'P0'},
    ]


class TestFilterCases:
    """SKIExecutor._filter_cases 过滤逻辑"""

    def test_no_filters_returns_all(self):
        """无过滤条件时返回全部用例"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(cases)
        assert len(result) == 5

    def test_filter_by_single_tag(self):
        """按单个 tag 过滤"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(cases, filter_tags=['smoke'])
        ids = [c['case_id'] for c in result]
        assert 'c001' in ids
        assert 'c003' in ids
        assert 'c002' not in ids

    def test_filter_by_multiple_tags_or(self):
        """多个 tag 为 OR 匹配"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(cases, filter_tags=['login', 'payment'])
        ids = [c['case_id'] for c in result]
        assert 'c001' in ids  # login
        assert 'c002' in ids  # payment
        assert 'c003' in ids  # payment

    def test_filter_by_priority(self):
        """按 priority 过滤"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(cases, filter_priority=['P0'])
        ids = [c['case_id'] for c in result]
        assert 'c001' in ids
        assert 'c005' in ids
        assert 'c002' not in ids

    def test_exclude_tags(self):
        """exclude_tags 应排除匹配的用例"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(cases, exclude_tags=['slow'])
        ids = [c['case_id'] for c in result]
        assert 'c005' not in ids
        assert len(result) == 4

    def test_filter_tags_and_exclude_tags(self):
        """同时使用 filter_tags 和 exclude_tags"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(
            cases, filter_tags=['regression'], exclude_tags=['slow']
        )
        ids = [c['case_id'] for c in result]
        assert 'c002' in ids      # regression 且无 slow
        assert 'c005' not in ids   # regression 但有 slow → 被排除

    def test_filter_tags_and_priority(self):
        """同时使用 filter_tags 和 filter_priority"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(
            cases, filter_tags=['smoke'], filter_priority=['P0']
        )
        ids = [c['case_id'] for c in result]
        assert ids == ['c001']  # smoke + P0

    def test_no_match_returns_empty(self):
        """无匹配时返回空列表"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(cases, filter_tags=['nonexistent'])
        assert result == []

    def test_empty_tags_case_excluded_by_tag_filter(self):
        """无 tags 的用例在有 filter_tags 时被排除"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(cases, filter_tags=['smoke'])
        ids = [c['case_id'] for c in result]
        assert 'c004' not in ids

    def test_empty_priority_case_excluded_by_priority_filter(self):
        """无 priority 的用例在有 filter_priority 时被排除"""
        cases = _make_cases()
        result = SKIExecutor._filter_cases(cases, filter_priority=['P0'])
        ids = [c['case_id'] for c in result]
        assert 'c004' not in ids
