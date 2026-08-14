"""SKIExecutor 漫游阶段的同步执行和安全边界测试。"""

import pytest
from unittest.mock import MagicMock

from core.runtime_control import ForceRunTermination
from core.ski_executor import SKIExecutor


def _executor(tmp_path, *, hooks=None, max_variants=1):
    executor = object.__new__(SKIExecutor)
    executor.module_dir = tmp_path
    executor.global_vars = {
        "Roam": {
            "Enabled": "是",
            "MaxVariantsPerCase": str(max_variants),
            "MaxDurationSeconds": "10",
            "MinConfidenceToAct": "0.6",
            "MaxTokenBudget": "20000",
            "MaxCostUsd": "0.5",
        }
    }
    executor.data_manager = MagicMock()
    executor.data_manager.tables = {
        "Login": {
            "D001": {"username": "base"},
            "D002": {"username": "variant"},
        }
    }
    executor.model_parser = None
    executor._hooks = hooks or {}
    executor.roam_mode = "batch_just_passed"
    executor._run_steps = MagicMock()
    return executor


def test_roam_session_executes_data_variant_synchronously_and_writes_map(tmp_path):
    custom = MagicMock()
    custom.next_action.return_value = {
        "next_action": {"action": "type", "model": "Login", "data": "D002"},
        "confidence": 1.0,
        "reversible": True,
    }
    executor = _executor(
        tmp_path,
        hooks={"on_case_pass_roam_ready": [lambda context: custom]},
    )
    case = {
        "case_id": "c001",
        "title": "登录",
        "tags": ["smoke"],
        "test_case": [{"action": "type", "model": "Login", "data": "D001"}],
    }

    summary = executor._run_roam_session(case)

    executor._run_steps.assert_called_once_with(
        [{"action": "type", "model": "Login", "data": "D002"}], "漫游"
    )
    assert summary["base_case_id"] == "c001"
    assert summary["variants_tried"] == 1
    assert summary["stopped_reason"] == "budget_variants"
    assert summary["test_map_delta"]["written"] is True
    saved = (tmp_path / "knowledge" / "test_map.json").read_text(encoding="utf-8")
    assert "case:c001:data:Login:D002" in saved


def test_roam_hook_can_supply_custom_decision_engine(tmp_path):
    custom = MagicMock()
    custom.next_action.side_effect = [
        {
            "next_action": {"action": "wait", "model": "", "data": "0"},
            "confidence": 1.0,
            "reversible": True,
            "stop": False,
        },
        {"stop": True, "stopped_reason": "manual_stop"},
    ]
    executor = _executor(
        tmp_path,
        hooks={"on_case_pass_roam_ready": [lambda context: custom]},
        max_variants=5,
    )
    summary = executor._run_roam_session(
        {"case_id": "c002", "title": "自定义", "test_case": []}
    )

    executor._run_steps.assert_called_once_with(
        [{"action": "wait", "model": "", "data": "0"}], "漫游"
    )
    assert summary["stopped_reason"] == "manual_stop"
    assert custom.next_action.call_count == 2


def test_roam_action_failure_is_a_finding_and_does_not_raise(tmp_path):
    custom = MagicMock()
    custom.next_action.return_value = {
        "next_action": {"action": "type", "model": "Login", "data": "D002"},
        "confidence": 1.0,
        "reversible": True,
    }
    executor = _executor(
        tmp_path,
        hooks={"on_case_pass_roam_ready": [lambda context: custom]},
    )
    executor._run_steps.side_effect = RuntimeError("variant failed")
    summary = executor._run_roam_session(
        {
            "case_id": "c003",
            "title": "失败变体",
            "test_case": [{"action": "type", "model": "Login", "data": "D001"}],
        }
    )

    assert summary["stopped_reason"] == "manual_stop"
    assert summary["findings"][0]["base_case_id"] == "c003"
    assert summary["findings"][0]["category"] == "UNKNOWN"


def test_roam_dynamic_resources_are_restored_after_action(tmp_path):
    executor = _executor(tmp_path, max_variants=1)
    executor.model_parser = MagicMock()
    executor.model_parser.models = {"Base": {"field": {"value": "base"}}}
    executor.data_manager.tables = {"Login": {"D001": {"username": "base"}}}

    def merge_models(models):
        executor.model_parser.models.update(models)

    def merge_table(name, rows):
        executor.data_manager.tables.setdefault(name, {}).update(rows)

    executor.model_parser.merge_models.side_effect = merge_models
    executor.data_manager.merge_table.side_effect = merge_table
    observed = {}

    def run_steps(steps, phase):
        observed["models"] = set(executor.model_parser.models)
        observed["tables"] = set(executor.data_manager.tables)

    executor._run_steps.side_effect = run_steps
    custom = MagicMock()
    custom.next_action.side_effect = [
        {
            "next_action": {"action": "type", "model": "Temp", "data": "R1"},
            "confidence": 1.0,
            "reversible": True,
            "temp_models": {"Temp": {"field": {"value": "temporary"}}},
            "temp_tables": {"TempData": {"R1": {"value": "temporary"}}},
        },
        {"stop": True, "stopped_reason": "manual_stop"},
    ]
    executor._hooks = {"on_case_pass_roam_ready": [lambda context: custom]}

    summary = executor._run_roam_session(
        {"case_id": "c004", "title": "资源隔离", "test_case": []}
    )

    assert observed["models"] == {"Base", "Temp"}
    assert observed["tables"] == {"Login", "TempData"}
    assert set(executor.model_parser.models) == {"Base"}
    assert set(executor.data_manager.tables) == {"Login"}
    assert summary["variants_tried"] == 1


def test_roam_dynamic_resources_are_restored_on_force_terminate(tmp_path):
    executor = _executor(tmp_path, max_variants=1)
    executor.data_manager.tables = {"Login": {"D001": {"username": "base"}}}

    def merge_table(name, rows):
        executor.data_manager.tables.setdefault(name, {}).update(rows)

    executor.data_manager.merge_table.side_effect = merge_table
    executor._run_steps.side_effect = ForceRunTermination("stop now")
    custom = MagicMock()
    custom.next_action.return_value = {
        "next_action": {"action": "type", "model": "Login", "data": "D002"},
        "confidence": 1.0,
        "reversible": True,
        "temp_tables": {"Login": {"D002": {"username": "temporary"}}},
    }
    executor._hooks = {"on_case_pass_roam_ready": [lambda context: custom]}

    with pytest.raises(ForceRunTermination):
        executor._run_roam_session(
            {"case_id": "c004-force", "title": "资源强制恢复", "test_case": []}
        )

    assert executor.data_manager.tables == {
        "Login": {"D001": {"username": "base"}}
    }


def test_roam_rejects_unknown_dynamic_keyword_without_running_it(tmp_path):
    executor = _executor(tmp_path, max_variants=5)
    custom = MagicMock()
    custom.next_action.return_value = {
        "next_action": {"action": "not_a_keyword", "model": "", "data": ""},
        "confidence": 1.0,
        "reversible": True,
    }
    executor._hooks = {"on_case_pass_roam_ready": [lambda context: custom]}

    summary = executor._run_roam_session(
        {"case_id": "c005", "title": "非法动作", "test_case": []}
    )

    executor._run_steps.assert_not_called()
    assert summary["stopped_reason"] == "manual_stop"
    assert "漫游动作不支持关键字" in summary["findings"][0]["description"]


def test_roam_irreversible_action_is_record_only(tmp_path):
    executor = _executor(tmp_path, max_variants=5)
    custom = MagicMock()
    custom.next_action.side_effect = [
        {
            "next_action": {"action": "send", "model": "Api", "data": "DANGER"},
            "confidence": 1.0,
            "reversible": False,
        },
        {"stop": True, "stopped_reason": "manual_stop"},
    ]
    executor._hooks = {"on_case_pass_roam_ready": [lambda context: custom]}

    summary = executor._run_roam_session(
        {"case_id": "c006", "title": "不可逆动作", "test_case": []}
    )

    executor._run_steps.assert_not_called()
    assert summary["variants_tried"] == 0
    assert summary["stopped_reason"] == "manual_stop"


def _case_executor_for_phase_order(roam_session=None):
    executor = object.__new__(SKIExecutor)
    executor.driver = MagicMock()
    executor._driver_closed = False
    executor.auto_screenshot = False
    executor.keyword_engine = MagicMock()
    executor.keyword_engine._context = MagicMock()
    executor.keyword_engine._context.named = {}
    executor.data_manager = MagicMock()
    executor.data_manager.tables = {}
    executor.model_parser = None
    executor.result_writer = MagicMock()
    executor.result_writer.current_run_dir = None
    executor.runtime_control = MagicMock()
    executor.runtime_control.wait_unpaused.return_value = True
    executor.runtime_control.drain_at_boundary.return_value = None
    executor.global_vars = {"Roam": {"Enabled": "是"}}
    executor.roam_enabled = True
    executor.roam_mode = "batch_just_passed"
    executor._hooks = {}
    executor.report_collector = None
    executor._diagnosis_engine = None
    executor._start_case_recording = MagicMock(return_value="")
    executor._stop_case_recording = MagicMock(return_value="")
    executor._attach_recording_path = lambda result, path: result
    if roam_session is not None:
        executor._run_roam_session = MagicMock(return_value=roam_session)
    return executor


def test_execute_case_inserts_roam_between_test_and_post_process(tmp_path):
    order = []
    roam_summary = {
        "base_case_id": "c007",
        "variants_tried": 1,
        "stopped_reason": "manual_stop",
    }
    executor = _case_executor_for_phase_order(roam_summary)
    executor._run_roam_session.side_effect = lambda case: order.append("漫游") or roam_summary

    def run_steps(steps, label):
        order.append(label)

    executor._run_steps = run_steps
    result = executor.execute_case(
        {
            "case_id": "c007",
            "title": "阶段顺序",
            "roam": "是",
            "expect_fail": "否",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0"}],
            "post_process": [{"action": "close", "model": "", "data": ""}],
        }
    )

    assert order == ["预处理", "用例", "漫游", "后处理"]
    assert executor._run_roam_session.call_args.args[0]["case_id"] == "c007"
    assert "roam_summary" in result
    assert executor._run_roam_session.call_count == 1


def test_execute_case_failure_does_not_start_roaming(tmp_path):
    order = []
    executor = _case_executor_for_phase_order()

    def run_steps(steps, label):
        order.append(label)
        if label == "用例":
            raise RuntimeError("base test failed")

    executor._run_steps = run_steps
    executor._run_roam_session = MagicMock()
    result = executor.execute_case(
        {
            "case_id": "c008",
            "title": "基础失败",
            "roam": "是",
            "expect_fail": "否",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0"}],
            "post_process": [{"action": "close", "model": "", "data": ""}],
        }
    )

    assert result["status"] == "FAIL"
    assert order == ["预处理", "用例", "后处理"]
    executor._run_roam_session.assert_not_called()


def test_execute_case_expect_fail_does_not_start_roaming(tmp_path):
    executor = _case_executor_for_phase_order()
    executor._run_steps = MagicMock()
    executor._run_roam_session = MagicMock()
    result = executor.execute_case(
        {
            "case_id": "c009",
            "title": "预期失败",
            "roam": "是",
            "expect_fail": "是",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0"}],
            "post_process": [],
        }
    )

    assert result["status"] == "FAIL"
    executor._run_roam_session.assert_not_called()


def test_execute_case_converts_roam_force_terminate_to_case_result(tmp_path):
    order = []
    executor = _case_executor_for_phase_order()

    def run_steps(steps, label):
        order.append(label)

    executor._run_steps = run_steps
    executor._run_roam_session = MagicMock(
        side_effect=ForceRunTermination("runtime force_terminate")
    )
    result = executor.execute_case(
        {
            "case_id": "c010",
            "title": "漫游强制终止",
            "roam": "是",
            "expect_fail": "否",
            "pre_process": [],
            "test_case": [{"action": "wait", "model": "", "data": "0"}],
            "post_process": [{"action": "close", "model": "", "data": ""}],
        }
    )

    assert result["status"] == "FAIL"
    assert "force_terminate" in result["error"]
    assert order == ["预处理", "用例"]
