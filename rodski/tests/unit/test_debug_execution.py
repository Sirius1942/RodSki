"""Debug execution mode unit tests.

Tests for kind="scenario_debug" and kind="step_debug" plan execution.
Covers:
- scenario_debug prepare=auto executes pre_process + scenario
- scenario_debug prepare=none skips pre_process
- scenario_debug cleanup=否 skips post_process
- scenario_debug cleanup=是 executes post_process
- step_debug step_mode=only executes only the specified step
- step_debug step_mode=from executes from specified step to end
- step_debug prepare=auto executes pre_process + preceding steps + target step
"""
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from core.ski_executor import SKIExecutor


@pytest.fixture
def module_dir(tmp_path):
    """Create standard test module directory structure."""
    mod = tmp_path / "test_module"
    (mod / "case").mkdir(parents=True)
    (mod / "model").mkdir()
    (mod / "data").mkdir()
    (mod / "fun").mkdir()
    (mod / "result").mkdir()

    (mod / "model" / "model.xml").write_text(
        '<?xml version="1.0"?><models></models>', encoding="utf-8"
    )
    (mod / "data" / "globalvalue.xml").write_text(
        '<?xml version="1.0"?><globalvalue></globalvalue>', encoding="utf-8"
    )
    (mod / "case" / "test.xml").write_text(
        '<?xml version="1.0"?><cases></cases>', encoding="utf-8"
    )
    return mod


@pytest.fixture
def executor(module_dir):
    """Create a SKIExecutor with mocked dependencies."""
    case_file = module_dir / "case" / "test.xml"
    driver = MagicMock()

    with patch("core.ski_executor.DataTableParser") as mock_dtp, \
         patch("core.ski_executor.GlobalValueParser") as mock_gvp, \
         patch("core.ski_executor.CaseParser") as mock_cp, \
         patch("core.ski_executor.KeywordEngine") as mock_ke, \
         patch("core.ski_executor.DataResolver") as mock_dr, \
         patch("core.ski_executor.ResultWriter") as mock_rw:
        mock_dtp.return_value = MagicMock()
        mock_gvp.return_value.parse.return_value = {}
        mock_cp.return_value = MagicMock()
        mock_ke.return_value = MagicMock()
        mock_ke.return_value._context = MagicMock()
        mock_ke.return_value._context.history = []
        mock_ke.return_value._context.named = {}
        mock_ke.return_value.get_return = MagicMock(return_value=None)
        mock_dr.return_value = MagicMock()
        mock_rw.return_value = MagicMock()
        mock_rw.return_value.current_run_dir = module_dir / "result" / "run_001"

        exe = SKIExecutor(
            case_path=str(case_file),
            driver=driver,
            module_dir=str(module_dir),
        )
    return exe


def _make_case(pre_steps=None, scenarios=None, post_steps=None):
    """Helper to build a case dict for debug execution tests."""
    return {
        'case_id': 'tc001',
        'title': 'Test Case 001',
        'pre_process': pre_steps or [],
        'test_case': [],
        'post_process': post_steps or [],
        'scenarios': scenarios or [],
    }


def _make_step(action, model='', data=''):
    return {'action': action, 'model': model, 'data': data}


def _make_scenario(scenario_id, steps):
    return {'id': scenario_id, 'title': f'Scenario {scenario_id}', 'type': 'scenario', 'steps': steps, 'depends': [], 'group': '', 'tag': []}


class TestScenarioDebugPrepareAuto:
    """scenario_debug prepare=auto: executes pre_process + full scenario."""

    def test_executes_pre_process_and_scenario(self, executor):
        pre_steps = [_make_step('open', 'browser', 'http://example.com')]
        scenario_steps = [_make_step('click', 'btn_login'), _make_step('type', 'input_user', 'admin')]
        scenario = _make_scenario('s1', scenario_steps)
        case = _make_case(pre_steps=pre_steps, scenarios=[scenario])

        debug_config = {'prepare': 'auto', 'cleanup': '否', 'step_mode': 'all'}
        selected_entries = [{'type': 'scenario', 'case_id': 'tc001', 'scenario_id': 's1'}]

        executed_steps = []
        original_run_steps = executor._run_steps
        original_execute_step_list = executor._execute_step_list

        def mock_run_steps(steps, phase):
            for s in steps:
                if s.get('action'):
                    executed_steps.append(('run_steps', phase, s['action']))

        def mock_execute_step_list(steps, phase):
            for s in steps:
                if s.get('action'):
                    executed_steps.append(('step_list', phase, s['action']))

        executor._run_steps = mock_run_steps
        executor._execute_step_list = mock_execute_step_list

        result = executor._execute_debug_case(case, 'scenario_debug', debug_config, selected_entries)

        assert result['status'] == 'PASS'
        # pre_process executed via _run_steps
        assert ('run_steps', '预处理', 'open') in executed_steps
        # scenario steps executed via _execute_step_list
        assert ('step_list', '用例', 'click') in executed_steps
        assert ('step_list', '用例', 'type') in executed_steps


class TestScenarioDebugPrepareNone:
    """scenario_debug prepare=none: skips pre_process."""

    def test_skips_pre_process(self, executor):
        pre_steps = [_make_step('open', 'browser', 'http://example.com')]
        scenario_steps = [_make_step('click', 'btn_login')]
        scenario = _make_scenario('s1', scenario_steps)
        case = _make_case(pre_steps=pre_steps, scenarios=[scenario])

        debug_config = {'prepare': 'none', 'cleanup': '否', 'step_mode': 'all'}
        selected_entries = [{'type': 'scenario', 'case_id': 'tc001', 'scenario_id': 's1'}]

        executed_steps = []

        def mock_run_steps(steps, phase):
            for s in steps:
                if s.get('action'):
                    executed_steps.append(('run_steps', phase, s['action']))

        def mock_execute_step_list(steps, phase):
            for s in steps:
                if s.get('action'):
                    executed_steps.append(('step_list', phase, s['action']))

        executor._run_steps = mock_run_steps
        executor._execute_step_list = mock_execute_step_list

        result = executor._execute_debug_case(case, 'scenario_debug', debug_config, selected_entries)

        assert result['status'] == 'PASS'
        # pre_process NOT executed
        assert not any(phase == '预处理' for _, phase, _ in executed_steps)
        # scenario steps still executed
        assert ('step_list', '用例', 'click') in executed_steps


class TestScenarioDebugCleanupNo:
    """scenario_debug cleanup=否: skips post_process."""

    def test_skips_post_process(self, executor):
        scenario_steps = [_make_step('click', 'btn')]
        scenario = _make_scenario('s1', scenario_steps)
        post_steps = [_make_step('close', 'browser')]
        case = _make_case(scenarios=[scenario], post_steps=post_steps)

        debug_config = {'prepare': 'none', 'cleanup': '否', 'step_mode': 'all'}
        selected_entries = [{'type': 'scenario', 'case_id': 'tc001', 'scenario_id': 's1'}]

        executed_steps = []

        def mock_run_steps(steps, phase):
            for s in steps:
                if s.get('action'):
                    executed_steps.append(('run_steps', phase, s['action']))

        def mock_execute_step_list(steps, phase):
            for s in steps:
                if s.get('action'):
                    executed_steps.append(('step_list', phase, s['action']))

        executor._run_steps = mock_run_steps
        executor._execute_step_list = mock_execute_step_list

        result = executor._execute_debug_case(case, 'scenario_debug', debug_config, selected_entries)

        assert result['status'] == 'PASS'
        assert not any(phase == '后处理' for _, phase, _ in executed_steps)


class TestScenarioDebugCleanupYes:
    """scenario_debug cleanup=是: executes post_process."""

    def test_executes_post_process(self, executor):
        scenario_steps = [_make_step('click', 'btn')]
        scenario = _make_scenario('s1', scenario_steps)
        post_steps = [_make_step('close', 'browser')]
        case = _make_case(scenarios=[scenario], post_steps=post_steps)

        debug_config = {'prepare': 'none', 'cleanup': '是', 'step_mode': 'all'}
        selected_entries = [{'type': 'scenario', 'case_id': 'tc001', 'scenario_id': 's1'}]

        executed_steps = []

        def mock_run_steps(steps, phase):
            for s in steps:
                if s.get('action'):
                    executed_steps.append(('run_steps', phase, s['action']))

        def mock_execute_step_list(steps, phase):
            for s in steps:
                if s.get('action'):
                    executed_steps.append(('step_list', phase, s['action']))

        executor._run_steps = mock_run_steps
        executor._execute_step_list = mock_execute_step_list

        result = executor._execute_debug_case(case, 'scenario_debug', debug_config, selected_entries)

        assert result['status'] == 'PASS'
        # post_process executed
        assert ('run_steps', '后处理', 'close') in executed_steps


class TestStepDebugModeOnly:
    """step_debug step_mode=only: executes only the specified step."""

    def test_executes_only_target_step(self, executor):
        steps = [
            _make_step('click', 'btn1'),
            _make_step('type', 'input1', 'hello'),
            _make_step('click', 'btn2'),
        ]
        scenario = _make_scenario('s1', steps)
        case = _make_case(scenarios=[scenario])

        debug_config = {'prepare': 'none', 'cleanup': '否', 'step_mode': 'only'}
        selected_entries = [{'type': 'step', 'case_id': 'tc001', 'scenario_id': 's1', 'step_no': 2}]

        executed_steps = []

        def mock_run_steps(steps_list, phase):
            for s in steps_list:
                if s.get('action'):
                    executed_steps.append(('run_steps', phase, s['action'], s.get('data', '')))

        def mock_execute_step_list(steps_list, phase):
            for s in steps_list:
                if s.get('action'):
                    executed_steps.append(('step_list', phase, s['action'], s.get('data', '')))

        executor._run_steps = mock_run_steps
        executor._execute_step_list = mock_execute_step_list

        result = executor._execute_debug_case(case, 'step_debug', debug_config, selected_entries)

        assert result['status'] == 'PASS'
        # Only step 2 (type, input1, hello) should be executed
        step_list_entries = [(a, d) for method, phase, a, d in executed_steps if method == 'step_list']
        assert len(step_list_entries) == 1
        assert step_list_entries[0] == ('type', 'hello')


class TestStepDebugModeFrom:
    """step_debug step_mode=from: executes from specified step to end."""

    def test_executes_from_step_to_end(self, executor):
        steps = [
            _make_step('click', 'btn1'),
            _make_step('type', 'input1', 'hello'),
            _make_step('click', 'btn2'),
            _make_step('click', 'btn3'),
        ]
        scenario = _make_scenario('s1', steps)
        case = _make_case(scenarios=[scenario])

        debug_config = {'prepare': 'none', 'cleanup': '否', 'step_mode': 'from'}
        selected_entries = [{'type': 'step', 'case_id': 'tc001', 'scenario_id': 's1', 'step_no': 2}]

        executed_steps = []

        def mock_run_steps(steps_list, phase):
            for s in steps_list:
                if s.get('action'):
                    executed_steps.append(('run_steps', phase, s['action']))

        def mock_execute_step_list(steps_list, phase):
            for s in steps_list:
                if s.get('action'):
                    executed_steps.append(('step_list', phase, s['action']))

        executor._run_steps = mock_run_steps
        executor._execute_step_list = mock_execute_step_list

        result = executor._execute_debug_case(case, 'step_debug', debug_config, selected_entries)

        assert result['status'] == 'PASS'
        # Steps 2, 3, 4 should be executed (from step 2 to end)
        step_list_entries = [a for method, phase, a in executed_steps if method == 'step_list']
        assert step_list_entries == ['type', 'click', 'click']


class TestStepDebugPrepareAutoWithPrecedingSteps:
    """step_debug prepare=auto: executes pre_process + preceding steps + target step."""

    def test_executes_pre_process_and_preceding_steps(self, executor):
        pre_steps = [_make_step('open', 'browser', 'http://example.com')]
        steps = [
            _make_step('click', 'btn1'),
            _make_step('type', 'input1', 'hello'),
            _make_step('click', 'btn_target'),
        ]
        scenario = _make_scenario('s1', steps)
        case = _make_case(pre_steps=pre_steps, scenarios=[scenario])

        debug_config = {'prepare': 'auto', 'cleanup': '否', 'step_mode': 'only'}
        selected_entries = [{'type': 'step', 'case_id': 'tc001', 'scenario_id': 's1', 'step_no': 3}]

        executed_steps = []

        def mock_run_steps(steps_list, phase):
            for s in steps_list:
                if s.get('action'):
                    executed_steps.append(('run_steps', phase, s['action']))

        def mock_execute_step_list(steps_list, phase):
            for s in steps_list:
                if s.get('action'):
                    executed_steps.append(('step_list', phase, s['action']))

        executor._run_steps = mock_run_steps
        executor._execute_step_list = mock_execute_step_list

        result = executor._execute_debug_case(case, 'step_debug', debug_config, selected_entries)

        assert result['status'] == 'PASS'
        # pre_process executed
        assert ('run_steps', '预处理', 'open') in executed_steps
        # preceding steps (step 1 and 2) + target step (step 3) executed
        step_list_entries = [a for method, phase, a in executed_steps if method == 'step_list']
        # prepare=auto executes steps before target (click, type) then target (click btn_target)
        assert step_list_entries == ['click', 'type', 'click']
