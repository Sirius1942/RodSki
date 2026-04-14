"""Execution graph unit tests."""
from __future__ import annotations

import pytest
from rodski_agent.execution.graph import SimpleGraph, build_execution_graph, HAS_LANGGRAPH


class TestSimpleGraph:
    def test_sequential_execution(self):
        """Nodes run in order, each updating state."""
        def n1(s): return {"a": 1}
        def n2(s): return {"b": s["a"] + 1}
        g = SimpleGraph(nodes=[("n1", n1), ("n2", n2)])
        result = g.invoke({})
        assert result == {"a": 1, "b": 2}

    def test_exception_sets_error_status(self):
        """Node exception -> status=error and stops."""
        def n1(s): raise ValueError("boom")
        def n2(s): return {"unreachable": True}
        g = SimpleGraph(nodes=[("n1", n1), ("n2", n2)])
        result = g.invoke({})
        assert result["status"] == "error"
        assert "boom" in result["error"]
        assert "unreachable" not in result

    def test_conditional_edge_skip(self):
        """Conditional edge can skip nodes."""
        def n1(s): return {"status": "error"}
        def n2(s): return {"skipped": False}  # should not run
        def n3(s): return {"reached": True}
        g = SimpleGraph(
            nodes=[("n1", n1), ("n2", n2), ("n3", n3)],
            conditional_edges={
                "n1": (lambda s: "n3" if s.get("status") == "error" else "n2",
                       {"n2": "n2", "n3": "n3"})
            }
        )
        result = g.invoke({})
        assert result.get("reached") is True
        assert "skipped" not in result

    def test_conditional_edge_end(self):
        """Conditional edge to __end__ stops execution."""
        def n1(s): return {"done": True}
        def n2(s): return {"unreachable": True}
        g = SimpleGraph(
            nodes=[("n1", n1), ("n2", n2)],
            conditional_edges={
                "n1": (lambda s: "end", {"end": "__end__"})
            }
        )
        result = g.invoke({"done": False})
        assert result["done"] is True
        assert "unreachable" not in result


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

    def test_uses_simple_graph_backend(self):
        """Since langgraph is not installed, should use SimpleGraph."""
        assert HAS_LANGGRAPH is False
