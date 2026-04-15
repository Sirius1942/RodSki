"""Pipeline 编排器和 CLI 命令单元测试。

测试 Design → Validation Gate → Execution 串联 pipeline 的完整流程。
所有外部依赖均 Mock，确保测试无网络或文件系统副作用。
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from rodski_agent.pipeline.orchestrator import (
    run_pipeline,
    _aggregate_execution_results,
    _find_case_files,
)


# ============================================================
# Orchestrator tests
# ============================================================


class TestRunPipeline:
    """run_pipeline 函数测试"""

    def test_design_success_execution_pass(self, tmp_path):
        """Design succeeds + execution passes → overall success."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            # Mock design graph
            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/case.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            # Mock validation gate
            mock_val.return_value = MagicMock(success=True, stderr="", stdout="OK")

            # Mock execution graph
            exec_graph = MagicMock()
            exec_graph.invoke.return_value = {
                "status": "pass",
                "report": {"total": 1, "passed": 1, "failed": 0, "cases": []},
            }
            mock_eg.return_value = exec_graph

            result = run_pipeline(
                requirement="test login",
                output_dir=output_dir,
            )

        assert result["status"] == "success"
        assert result["design"]["status"] == "success"
        assert result["execution"]["status"] == "pass"

    def test_design_failure_skips_execution(self, tmp_path):
        """Design fails → execution skipped, overall error."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg:
            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "error",
                "error": "XML validation failed",
                "generated_files": [],
                "validation_errors": ["bad xml"],
            }
            mock_dg.return_value = design_graph

            result = run_pipeline(
                requirement="test login",
                output_dir=output_dir,
            )

        assert result["status"] == "error"
        assert "validation" in result["error"].lower() or "Design" in result.get("error", "")
        assert result["execution"] == {}

    def test_validation_gate_failure(self, tmp_path):
        """Design succeeds but validation gate fails → error."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/case.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_val.return_value = MagicMock(
                success=False,
                stderr="case/test.xml: invalid action 'click'",
                stdout="",
            )

            result = run_pipeline(
                requirement="test login",
                output_dir=output_dir,
            )

        assert result["status"] == "error"
        assert "Validation gate failed" in result["error"]
        assert result["validation"]["passed"] is False

    def test_execution_failure(self, tmp_path):
        """Design succeeds + execution fails → overall failure."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/case.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_val.return_value = MagicMock(success=True, stderr="", stdout="OK")

            exec_graph = MagicMock()
            exec_graph.invoke.return_value = {
                "status": "fail",
                "report": {"total": 2, "passed": 0, "failed": 2, "cases": []},
                "error": "all cases failed",
            }
            mock_eg.return_value = exec_graph

            result = run_pipeline(
                requirement="test login",
                output_dir=output_dir,
            )

        assert result["status"] == "failure"
        assert result["design"]["status"] == "success"
        assert result["execution"]["status"] == "fail"

    def test_design_exception(self, tmp_path):
        """Design raises exception → error status."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg:
            mock_dg.side_effect = ImportError("no design module")

            result = run_pipeline(
                requirement="test login",
                output_dir=output_dir,
            )

        assert result["status"] == "error"
        assert "Design phase failed" in result["error"]

    def test_execution_exception(self, tmp_path):
        """Execution raises exception → error status."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_val.return_value = MagicMock(success=True, stderr="", stdout="OK")

            mock_eg.side_effect = RuntimeError("graph build failed")

            result = run_pipeline(
                requirement="test login",
                output_dir=output_dir,
            )

        assert result["status"] == "error"
        assert "graph build failed" in result["error"]

    def test_passes_url_to_design(self, tmp_path):
        """target_url should be passed to design state."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_val.return_value = MagicMock(success=True, stderr="", stdout="OK")

            exec_graph = MagicMock()
            exec_graph.invoke.return_value = {
                "status": "pass",
                "report": {"total": 0, "passed": 0, "failed": 0},
            }
            mock_eg.return_value = exec_graph

            run_pipeline(
                requirement="test login",
                output_dir=output_dir,
                target_url="https://example.com",
            )

            call_args = design_graph.invoke.call_args[0][0]
            assert call_args["target_url"] == "https://example.com"

    def test_passes_retry_and_browser_to_execution(self, tmp_path):
        """max_retry, headless, browser should be passed to execution state."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_val.return_value = MagicMock(success=True, stderr="", stdout="OK")

            exec_graph = MagicMock()
            exec_graph.invoke.return_value = {
                "status": "pass",
                "report": {"total": 0, "passed": 0, "failed": 0},
            }
            mock_eg.return_value = exec_graph

            run_pipeline(
                requirement="test",
                output_dir=output_dir,
                max_retry=5,
                headless=False,
                browser="firefox",
            )

            call_args = exec_graph.invoke.call_args[0][0]
            assert call_args["max_retry"] == 5
            assert call_args["headless"] is False
            assert call_args["browser"] == "firefox"

    def test_partial_execution_result(self, tmp_path):
        """Partial execution (some pass, some fail) → failure."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_val.return_value = MagicMock(success=True, stderr="", stdout="OK")

            exec_graph = MagicMock()
            exec_graph.invoke.return_value = {
                "status": "partial",
                "report": {"total": 3, "passed": 1, "failed": 2},
            }
            mock_eg.return_value = exec_graph

            result = run_pipeline(
                requirement="test",
                output_dir=output_dir,
            )

        assert result["status"] == "failure"


# ============================================================
# Helper function tests
# ============================================================


class TestFindCaseFiles:
    """_find_case_files 测试"""

    def test_finds_xml_files(self, tmp_path):
        """Should find all XML files in case/ directory."""
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        (case_dir / "test1.xml").write_text("<cases/>")
        (case_dir / "test2.xml").write_text("<cases/>")
        (case_dir / "readme.txt").write_text("not xml")

        files = _find_case_files(str(tmp_path))
        assert len(files) == 2
        assert all(f.endswith(".xml") for f in files)

    def test_no_case_dir(self, tmp_path):
        """No case/ directory → empty list."""
        assert _find_case_files(str(tmp_path)) == []


class TestAggregateExecutionResults:
    """_aggregate_execution_results 测试"""

    def test_empty_results(self):
        """Empty results → pass with zero counts."""
        result = _aggregate_execution_results([])
        assert result["status"] == "pass"
        assert result["report"]["total"] == 0

    def test_single_result(self):
        """Single result returned directly."""
        r = [{"status": "pass", "report": {"total": 1, "passed": 1, "failed": 0}}]
        result = _aggregate_execution_results(r)
        assert result["status"] == "pass"

    def test_multi_result_all_pass(self):
        """Multiple results all pass → pass."""
        results = [
            {"status": "pass", "report": {"total": 1, "passed": 1, "failed": 0, "cases": []}},
            {"status": "pass", "report": {"total": 2, "passed": 2, "failed": 0, "cases": []}},
        ]
        result = _aggregate_execution_results(results)
        assert result["status"] == "pass"
        assert result["report"]["total"] == 3
        assert result["report"]["passed"] == 3

    def test_multi_result_partial(self):
        """Mixed pass/fail → partial."""
        results = [
            {"status": "pass", "report": {"total": 1, "passed": 1, "failed": 0, "cases": []}},
            {"status": "fail", "report": {"total": 1, "passed": 0, "failed": 1, "cases": []}},
        ]
        result = _aggregate_execution_results(results)
        assert result["status"] == "partial"


# ============================================================
# CLI tests
# ============================================================


class TestPipelineCLI:
    """pipeline CLI 命令测试"""

    def test_pipeline_help(self, cli_runner):
        """pipeline --help should show help text."""
        from rodski_agent.cli import main
        result = cli_runner.invoke(main, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "--requirement" in result.output
        assert "--output" in result.output
        assert "--max-retry" in result.output
        assert "--max-fix-attempts" in result.output
        assert "--parallel" in result.output
        assert "--max-workers" in result.output

    def test_pipeline_missing_requirement(self, cli_runner):
        """Missing --requirement should fail."""
        from rodski_agent.cli import main
        result = cli_runner.invoke(main, ["pipeline", "--output", "/tmp/out"])
        assert result.exit_code != 0

    def test_pipeline_json_output(self, cli_runner, tmp_path):
        """pipeline with --format json should produce valid JSON."""
        from rodski_agent.cli import main
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/case.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_val.return_value = MagicMock(success=True, stderr="", stdout="OK")

            exec_graph = MagicMock()
            exec_graph.invoke.return_value = {
                "status": "pass",
                "report": {"total": 1, "passed": 1, "failed": 0},
            }
            mock_eg.return_value = exec_graph

            result = cli_runner.invoke(main, [
                "--format", "json",
                "pipeline",
                "--requirement", "test login",
                "--output", output_dir,
            ])

        parsed = json.loads(result.output.strip())
        assert parsed["status"] == "success"
        assert parsed["command"] == "pipeline"
        assert "design" in parsed["output"]
        assert "execution" in parsed["output"]

    def test_pipeline_human_output_success(self, cli_runner, tmp_path):
        """pipeline human output on success."""
        from rodski_agent.cli import main
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg, \
             patch("rodski_agent.common.rodski_tools.rodski_validate") as mock_val:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/a.xml", "/tmp/b.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_val.return_value = MagicMock(success=True, stderr="", stdout="OK")

            exec_graph = MagicMock()
            exec_graph.invoke.return_value = {
                "status": "pass",
                "report": {"total": 2, "passed": 2, "failed": 0},
            }
            mock_eg.return_value = exec_graph

            result = cli_runner.invoke(main, [
                "pipeline",
                "--requirement", "test login",
                "--output", output_dir,
            ])

        assert result.exit_code == 0
        assert "Pipeline complete" in result.output
        assert "2 file(s)" in result.output

    def test_pipeline_error_exit_code(self, cli_runner, tmp_path):
        """pipeline error should have non-zero exit code."""
        from rodski_agent.cli import main
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg:
            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "error",
                "error": "Design failed",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            result = cli_runner.invoke(main, [
                "--format", "json",
                "pipeline",
                "--requirement", "test",
                "--output", output_dir,
            ])

        parsed = json.loads(result.output.strip())
        assert parsed["status"] == "error"
        assert result.exit_code != 0


# ============================================================
# Integration test (using mock LLM)
# ============================================================


class TestPipelineIntegration:
    """Pipeline 端到端集成测试（Mock LLM）。"""

    def test_full_pipeline_with_mock_llm(self, tmp_path):
        """Full pipeline with real design graph (mock LLM) and mock execution."""
        import json as _json

        output_dir = str(tmp_path / "pipeline_output")

        scenarios = _json.dumps([{"scenario_name": "t", "description": "Test", "type": "ui", "steps_outline": ["a"]}])
        case_plan = _json.dumps([{
            "id": "c001", "title": "Test",
            "steps": [{"phase": "test_case", "action": "type", "model": "Login", "data": "D001"}],
        }])
        test_data = _json.dumps({
            "datatables": [{"name": "Login", "rows": [{"id": "D001", "fields": [{"name": "f1", "value": "v1"}]}]}],
            "verify_tables": [],
        })
        llm_responses = [scenarios, case_plan, test_data]
        call_count = {"n": 0}

        def mock_llm(prompt, agent_type="design"):
            idx = call_count["n"]
            call_count["n"] += 1
            return llm_responses[idx] if idx < len(llm_responses) else "[]"

        with patch("rodski_agent.common.llm_bridge.call_llm_text", side_effect=mock_llm), \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:
            exec_graph = MagicMock()
            exec_graph.invoke.return_value = {
                "status": "pass",
                "report": {"total": 1, "passed": 1, "failed": 0},
            }
            mock_eg.return_value = exec_graph

            result = run_pipeline(
                requirement="测试登录功能",
                output_dir=output_dir,
            )

        assert result["design"]["status"] == "success"
        assert len(result["design"]["generated_files"]) >= 1
        assert result["execution"]["status"] == "pass"
        assert result["status"] == "success"
        assert os.path.isdir(os.path.join(output_dir, "case"))
