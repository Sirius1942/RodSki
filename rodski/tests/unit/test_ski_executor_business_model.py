"""Focused integration tests for Case-owned business_call execution."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

try:
    from core.business_model import BusinessModelError
    from core.ski_executor import SKIExecutor
except ImportError:  # Running from the repository root.
    from rodski.core.business_model import BusinessModelError
    from rodski.core.ski_executor import SKIExecutor


BUSINESS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<business_models version="0.1">
  <business_model id="demo_flow" name="Executor demo" version="1">
    <nodes>
      <node id="start" />
      <node id="request">
        <steps>
          <test_step action="send" data="${Business.InputDataID}" />
        </steps>
      </node>
      <node id="finish" />
    </nodes>
    <edges>
      <edge from="start" to="request" />
      <edge from="request" to="finish" />
    </edges>
    <flows>
      <flow id="F_OK" type="basic" path="start&gt;request&gt;finish" />
    </flows>
  </business_model>
</business_models>
"""


def _executor(tmp_path: Path, expected_path: str = "start>request>finish") -> SKIExecutor:
    (tmp_path / "business").mkdir()
    (tmp_path / "business" / "business.xml").write_text(BUSINESS_XML, encoding="utf-8")

    tables = {
        "demo_flow": {"D1": {"value": "input"}},
        "demo_flow_verify": {"V1": {"expected_path": expected_path}},
    }
    executor = object.__new__(SKIExecutor)
    executor.module_dir = tmp_path
    executor._business_models = None
    executor.data_manager = SimpleNamespace(tables=tables, _sqlite_source=None)
    executor.model_parser = None
    executor.keyword_engine = SimpleNamespace(_context=SimpleNamespace(history=[]))
    executor._current_case_steps_log = []

    def fake_execute_step(step, phase_label):
        assert step["action"] == "send"
        assert step["data"] == "D1"
        assert phase_label == "test_case"
        executor.keyword_engine._context.history.append({"status": "ok"})

    executor.execute_step = fake_execute_step
    return executor


def test_business_call_runs_inside_case_and_restores_data_view(tmp_path):
    executor = _executor(tmp_path)
    original_tables = executor.data_manager.tables

    executor._execute_business_call(
        {"id": "call-1", "ref": "demo_flow", "flow": "F_OK", "input": "D1", "expect": "V1"},
        "test_case",
    )

    assert executor.data_manager.tables is original_tables
    assert len(executor._current_case_steps_log) == 1
    record = executor._current_case_steps_log[0]
    assert record["action"] == "business_call"
    assert record["status"] == "ok"
    business_result = record["business_result"]
    assert business_result["passed"] is True
    assert business_result["actual_path"] == ["start", "request", "finish"]
    assert business_result["expected_path"] == ["start", "request", "finish"]


def test_business_call_records_failure_before_propagating_to_case(tmp_path):
    executor = _executor(tmp_path, expected_path="start>finish")
    original_tables = executor.data_manager.tables

    with pytest.raises(BusinessModelError, match="expected_path"):
        executor._execute_business_call(
            {"ref": "demo_flow", "flow": "F_OK", "input": "D1", "expect": "V1"},
            "test_case",
        )

    assert executor.data_manager.tables is original_tables
    assert executor._current_case_steps_log[0]["status"] == "fail"
    assert executor._current_case_steps_log[0]["business_result"]["passed"] is False
