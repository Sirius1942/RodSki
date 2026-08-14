"""SKIExecutor(hooks=...) 构造参数测试（v8.2.0 Hooks 机制）

覆盖：
  - hooks=None（默认，行为与迭代前完全一致）
  - hooks={"before_keyword": [...], "after_keyword": [...]} 正确接线到 KeywordEngine
  - on_case_failure 挂载点在 case 失败时被调用
  - diagnosis_engine 配置后 diagnose() 被调用且结果写入 report_collector
"""
from unittest.mock import MagicMock, patch

import pytest

from core.ski_executor import SKIExecutor


class TestSKIExecutorHooksConstruction:
    """hooks= 构造参数接线到 KeywordEngine"""

    @pytest.fixture
    def module_dir(self, tmp_path):
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

    def _build_executor(self, module_dir, **kwargs):
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
            ke_instance = MagicMock()
            ke_instance._context = MagicMock()
            ke_instance._context.history = []
            ke_instance._context.named = {}
            mock_ke.return_value = ke_instance
            mock_dr.return_value = MagicMock()
            mock_rw.return_value = MagicMock()

            executor = SKIExecutor(
                case_path=str(case_file),
                driver=driver,
                **kwargs,
            )
            return executor, ke_instance

    def test_hooks_none_default_behavior_unchanged(self, module_dir):
        """hooks=None（未传）时，_hooks 为空字典，keyword_engine 的 hook 列表为空。"""
        executor, ke_instance = self._build_executor(module_dir)
        assert executor._hooks == {}
        assert ke_instance.before_keyword_hooks == []
        assert ke_instance.after_keyword_hooks == []
        assert executor._diagnosis_engine is None

    def test_hooks_before_after_keyword_wired(self, module_dir):
        before_hook = MagicMock()
        after_hook = MagicMock()
        executor, ke_instance = self._build_executor(
            module_dir,
            hooks={"before_keyword": [before_hook], "after_keyword": [after_hook]},
        )
        assert ke_instance.before_keyword_hooks == [before_hook]
        assert ke_instance.after_keyword_hooks == [after_hook]

    def test_hooks_missing_keys_default_to_empty(self, module_dir):
        """hooks 字典中未提供的事件键，对应回调列表应为空列表而非 None/报错。"""
        executor, ke_instance = self._build_executor(
            module_dir,
            hooks={"on_case_failure": [MagicMock()]},
        )
        assert ke_instance.before_keyword_hooks == []
        assert ke_instance.after_keyword_hooks == []
        assert len(executor._hooks.get("on_case_failure", [])) == 1


class TestHooksSurviveDriverRecreation:
    def test_recreated_keyword_engine_receives_before_and_after_hooks(self):
        executor = object.__new__(SKIExecutor)
        before_hook = MagicMock()
        after_hook = MagicMock()
        executor._hooks = {
            "before_keyword": [before_hook],
            "after_keyword": [after_hook],
        }
        executor._driver_closed = True
        executor.driver_factory = MagicMock(return_value=MagicMock())
        executor.data_dir = MagicMock()
        executor.model_parser = MagicMock()
        executor.data_manager = MagicMock()
        executor.global_vars = {}
        executor.case_path = MagicMock()
        executor.module_dir = MagicMock()
        executor.data_resolver = MagicMock()
        executor._tracer = None
        executor._current_recording_path = None

        with patch("core.ski_executor.KeywordEngine") as keyword_engine_cls:
            recreated = keyword_engine_cls.return_value
            executor._ensure_driver_alive()

        assert recreated.before_keyword_hooks == [before_hook]
        assert recreated.after_keyword_hooks == [after_hook]


class TestOnCaseFailureMountPoint:
    """execute_case 内 on_case_failure 挂载点：进程内回调 + DiagnosisEngine 接入"""

    @pytest.fixture
    def executor(self):
        """复用 test_ski_executor.py::TestExecuteCase 的最小 mock 构造模式。"""
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
        executor._current_case_scenario_statuses = []
        executor._step_index = 0
        executor._current_case_id = ""
        executor._phase_runtime_seq = 0
        executor.config = MagicMock()
        return executor

    def _make_failing_case(self):
        return {
            "case_id": "c001",
            "title": "失败用例",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0"}],
            "post_process": [],
        }

    def test_on_case_failure_hook_called_with_case_error_screenshot(self, executor):
        hook = MagicMock()
        executor._hooks = {"on_case_failure": [hook]}
        executor._diagnosis_engine = None

        case = self._make_failing_case()

        def failing_run_steps(steps, label):
            if label == "用例":
                raise RuntimeError("boom")

        executor._run_steps = failing_run_steps
        result = executor.execute_case(case)

        assert result["status"] == "FAIL"
        hook.assert_called_once()
        call_args = hook.call_args[0]
        assert call_args[0]["case_id"] == "c001"
        assert isinstance(call_args[1], RuntimeError)

    def test_on_case_failure_hook_exception_does_not_break_execute_case(self, executor):
        def bad_hook(case, err, screenshot_path):
            raise RuntimeError("hook 自身故障")

        executor._hooks = {"on_case_failure": [bad_hook]}
        executor._diagnosis_engine = None

        case = self._make_failing_case()

        def failing_run_steps(steps, label):
            if label == "用例":
                raise RuntimeError("boom")

        executor._run_steps = failing_run_steps
        result = executor.execute_case(case)
        assert result["status"] == "FAIL"  # 未因 hook 异常而崩溃

    def test_diagnosis_engine_invoked_on_failure(self, executor):
        diag_report = MagicMock()
        diag_report.to_dict.return_value = {"root_cause": "x", "category": "CASE_DEFECT"}
        diag_engine = MagicMock()
        diag_engine.diagnose.return_value = diag_report

        report_collector = MagicMock()
        executor._hooks = {}
        executor._diagnosis_engine = diag_engine
        executor.report_collector = report_collector

        case = self._make_failing_case()

        def failing_run_steps(steps, label):
            if label == "用例":
                raise RuntimeError("boom")

        executor._run_steps = failing_run_steps
        result = executor.execute_case(case)

        assert result["status"] == "FAIL"
        assert result["case_diagnosis"] == {
            "root_cause": "x",
            "category": "CASE_DEFECT",
        }
        diag_engine.diagnose.assert_called_once()
        report_collector.record_diagnosis.assert_called_once_with(
            {"root_cause": "x", "category": "CASE_DEFECT"}
        )

    def test_diagnosis_engine_none_no_diagnose_call(self, executor):
        """diagnosis_engine=None（默认）时不应尝试诊断，行为与现状一致。"""
        executor._hooks = {}
        executor._diagnosis_engine = None

        case = self._make_failing_case()

        def failing_run_steps(steps, label):
            if label == "用例":
                raise RuntimeError("boom")

        executor._run_steps = failing_run_steps
        result = executor.execute_case(case)
        assert result["status"] == "FAIL"  # 无异常即通过

    def test_missing_hooks_attribute_falls_back_to_empty(self, executor):
        """未设置 _hooks/_diagnosis_engine 属性时（如旧测试用 object.__new__ 构造），
        getattr 兜底应保证不抛 AttributeError（回归保护）。"""
        case = self._make_failing_case()

        def failing_run_steps(steps, label):
            if label == "用例":
                raise RuntimeError("boom")

        executor._run_steps = failing_run_steps
        # 故意不设置 executor._hooks / executor._diagnosis_engine
        result = executor.execute_case(case)
        assert result["status"] == "FAIL"
