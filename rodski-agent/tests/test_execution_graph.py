"""Execution graph unit tests."""
from __future__ import annotations

import pytest
from rodski_agent.execution.graph import build_execution_graph


class TestBuildExecutionGraph:
    def test_happy_path_with_mocks(self):
        """Full graph with mock nodes: pre_check -> execute -> parse_result -> report."""
        def mock_pre_check(s): return {"status": "running"}
        def mock_execute(s): return {"execution_result": {"exit_code": 0}}
        def mock_parse_result(s): return {"case_results": [{"id": "c001", "status": "PASS", "time": 1.0}]}
        def mock_diagnose(s): return {"diagnosis": {"skipped": True}}
        def mock_report(s):
            cases = s.get("case_results", [])
            passed = sum(1 for c in cases if c["status"] == "PASS")
            return {"report": {"total": len(cases), "passed": passed, "failed": 0}, "status": "pass"}

        g = build_execution_graph(mock_pre_check, mock_execute, mock_parse_result, mock_diagnose, mock_report)
        result = g.invoke({"case_path": "/fake", "headless": True})
        assert result["status"] == "pass"
        assert result["report"]["total"] == 1

    def test_pre_check_error_skips_to_report(self):
        """When pre_check sets error, execute is skipped."""
        call_log = []
        def mock_pre_check(s):
            call_log.append("pre_check")
            return {"status": "error", "error": "not found"}
        def mock_execute(s):
            call_log.append("execute")
            return {}
        def mock_parse_result(s):
            call_log.append("parse_result")
            return {}
        def mock_diagnose(s):
            call_log.append("diagnose")
            return {}
        def mock_report(s):
            call_log.append("report")
            return {"report": {"total": 0}, "status": "error"}

        g = build_execution_graph(mock_pre_check, mock_execute, mock_parse_result, mock_diagnose, mock_report)
        result = g.invoke({"case_path": "/bad"})
        assert "pre_check" in call_log
        assert "report" in call_log
        assert "execute" not in call_log

    def test_failure_triggers_diagnose(self):
        """When parse_result has failures, diagnose is called."""
        call_log = []
        def mock_pre_check(s): return {"status": "running"}
        def mock_execute(s): return {"execution_result": {"exit_code": 1}}
        def mock_parse_result(s):
            call_log.append("parse_result")
            return {"case_results": [{"id": "c001", "status": "FAIL"}]}
        def mock_diagnose(s):
            call_log.append("diagnose")
            return {"diagnosis": {"category": "CASE_DEFECT"}}
        def mock_retry_decide(s):
            call_log.append("retry_decide")
            return {"retry_decision": "give_up"}
        def mock_report(s):
            call_log.append("report")
            return {"status": "fail"}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report, mock_retry_decide,
        )
        result = g.invoke({"case_path": "/test"})
        assert "diagnose" in call_log
        assert "retry_decide" in call_log
        assert result["status"] == "fail"
