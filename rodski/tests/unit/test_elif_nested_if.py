"""WI-64 elif + 两层嵌套 if — 单元测试

覆盖：
- CaseParser 解析 elif 元素和 elif 链
- CaseParser 解析嵌套 if（最多 2 层）
- CaseParser 超过 2 层嵌套时报错
- SKIExecutor._execute_if_block 执行 elif 链
- SKIExecutor._execute_if_block 执行嵌套 if
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call

from core.case_parser import CaseParser
from core.exceptions import XmlSchemaValidationError
from core.ski_executor import SKIExecutor


# =====================================================================
# CaseParser — elif 解析
# =====================================================================

CASE_ELIF = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c001" title="elif 测试">
    <test_case>
      <if condition="$status == 200">
        <test_step action="wait" model="" data="1"/>
      </if>
      <elif condition="$status == 404">
        <test_step action="wait" model="" data="2"/>
      </elif>
      <elif condition="$status == 500">
        <test_step action="wait" model="" data="3"/>
      </elif>
      <else>
        <test_step action="wait" model="" data="4"/>
      </else>
    </test_case>
  </case>
</cases>'''


CASE_NESTED_IF = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c002" title="嵌套 if 测试">
    <test_case>
      <if condition="element_exists(#dialog)">
        <test_step action="type" model="Dialog" data="D001"/>
        <if condition="$status == error">
          <test_step action="screenshot" model="" data="error.png"/>
        </if>
      </if>
    </test_case>
  </case>
</cases>'''


CASE_IF_ELSE_ONLY = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c003" title="纯 if/else 测试">
    <test_case>
      <if condition="$flag == yes">
        <test_step action="wait" model="" data="10"/>
        <else>
          <test_step action="wait" model="" data="20"/>
        </else>
      </if>
    </test_case>
  </case>
</cases>'''


class TestCaseParserElif:
    """CaseParser 解析 elif 元素"""

    def test_elif_chain_parsed(self, tmp_path):
        """if 后紧跟的 elif 应被解析为 elif_chain"""
        f = tmp_path / "elif.xml"
        f.write_text(CASE_ELIF, encoding="utf-8")
        cases = CaseParser(str(f)).parse_cases()
        steps = cases[0]['test_case']
        assert len(steps) == 1  # 合并为一个 if 块
        if_block = steps[0]
        assert if_block['type'] == 'if'
        assert if_block['condition'] == '$status == 200'
        assert len(if_block.get('elif_chain', [])) == 2

    def test_elif_chain_conditions(self, tmp_path):
        """elif 链中的条件应被正确解析"""
        f = tmp_path / "elif.xml"
        f.write_text(CASE_ELIF, encoding="utf-8")
        cases = CaseParser(str(f)).parse_cases()
        if_block = cases[0]['test_case'][0]
        elif_chain = if_block['elif_chain']
        assert elif_chain[0]['condition'] == '$status == 404'
        assert elif_chain[1]['condition'] == '$status == 500'

    def test_elif_chain_steps(self, tmp_path):
        """elif 块内的 test_step 应被解析"""
        f = tmp_path / "elif.xml"
        f.write_text(CASE_ELIF, encoding="utf-8")
        cases = CaseParser(str(f)).parse_cases()
        if_block = cases[0]['test_case'][0]
        elif_chain = if_block['elif_chain']
        assert elif_chain[0]['steps'][0]['data'] == '2'
        assert elif_chain[1]['steps'][0]['data'] == '3'

    def test_else_after_elif_chain(self, tmp_path):
        """elif 链末尾的 else 应被合并到 if 块的 else_steps"""
        f = tmp_path / "elif.xml"
        f.write_text(CASE_ELIF, encoding="utf-8")
        cases = CaseParser(str(f)).parse_cases()
        if_block = cases[0]['test_case'][0]
        assert len(if_block['else_steps']) == 1
        assert if_block['else_steps'][0]['data'] == '4'


class TestCaseParserNestedIf:
    """CaseParser 解析嵌套 if"""

    def test_nested_if_parsed(self, tmp_path):
        """if 内部的嵌套 if 应被解析"""
        f = tmp_path / "nested.xml"
        f.write_text(CASE_NESTED_IF, encoding="utf-8")
        cases = CaseParser(str(f)).parse_cases()
        if_block = cases[0]['test_case'][0]
        assert if_block['type'] == 'if'
        # then 分支应包含 2 个元素：test_step + 嵌套 if
        then_steps = if_block['steps']
        assert len(then_steps) == 2
        assert then_steps[0]['action'] == 'type'
        assert then_steps[1]['type'] == 'if'
        assert then_steps[1]['condition'] == '$status == error'

    def test_nested_if_steps(self, tmp_path):
        """嵌套 if 的步骤应被正确解析"""
        f = tmp_path / "nested.xml"
        f.write_text(CASE_NESTED_IF, encoding="utf-8")
        cases = CaseParser(str(f)).parse_cases()
        nested_if = cases[0]['test_case'][0]['steps'][1]
        assert nested_if['steps'][0]['action'] == 'screenshot'
        assert nested_if['steps'][0]['data'] == 'error.png'

    def test_three_level_nesting_rejected_by_schema(self, tmp_path):
        """超过 2 层嵌套应被 XSD Schema 拒绝（NestedIfType 不允许嵌套 if）"""
        xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<cases>
  <case execute="是" id="c999" title="三层嵌套">
    <test_case>
      <if condition="a == 1">
        <if condition="b == 2">
          <if condition="c == 3">
            <test_step action="wait" model="" data="1"/>
          </if>
        </if>
      </if>
    </test_case>
  </case>
</cases>'''
        f = tmp_path / "deep.xml"
        f.write_text(xml, encoding="utf-8")
        with pytest.raises(XmlSchemaValidationError):
            CaseParser(str(f)).parse_cases()


class TestCaseParserIfElseBackcompat:
    """CaseParser 向后兼容 — 纯 if/else 结构"""

    def test_if_else_without_elif(self, tmp_path):
        """不含 elif 的 if/else 应正常解析"""
        f = tmp_path / "ifelse.xml"
        f.write_text(CASE_IF_ELSE_ONLY, encoding="utf-8")
        cases = CaseParser(str(f)).parse_cases()
        if_block = cases[0]['test_case'][0]
        assert if_block['type'] == 'if'
        assert if_block['steps'][0]['data'] == '10'
        assert if_block['else_steps'][0]['data'] == '20'
        assert 'elif_chain' not in if_block


# =====================================================================
# SKIExecutor — elif 链执行
# =====================================================================

class TestExecuteIfBlock:
    """SKIExecutor._execute_if_block 执行 if/elif/else"""

    @pytest.fixture
    def executor(self):
        """构造最小化 mock SKIExecutor"""
        ex = object.__new__(SKIExecutor)
        ex.driver = MagicMock()
        ex._driver_closed = False
        ex.auto_screenshot = False
        ex.dynamic_executor = MagicMock()
        ex.keyword_engine = MagicMock()
        ex.keyword_engine._context = MagicMock()
        ex.keyword_engine._context.history = []
        ex.keyword_engine._context.named = {}
        ex.data_resolver = MagicMock()
        ex.data_resolver.resolve.side_effect = lambda v: v
        ex.result_writer = MagicMock()
        ex.result_writer.current_run_dir = None
        ex.default_wait_time = 0.0
        ex._current_case_step_wait = None
        ex._current_case_steps_log = []
        ex._step_index = 0
        ex._current_case_id = "test"
        ex._phase_runtime_seq = 1
        ex.auto_screenshot_on_step = False
        ex.model_parser = None
        return ex

    def test_if_true_executes_then(self, executor):
        """if 条件为 True 时执行 then 分支"""
        executor.dynamic_executor.evaluate_condition.return_value = True
        step = {
            'type': 'if',
            'condition': '$x == 1',
            'steps': [{'action': 'wait', 'model': '', 'data': '1'}],
            'elif_chain': [{'condition': '$x == 2', 'steps': [{'action': 'wait', 'model': '', 'data': '2'}]}],
            'else_steps': [{'action': 'wait', 'model': '', 'data': '3'}],
        }
        executor._execute_if_block(step, '用例')
        executor.keyword_engine.execute.assert_called_once()
        call_args = executor.keyword_engine.execute.call_args
        assert call_args[0][0] == 'wait'

    def test_if_false_elif_true(self, executor):
        """if 为 False，elif 为 True 时执行 elif 分支"""
        executor.dynamic_executor.evaluate_condition.side_effect = [False, True]
        step = {
            'type': 'if',
            'condition': '$x == 1',
            'steps': [{'action': 'wait', 'model': '', 'data': 'if-branch'}],
            'elif_chain': [
                {'condition': '$x == 2', 'steps': [{'action': 'wait', 'model': '', 'data': 'elif-branch'}]},
            ],
            'else_steps': [{'action': 'wait', 'model': '', 'data': 'else-branch'}],
        }
        executor._execute_if_block(step, '用例')
        # 应只执行 elif 分支
        assert executor.keyword_engine.execute.call_count == 1
        call_data = executor.keyword_engine.execute.call_args[0][1]
        assert call_data['data'] == 'elif-branch'

    def test_all_false_executes_else(self, executor):
        """if 和所有 elif 均为 False 时执行 else 分支"""
        executor.dynamic_executor.evaluate_condition.side_effect = [False, False, False]
        step = {
            'type': 'if',
            'condition': '$x == 1',
            'steps': [{'action': 'wait', 'model': '', 'data': 'if-branch'}],
            'elif_chain': [
                {'condition': '$x == 2', 'steps': [{'action': 'wait', 'model': '', 'data': 'elif1'}]},
                {'condition': '$x == 3', 'steps': [{'action': 'wait', 'model': '', 'data': 'elif2'}]},
            ],
            'else_steps': [{'action': 'wait', 'model': '', 'data': 'else-branch'}],
        }
        executor._execute_if_block(step, '用例')
        assert executor.keyword_engine.execute.call_count == 1
        call_data = executor.keyword_engine.execute.call_args[0][1]
        assert call_data['data'] == 'else-branch'

    def test_all_false_no_else_noop(self, executor):
        """if 和 elif 均为 False 且无 else 时不执行任何步骤"""
        executor.dynamic_executor.evaluate_condition.side_effect = [False, False]
        step = {
            'type': 'if',
            'condition': '$x == 1',
            'steps': [{'action': 'wait', 'model': '', 'data': '1'}],
            'elif_chain': [
                {'condition': '$x == 2', 'steps': [{'action': 'wait', 'model': '', 'data': '2'}]},
            ],
            'else_steps': [],
        }
        executor._execute_if_block(step, '用例')
        executor.keyword_engine.execute.assert_not_called()

    def test_nested_if_executed(self, executor):
        """嵌套 if 块应被递归执行"""
        # 外层 if True，内层 if True
        executor.dynamic_executor.evaluate_condition.side_effect = [True, True]
        step = {
            'type': 'if',
            'condition': 'outer == yes',
            'steps': [
                {'action': 'wait', 'model': '', 'data': 'outer-step'},
                {
                    'type': 'if',
                    'condition': 'inner == yes',
                    'steps': [{'action': 'screenshot', 'model': '', 'data': 'inner-step'}],
                    'else_steps': [],
                },
            ],
            'else_steps': [],
        }
        executor._execute_if_block(step, '用例')
        assert executor.keyword_engine.execute.call_count == 2
        actions = [c[0][0] for c in executor.keyword_engine.execute.call_args_list]
        assert 'wait' in actions
        assert 'screenshot' in actions

    def test_nested_if_inner_false(self, executor):
        """外层 if True，内层 if False 时只执行外层步骤"""
        executor.dynamic_executor.evaluate_condition.side_effect = [True, False]
        step = {
            'type': 'if',
            'condition': 'outer == yes',
            'steps': [
                {'action': 'wait', 'model': '', 'data': 'outer-step'},
                {
                    'type': 'if',
                    'condition': 'inner == no',
                    'steps': [{'action': 'screenshot', 'model': '', 'data': 'inner'}],
                    'else_steps': [],
                },
            ],
            'else_steps': [],
        }
        executor._execute_if_block(step, '用例')
        assert executor.keyword_engine.execute.call_count == 1
        assert executor.keyword_engine.execute.call_args[0][0] == 'wait'

    def test_condition_eval_failure_skips_block(self, executor):
        """条件评估失败时跳过整个 if 块"""
        executor.dynamic_executor.evaluate_condition.side_effect = RuntimeError("eval error")
        step = {
            'type': 'if',
            'condition': 'bad_condition',
            'steps': [{'action': 'wait', 'model': '', 'data': '1'}],
            'else_steps': [],
        }
        # 不应抛异常
        executor._execute_if_block(step, '用例')
        executor.keyword_engine.execute.assert_not_called()
