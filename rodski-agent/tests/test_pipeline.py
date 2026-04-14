"""Pipeline 编排器和 CLI 命令单元测试。

测试 Design → Execution 串联 pipeline 的完整流程。
所有外部依赖均 Mock，确保测试无网络或文件系统副作用。
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from rodski_agent.pipeline.orchestrator import run_pipeline


# ============================================================
# Orchestrator tests
# ============================================================


class TestRunPipeline:
    """run_pipeline 函数测试"""

    def test_design_success_execution_pass(self, tmp_path):
        """Design succeeds + execution passes → overall success."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:

            # Mock design graph
            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/case.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

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

    def test_execution_failure(self, tmp_path):
        """Design succeeds + execution fails → overall failure."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/case.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

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
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

            mock_eg.side_effect = RuntimeError("graph build failed")

            result = run_pipeline(
                requirement="test login",
                output_dir=output_dir,
            )

        assert result["status"] == "error"
        assert "Execution phase failed" in result["error"]

    def test_passes_url_to_design(self, tmp_path):
        """target_url should be passed to design state."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

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

            # Check design_graph.invoke was called with target_url
            call_args = design_graph.invoke.call_args[0][0]
            assert call_args["target_url"] == "https://example.com"

    def test_passes_retry_and_browser_to_execution(self, tmp_path):
        """max_retry, headless, browser should be passed to execution state."""
        output_dir = str(tmp_path / "output")

        with patch("rodski_agent.design.graph.build_design_graph") as mock_dg, \
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

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
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

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
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/case.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

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
             patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:

            design_graph = MagicMock()
            design_graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/a.xml", "/tmp/b.xml"],
                "validation_errors": [],
            }
            mock_dg.return_value = design_graph

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
# Integration test (using real nodes with LLM fallback)
# ============================================================


class TestPipelineIntegration:
    """Pipeline 端到端集成测试（LLM 不可用，使用 fallback）。"""

    def test_full_pipeline_with_fallback(self, tmp_path):
        """Full pipeline with real design graph (fallback) and mock execution."""
        output_dir = str(tmp_path / "pipeline_output")

        with patch("rodski_agent.execution.graph.build_execution_graph") as mock_eg:
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

        # Design should succeed via fallback
        assert result["design"]["status"] == "success"
        assert len(result["design"]["generated_files"]) >= 1
        # Execution mock should pass
        assert result["execution"]["status"] == "pass"
        assert result["status"] == "success"
        # Files should exist
        assert os.path.isdir(os.path.join(output_dir, "case"))
