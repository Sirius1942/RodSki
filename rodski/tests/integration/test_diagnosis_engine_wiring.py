"""DiagnosisEngine 接入集成测试（v8.2.0 Hooks 机制 WI-60-08）

覆盖：
  - diagnosis_engine 配置后，case 失败时 diagnose() 被调用，
    结果通过 report_collector.record_diagnosis() 写入 CaseReport.case_diagnosis
  - diagnosis_engine=None（默认）时行为与现状完全一致（不调用 diagnose，不报错）
"""
from unittest.mock import MagicMock

import pytest

from core.ski_executor import SKIExecutor
from core.diagnosis_engine import DiagnosisEngine, DiagnosisReport
from report.collector import ReportCollector


def _build_executor_with_report_collector(diagnosis_engine=None):
    """复用 test_ski_executor.py::TestExecuteCase 的最小 mock 构造模式，
    额外接入真实的 ReportCollector（而非 mock），验证端到端写入。
    """
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
    executor._hooks = {}
    executor._diagnosis_engine = diagnosis_engine

    collector = ReportCollector()
    collector.start_run()
    collector.start_case({"case_id": "c001", "title": "必然失败用例"})
    executor.report_collector = collector
    return executor, collector


def _make_failing_case():
    return {
        "case_id": "c001",
        "title": "必然失败用例",
        "pre_process": [],
        "test_case": [{"action": "wait", "model": "", "data": "0"}],
        "post_process": [],
    }


def test_diagnosis_engine_wired_writes_recovery_action_to_report():
    diagnosis_engine = DiagnosisEngine()  # 无 ai_verifier/llm_client，纯规则匹配
    executor, collector = _build_executor_with_report_collector(diagnosis_engine)

    def failing_run_steps(steps, label):
        if label == "用例":
            raise TimeoutError("步骤超时")  # core.exceptions.TimeoutError，命中 ERROR_ACTION_MAP

    executor._run_steps = failing_run_steps
    result = executor.execute_case(_make_failing_case())

    assert result["status"] == "FAIL"
    assert collector._current_case.case_diagnosis is not None
    assert "recovery_action" in collector._current_case.case_diagnosis
    assert collector._current_case.case_diagnosis["recovery_action"]["action"] == "refresh"


def test_diagnosis_engine_none_does_not_touch_report():
    """diagnosis_engine=None（默认）时不应调用 diagnose，case_diagnosis 保持 None（回归）。"""
    executor, collector = _build_executor_with_report_collector(diagnosis_engine=None)

    def failing_run_steps(steps, label):
        if label == "用例":
            raise RuntimeError("boom")

    executor._run_steps = failing_run_steps
    result = executor.execute_case(_make_failing_case())

    assert result["status"] == "FAIL"
    assert collector._current_case.case_diagnosis is None
