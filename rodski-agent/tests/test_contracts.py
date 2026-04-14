"""AgentOutput / RunOutput / DesignOutput / DiagnoseOutput 契约测试。"""

from __future__ import annotations

import json

import pytest

from rodski_agent.common.contracts import (
    AgentOutput,
    DesignOutput,
    DiagnoseOutput,
    RunOutput,
)


class TestRunOutput:
    def test_to_dict_基础字段(self):
        ro = RunOutput(total=3, passed=2, failed=1, cases=[{"id": "c001", "status": "PASS"}])
        d = ro.to_dict()
        assert d["total"] == 3
        assert d["passed"] == 2
        assert d["failed"] == 1
        assert len(d["cases"]) == 1
        assert "diagnosis" not in d  # None 时应被删除

    def test_to_dict_带diagnosis(self):
        ro = RunOutput(total=1, passed=0, failed=1, diagnosis={"root_cause": "timeout"})
        d = ro.to_dict()
        assert d["diagnosis"] == {"root_cause": "timeout"}

    def test_defaults(self):
        ro = RunOutput()
        assert ro.total == 0
        assert ro.cases == []


class TestDesignOutput:
    def test_to_dict(self):
        do = DesignOutput(cases=["c1.xml"], models=["m1.xml"], data=["d1.xml"], summary="OK")
        d = do.to_dict()
        assert d["cases"] == ["c1.xml"]
        assert d["summary"] == "OK"


class TestDiagnoseOutput:
    def test_to_dict(self):
        diag = DiagnoseOutput(
            root_cause="Selector changed",
            confidence=0.85,
            category="PRODUCT_DEFECT",
            suggestion="Update locator",
            evidence=["screenshot.png"],
        )
        d = diag.to_dict()
        assert d["root_cause"] == "Selector changed"
        assert d["confidence"] == 0.85


class TestAgentOutput:
    def test_to_dict_省略None字段(self):
        ao = AgentOutput(status="success", command="run", output={"total": 1})
        d = ao.to_dict()
        assert "error" not in d
        assert "metadata" not in d

    def test_to_dict_包含error(self):
        ao = AgentOutput(status="error", command="run", error="something broke")
        d = ao.to_dict()
        assert d["error"] == "something broke"

    def test_to_dict_包含metadata(self):
        ao = AgentOutput(status="success", command="run", output={}, metadata={"version": "0.1.0"})
        d = ao.to_dict()
        assert d["metadata"]["version"] == "0.1.0"

    def test_to_json_输出合法JSON(self):
        ao = AgentOutput(status="success", command="run", output={"total": 2, "passed": 2, "failed": 0})
        j = ao.to_json()
        parsed = json.loads(j)
        assert parsed["status"] == "success"
        assert parsed["output"]["total"] == 2

    def test_to_json_中文不转义(self):
        ao = AgentOutput(status="error", command="run", error="路径不存在")
        j = ao.to_json()
        assert "路径不存在" in j  # ensure_ascii=False

    def test_to_human_error(self):
        ao = AgentOutput(status="error", command="run", error="File not found")
        text = ao.to_human()
        assert "Error" in text
        assert "File not found" in text

    def test_to_human_run_all_pass(self):
        ao = AgentOutput(status="success", command="run", output={"total": 3, "passed": 3, "failed": 0})
        text = ao.to_human()
        assert "3 case(s) passed" in text

    def test_to_human_run_partial(self):
        ao = AgentOutput(status="failure", command="run", output={"total": 5, "passed": 3, "failed": 2})
        text = ao.to_human()
        assert "3/5 passed" in text

    def test_to_human_run_all_fail(self):
        ao = AgentOutput(status="failure", command="run", output={"total": 2, "passed": 0, "failed": 2})
        text = ao.to_human()
        assert "2 case(s) failed" in text

    def test_to_human_design(self):
        ao = AgentOutput(status="success", command="design", output={"cases": ["a.xml", "b.xml"], "summary": "Done"})
        text = ao.to_human()
        assert "2 case(s)" in text
        assert "Done" in text

    def test_to_human_diagnose(self):
        ao = AgentOutput(
            status="success",
            command="diagnose",
            output={"root_cause": "element missing", "confidence": 0.9, "suggestion": "update selector"},
        )
        text = ao.to_human()
        assert "element missing" in text
        assert "90%" in text

    def test_to_human_fallback(self):
        ao = AgentOutput(status="success", command="pipeline", output={})
        text = ao.to_human()
        assert "pipeline" in text

    def test_roundtrip_serialization(self):
        """to_json -> json.loads -> 与 to_dict 一致。"""
        ao = AgentOutput(
            status="failure",
            command="run",
            output={"total": 2, "passed": 1, "failed": 1, "cases": []},
            error=None,
            metadata={"duration_ms": 1500},
        )
        parsed = json.loads(ao.to_json())
        assert parsed == ao.to_dict()
