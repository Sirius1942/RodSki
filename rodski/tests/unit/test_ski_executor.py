"""SKIExecutor 单元测试

测试 core/ski_executor.py 中的 SKI 测试执行引擎。
覆盖：resolve_module_dir（路径推导）、初始化、
      execute_case（三阶段执行：成功/失败/后处理/expect_fail）、
      _ensure_driver_alive（驱动重建）、execute_step（基本流程）。
所有驱动/解析器调用均通过 mock 隔离，不执行真实测试。
"""
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from core.ski_executor import resolve_module_dir, SKIExecutor
from core.exceptions import AssertionFailedError


# =====================================================================
# resolve_module_dir —— 从 case 路径推导测试模块目录
# =====================================================================
class TestResolveModuleDir:
    """resolve_module_dir —— 路径推导逻辑"""

    def test_file_path(self, tmp_path):
        """case 文件路径应推导为 parent.parent"""
        # 模拟 module_dir/case/test.xml 结构
        case_dir = tmp_path / "my_module" / "case"
        case_dir.mkdir(parents=True)
        case_file = case_dir / "test.xml"
        case_file.touch()
        result = resolve_module_dir(case_file)
        assert result == tmp_path / "my_module"

    def test_case_directory(self, tmp_path):
        """case/ 目录路径应推导为 parent"""
        case_dir = tmp_path / "my_module" / "case"
        case_dir.mkdir(parents=True)
        result = resolve_module_dir(case_dir)
        assert result == tmp_path / "my_module"

    def test_other_directory(self, tmp_path):
        """非 case/ 目录应原样返回"""
        other_dir = tmp_path / "random_dir"
        other_dir.mkdir()
        result = resolve_module_dir(other_dir)
        assert result == other_dir


# =====================================================================
# SKIExecutor 初始化（通过 mock 隔离文件系统）
# =====================================================================
class TestSKIExecutorInit:
    """SKIExecutor 初始化参数和目录推导"""

    @pytest.fixture
    def module_dir(self, tmp_path):
        """创建标准测试模块目录结构"""
        mod = tmp_path / "test_module"
        (mod / "case").mkdir(parents=True)
        (mod / "model").mkdir()
        (mod / "data").mkdir()
        (mod / "fun").mkdir()
        (mod / "result").mkdir()

        # 创建最小化的文件
        (mod / "model" / "model.xml").write_text(
            '<?xml version="1.0"?><models></models>', encoding="utf-8"
        )
        (mod / "data" / "globalvalue.xml").write_text(
            '<?xml version="1.0"?><globalvalue></globalvalue>', encoding="utf-8"
        )
        # 创建 case 文件
        (mod / "case" / "test.xml").write_text(
            '<?xml version="1.0"?><cases></cases>', encoding="utf-8"
        )
        return mod

    def test_module_dir_auto_resolved(self, module_dir):
        """module_dir 应从 case_path 自动推导"""
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
            mock_dr.return_value = MagicMock()
            mock_rw.return_value = MagicMock()

            executor = SKIExecutor(
                case_path=str(case_file),
                driver=driver,
            )
            assert executor.module_dir == module_dir.resolve()

    def test_explicit_module_dir(self, module_dir):
        """显式传入 module_dir 时应使用该路径"""
        case_file = module_dir / "case" / "test.xml"
        driver = MagicMock()
        custom_dir = module_dir.parent / "custom"
        custom_dir.mkdir()

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
            mock_dr.return_value = MagicMock()
            mock_rw.return_value = MagicMock()

            executor = SKIExecutor(
                case_path=str(case_file),
                driver=driver,
                module_dir=str(custom_dir),
            )
            assert executor.module_dir == custom_dir.resolve()


# =====================================================================
# execute_case —— 三阶段执行
# =====================================================================
class TestExecuteCase:
    """execute_case —— 用例三阶段执行逻辑"""

    @pytest.fixture
    def executor(self):
        """创建一个高度 mock 化的 SKIExecutor"""
        # 直接构造对象，绕过 __init__
        executor = object.__new__(SKIExecutor)
        executor.driver = MagicMock()
        executor._driver_closed = False
        executor.driver_factory = None
        executor.auto_screenshot = False
        executor.auto_screenshot_on_step = False
        executor.keyword_engine = MagicMock()
        executor.keyword_engine._context = MagicMock()
        executor.keyword_engine._context.history = []
        executor.keyword_engine._context.named = {}
        executor.data_resolver = MagicMock()
        executor.data_resolver.resolve.side_effect = lambda v: v
        executor.dynamic_executor = MagicMock()
        executor.result_writer = MagicMock()
        executor.result_writer.current_run_dir = None
        executor.runtime_control = MagicMock()
        executor.runtime_control.drain_at_boundary = MagicMock()
        executor.runtime_control.wait_unpaused = MagicMock(return_value=True)
        executor.model_parser = None
        executor.data_manager = MagicMock()
        executor.data_manager.tables = {}
        executor.default_wait_time = 0.0
        executor._current_case_step_wait = None
        executor._runtime_stopped_graceful = False
        executor._current_case_steps_log = []
        executor._step_index = 0
        executor._current_case_id = ""
        executor._phase_runtime_seq = 0
        executor.config = MagicMock()
        return executor

    def test_all_phases_pass(self, executor):
        """所有阶段成功时应返回 PASS"""
        case = {
            "case_id": "c001",
            "title": "成功用例",
            "pre_process": [],
            "test_case": [],
            "post_process": [],
        }
        result = executor.execute_case(case)
        assert result["status"] == "PASS"
        assert result["case_id"] == "c001"
        assert "execution_time" in result

    def test_test_phase_fail(self, executor):
        """用例阶段失败时应返回 FAIL 且仍执行后处理"""
        post_executed = {"called": False}

        original_run_steps = executor._run_steps

        def mock_run_steps(steps, label):
            if label == "用例":
                raise RuntimeError("某步骤失败")
            elif label == "后处理":
                post_executed["called"] = True

        executor._run_steps = mock_run_steps

        case = {
            "case_id": "c002",
            "title": "失败用例",
            "pre_process": [],
            "test_case": [{"action": "type", "model": "", "data": "test"}],
            "post_process": [{"action": "close", "model": "", "data": ""}],
        }
        result = executor.execute_case(case)
        assert result["status"] == "FAIL"
        assert "某步骤失败" in result["error"]
        assert post_executed["called"] is True  # 后处理仍被执行

    def test_pre_process_fail_skips_test(self, executor):
        """预处理失败时应跳过用例阶段但仍执行后处理"""
        test_executed = {"called": False}
        post_executed = {"called": False}

        def mock_run_steps(steps, label):
            if label == "预处理":
                raise RuntimeError("预处理错误")
            elif label == "用例":
                test_executed["called"] = True
            elif label == "后处理":
                post_executed["called"] = True

        executor._run_steps = mock_run_steps

        case = {
            "case_id": "c003",
            "title": "预处理失败",
            "pre_process": [{"action": "navigate", "model": "", "data": ""}],
            "test_case": [{"action": "type", "model": "", "data": ""}],
            "post_process": [{"action": "close", "model": "", "data": ""}],
        }
        result = executor.execute_case(case)
        assert result["status"] == "FAIL"
        assert test_executed["called"] is False  # 用例阶段被跳过
        assert post_executed["called"] is True   # 后处理仍执行

    def test_expect_fail_actual_fail(self, executor):
        """expect_fail='是' 且实际失败时应标记为 PASS"""
        def mock_run_steps(steps, label):
            if label == "用例":
                raise RuntimeError("预期中的失败")

        executor._run_steps = mock_run_steps

        case = {
            "case_id": "c004",
            "title": "预期失败用例",
            "expect_fail": "是",
            "pre_process": [],
            "test_case": [{"action": "verify", "model": "", "data": "不存在的文字"}],
            "post_process": [],
        }
        result = executor.execute_case(case)
        assert result["status"] == "PASS"
        assert "预期失败" in result["error"]

    def test_expect_fail_actual_pass(self, executor):
        """expect_fail='是' 且实际成功时应标记为 FAIL"""
        executor._run_steps = lambda steps, label: None  # 所有阶段成功

        case = {
            "case_id": "c005",
            "title": "应失败但成功",
            "expect_fail": "是",
            "pre_process": [],
            "test_case": [],
            "post_process": [],
        }
        result = executor.execute_case(case)
        assert result["status"] == "FAIL"
        assert "预期失败但实际成功" in result["error"]

    def test_execution_time_recorded(self, executor):
        """执行时间应被记录"""
        executor._run_steps = lambda steps, label: None

        case = {
            "case_id": "c006",
            "title": "计时用例",
            "pre_process": [],
            "test_case": [],
            "post_process": [],
        }
        result = executor.execute_case(case)
        assert result["execution_time"] >= 0


# =====================================================================
# _ensure_driver_alive
# =====================================================================
class TestEnsureDriverAlive:
    """_ensure_driver_alive —— 驱动关闭后重建"""

    def test_driver_alive_noop(self):
        """驱动未关闭时不做任何操作"""
        executor = object.__new__(SKIExecutor)
        executor._driver_closed = False
        executor.driver = MagicMock()
        # 不应抛异常
        executor._ensure_driver_alive()

    def test_driver_closed_with_factory(self):
        """驱动已关闭且有 factory 时应重建"""
        executor = object.__new__(SKIExecutor)
        executor._driver_closed = True
        executor.driver = MagicMock()
        executor.driver_factory = MagicMock(return_value=MagicMock())
        executor.data_dir = Path("/tmp")
        executor.model_parser = None
        executor.data_manager = MagicMock()
        executor.global_vars = {}
        executor.case_path = Path("/tmp/test.xml")
        executor.module_dir = Path("/tmp")
        executor.data_resolver = MagicMock()

        with patch("core.ski_executor.KeywordEngine") as mock_ke:
            mock_ke.return_value = MagicMock()
            mock_ke.return_value.get_return = MagicMock()
            executor._ensure_driver_alive()

        assert executor._driver_closed is False
        executor.driver_factory.assert_called_once()

    def test_driver_closed_no_factory_raises(self):
        """驱动已关闭且无 factory 时应抛 DriverStoppedError"""
        from core.exceptions import DriverStoppedError

        executor = object.__new__(SKIExecutor)
        executor._driver_closed = True
        executor.driver_factory = None

        with pytest.raises(DriverStoppedError):
            executor._ensure_driver_alive()


# =====================================================================
# close —— 资源清理
# =====================================================================
class TestClose:
    """close —— 资源释放"""

    def test_close_cleans_resources(self):
        """close 应关闭所有解析器和连接"""
        executor = object.__new__(SKIExecutor)
        executor.case_parser = MagicMock()
        executor.data_manager = MagicMock()
        executor.global_parser = MagicMock()
        executor.keyword_engine = MagicMock()
        executor.keyword_engine._db_connections = {"mysql": MagicMock()}
        executor._driver_closed = False
        executor.driver = MagicMock()

        executor.close()

        executor.case_parser.close.assert_called_once()
        executor.data_manager.close.assert_called_once()
        executor.global_parser.close.assert_called_once()
        executor.driver.close.assert_called_once()

    def test_close_skips_closed_driver(self):
        """驱动已关闭时不再尝试关闭"""
        executor = object.__new__(SKIExecutor)
        executor.case_parser = MagicMock()
        executor.data_manager = MagicMock()
        executor.global_parser = MagicMock()
        executor.keyword_engine = MagicMock()
        executor.keyword_engine._db_connections = {}
        executor._driver_closed = True
        executor.driver = MagicMock()

        executor.close()

        executor.driver.close.assert_not_called()



# =====================================================================
# execute_step —— 步骤执行与失败记录
# =====================================================================
class TestExecuteStep:
    """execute_step —— verify 失败应记录为 fail 并抛出异常"""

    @pytest.fixture
    def executor(self):
        executor = object.__new__(SKIExecutor)
        executor.driver = MagicMock()
        executor._driver_closed = False
        executor.auto_screenshot_on_step = False
        executor.default_wait_time = 0.0
        executor._current_case_step_wait = None
        executor._current_case_steps_log = []
        executor.data_resolver = MagicMock()
        executor.data_resolver.resolve.side_effect = lambda v: v
        executor.keyword_engine = MagicMock()
        executor.keyword_engine._context = MagicMock()
        executor.keyword_engine._context.history = []
        executor.keyword_engine._context.named = {}
        executor.report_collector = MagicMock()
        executor.model_parser = None
        return executor

    def test_verify_failure_marks_step_fail_and_records_report(self, executor):
        failure_payload = {
            'amount': '20元',
            'passed': False,
            '_verify_passed': False,
            '_verify_mismatches': [
                {'element': 'amount', 'expected': '10元', 'actual': '20元'}
            ],
        }

        def raise_assertion(*args, **kwargs):
            executor.keyword_engine._context.history.append(failure_payload)
            raise AssertionFailedError('批量验证失败: amount(期望=10元, 实际=20元)')

        executor.keyword_engine.execute.side_effect = raise_assertion

        with pytest.raises(AssertionFailedError):
            executor.execute_step({'action': 'verify', 'model': 'Order', 'data': 'V001'}, '用例')

        assert len(executor._current_case_steps_log) == 1
        step_log = executor._current_case_steps_log[0]
        assert step_log['status'] == 'fail'
        assert step_log['return_value'] == failure_payload
        assert '批量验证失败' in step_log['error']

        executor.report_collector.record_step.assert_called_once()
        report_step = executor.report_collector.record_step.call_args.args[0]
        assert report_step['status'] == 'fail'
        assert report_step['return_value'] == failure_payload


# =====================================================================
# pre_process / post_process 失败场景
# =====================================================================
class TestPrePostProcessFailure:
    """pre_process/post_process 失败时的行为验证"""

    @pytest.fixture
    def executor(self):
        executor = object.__new__(SKIExecutor)
        executor.driver = MagicMock()
        executor._driver_closed = False
        executor.driver_factory = None
        executor.auto_screenshot = False
        executor.auto_screenshot_on_step = False
        executor.keyword_engine = MagicMock()
        executor.keyword_engine._context = MagicMock()
        executor.keyword_engine._context.history = []
        executor.keyword_engine._context.named = {}
        executor.data_resolver = MagicMock()
        executor.data_resolver.resolve.side_effect = lambda v: v
        executor.dynamic_executor = MagicMock()
        executor.result_writer = MagicMock()
        executor.result_writer.current_run_dir = None
        executor.runtime_control = MagicMock()
        executor.runtime_control.drain_at_boundary = MagicMock()
        executor.runtime_control.wait_unpaused = MagicMock(return_value=True)
        executor.model_parser = None
        executor.data_manager = MagicMock()
        executor.data_manager.tables = {}
        executor.default_wait_time = 0.0
        executor._current_case_step_wait = None
        executor._runtime_stopped_graceful = False
        executor._current_case_steps_log = []
        executor._step_index = 0
        executor._current_case_id = ""
        executor._phase_runtime_seq = 0
        executor.config = MagicMock()
        executor.report_collector = None
        return executor

    def _make_case(self, pre_steps=None, test_steps=None, post_steps=None):
        return {
            'case_id': 'c001',
            'title': 'test',
            'expect_fail': '否',
            'component_type': '界面',
            'step_wait': None,
            'pre_process': pre_steps or [],
            'test_case': test_steps or [{'action': 'click', 'model': 'M', 'data': ''}],
            'post_process': post_steps or [],
        }

    def test_pre_process_failure_skips_test_case(self, executor):
        """pre_process 失败时 test_case 步骤不被调用"""
        call_log = []

        def run_steps(steps, phase):
            call_log.append(phase)
            if phase == '预处理':
                raise RuntimeError('pre_process failed')

        executor._run_steps = run_steps
        executor._snapshot_runtime_resources = MagicMock(return_value={})
        executor._case_result_force_terminated = MagicMock()

        result = executor.execute_case(self._make_case(
            pre_steps=[{'action': 'open', 'model': '', 'data': ''}],
        ))

        assert '用例' not in call_log
        assert result['status'] == 'FAIL'

    def test_pre_process_failure_still_runs_post_process(self, executor):
        """pre_process 失败时 post_process 仍执行"""
        call_log = []

        def run_steps(steps, phase):
            call_log.append(phase)
            if phase == '预处理':
                raise RuntimeError('pre_process failed')

        executor._run_steps = run_steps
        executor._snapshot_runtime_resources = MagicMock(return_value={})
        executor._case_result_force_terminated = MagicMock()

        executor.execute_case(self._make_case(
            pre_steps=[{'action': 'open', 'model': '', 'data': ''}],
            post_steps=[{'action': 'close', 'model': '', 'data': ''}],
        ))

        assert '后处理' in call_log

    def test_post_process_failure_marks_case_fail(self, executor):
        """post_process 失败时用例状态为 FAIL"""
        def run_steps(steps, phase):
            if phase == '后处理':
                raise RuntimeError('post_process failed')

        executor._run_steps = run_steps
        executor._snapshot_runtime_resources = MagicMock(return_value={})
        executor._case_result_force_terminated = MagicMock()

        result = executor.execute_case(self._make_case(
            post_steps=[{'action': 'close', 'model': '', 'data': ''}],
        ))

        assert result['status'] == 'FAIL'
