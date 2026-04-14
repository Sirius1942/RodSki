"""MCP Server 单元测试 (Iteration 10)。

测试 MCP Server 的工具函数和资源函数逻辑。
由于 mcp 库可能不可用，测试聚焦于底层实现函数。
"""
from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from rodski_agent.mcp_server import (
    MCPUnavailableError,
    _execute_run,
    _execute_design,
    _execute_pipeline,
    _execute_diagnose,
    _get_config_resource,
)


# ============================================================
# MCPUnavailableError and create_mcp_server
# ============================================================


class TestCreateMCPServer:
    """create_mcp_server 测试。"""

    def test_mcp_unavailable_error(self):
        """When mcp is not installed, MCPUnavailableError is raised."""
        from rodski_agent.mcp_server import create_mcp_server

        with patch.dict("sys.modules", {"mcp": None, "mcp.server": None, "mcp.server.fastmcp": None}):
            import importlib
            import rodski_agent.mcp_server as mod
            importlib.reload(mod)
            try:
                with pytest.raises(mod.MCPUnavailableError, match="MCP SDK not available"):
                    mod.create_mcp_server()
            finally:
                importlib.reload(mod)

    def test_mcp_available(self):
        """When mcp is installed, server is created successfully."""
        from rodski_agent.mcp_server import create_mcp_server

        # Mock FastMCP
        mock_fastmcp_class = MagicMock()
        mock_instance = MagicMock()
        mock_fastmcp_class.return_value = mock_instance

        mock_module = MagicMock()
        mock_module.FastMCP = mock_fastmcp_class

        with patch.dict("sys.modules", {"mcp.server.fastmcp": mock_module}):
            import importlib
            import rodski_agent.mcp_server as mod
            importlib.reload(mod)
            try:
                server = mod.create_mcp_server()
                assert server is not None
            finally:
                importlib.reload(mod)


# ============================================================
# Tool: rodski_run
# ============================================================


class TestExecuteRun:
    """_execute_run 工具实现测试。"""

    def test_successful_run(self, tmp_path):
        """Successful execution → JSON with pass status."""
        with patch("rodski_agent.execution.graph.build_execution_graph") as mock_bg:
            graph = MagicMock()
            graph.invoke.return_value = {
                "status": "pass",
                "report": {"total": 2, "passed": 2, "failed": 0, "cases": []},
                "retry_count": 0,
                "fixes_applied": [],
            }
            mock_bg.return_value = graph

            result = _execute_run(str(tmp_path), max_retry=3, headless=True, browser="chromium")

        data = json.loads(result)
        assert data["status"] == "pass"
        assert data["report"]["total"] == 2
        assert data["retry_count"] == 0

    def test_failed_run(self, tmp_path):
        """Failed execution → JSON with fail status."""
        with patch("rodski_agent.execution.graph.build_execution_graph") as mock_bg:
            graph = MagicMock()
            graph.invoke.return_value = {
                "status": "fail",
                "report": {"total": 1, "passed": 0, "failed": 1},
                "error": "test failed",
                "retry_count": 2,
                "fixes_applied": ["added_wait"],
            }
            mock_bg.return_value = graph

            result = _execute_run(str(tmp_path), max_retry=3, headless=True, browser="chromium")

        data = json.loads(result)
        assert data["status"] == "fail"
        assert data["error"] == "test failed"
        assert data["retry_count"] == 2
        assert data["fixes_applied"] == ["added_wait"]

    def test_run_exception(self):
        """Exception during run → error JSON."""
        with patch("rodski_agent.execution.graph.build_execution_graph", side_effect=ImportError("no module")):
            result = _execute_run("/bad/path", max_retry=3, headless=True, browser="chromium")

        data = json.loads(result)
        assert data["status"] == "error"
        assert "Run failed" in data["error"]

    def test_run_uses_absolute_path(self, tmp_path):
        """case_path is converted to absolute."""
        with patch("rodski_agent.execution.graph.build_execution_graph") as mock_bg:
            graph = MagicMock()
            graph.invoke.return_value = {"status": "pass", "report": {}}
            mock_bg.return_value = graph

            _execute_run("relative/path", max_retry=1, headless=True, browser="chromium")

            call_state = graph.invoke.call_args[0][0]
            assert os.path.isabs(call_state["case_path"])


# ============================================================
# Tool: rodski_design
# ============================================================


class TestExecuteDesign:
    """_execute_design 工具实现测试。"""

    def test_successful_design(self, tmp_path):
        """Design succeeds → JSON with generated files."""
        with patch("rodski_agent.design.graph.build_design_graph") as mock_bg:
            graph = MagicMock()
            graph.invoke.return_value = {
                "status": "success",
                "generated_files": ["/tmp/case/c001.xml", "/tmp/model/model.xml"],
                "validation_errors": [],
            }
            mock_bg.return_value = graph

            result = _execute_design(
                "test login", str(tmp_path / "output"), ""
            )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["file_count"] == 2
        assert len(data["generated_files"]) == 2

    def test_design_with_url(self, tmp_path):
        """target_url is passed to design state."""
        with patch("rodski_agent.design.graph.build_design_graph") as mock_bg:
            graph = MagicMock()
            graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_bg.return_value = graph

            _execute_design("test", str(tmp_path), "https://example.com")

            call_state = graph.invoke.call_args[0][0]
            assert call_state["target_url"] == "https://example.com"

    def test_design_without_url(self, tmp_path):
        """Empty target_url is not passed to state."""
        with patch("rodski_agent.design.graph.build_design_graph") as mock_bg:
            graph = MagicMock()
            graph.invoke.return_value = {
                "status": "success",
                "generated_files": [],
                "validation_errors": [],
            }
            mock_bg.return_value = graph

            _execute_design("test", str(tmp_path), "")

            call_state = graph.invoke.call_args[0][0]
            assert "target_url" not in call_state

    def test_design_failure(self, tmp_path):
        """Design fails → error JSON with validation errors."""
        with patch("rodski_agent.design.graph.build_design_graph") as mock_bg:
            graph = MagicMock()
            graph.invoke.return_value = {
                "status": "error",
                "error": "XML invalid",
                "generated_files": [],
                "validation_errors": ["bad schema"],
            }
            mock_bg.return_value = graph

            result = _execute_design("test", str(tmp_path), "")

        data = json.loads(result)
        assert data["status"] == "error"
        assert "bad schema" in data["validation_errors"]

    def test_design_exception(self):
        """Exception → error JSON."""
        with patch("rodski_agent.design.graph.build_design_graph", side_effect=RuntimeError("boom")):
            result = _execute_design("test", "/tmp", "")

        data = json.loads(result)
        assert data["status"] == "error"
        assert "Design failed" in data["error"]


# ============================================================
# Tool: rodski_pipeline
# ============================================================


class TestExecutePipeline:
    """_execute_pipeline 工具实现测试。"""

    def test_successful_pipeline(self, tmp_path):
        """Pipeline succeeds → combined result."""
        with patch("rodski_agent.pipeline.orchestrator.run_pipeline") as mock_rp:
            mock_rp.return_value = {
                "status": "success",
                "design": {"status": "success", "generated_files": ["/f.xml"]},
                "execution": {"status": "pass", "report": {"total": 1, "passed": 1}},
            }

            result = _execute_pipeline(
                "test", str(tmp_path), "", max_retry=3, headless=True, browser="chromium"
            )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["design"]["status"] == "success"
        assert data["execution"]["status"] == "pass"

    def test_pipeline_passes_all_params(self, tmp_path):
        """All parameters are forwarded to run_pipeline."""
        with patch("rodski_agent.pipeline.orchestrator.run_pipeline") as mock_rp:
            mock_rp.return_value = {"status": "success", "design": {}, "execution": {}}

            _execute_pipeline(
                "test req",
                str(tmp_path / "out"),
                "https://example.com",
                max_retry=5,
                headless=False,
                browser="firefox",
            )

            call_kwargs = mock_rp.call_args[1]
            assert call_kwargs["requirement"] == "test req"
            assert call_kwargs["target_url"] == "https://example.com"
            assert call_kwargs["max_retry"] == 5
            assert call_kwargs["headless"] is False
            assert call_kwargs["browser"] == "firefox"

    def test_pipeline_empty_url_becomes_none(self, tmp_path):
        """Empty target_url → None passed to run_pipeline."""
        with patch("rodski_agent.pipeline.orchestrator.run_pipeline") as mock_rp:
            mock_rp.return_value = {"status": "success", "design": {}, "execution": {}}

            _execute_pipeline("test", str(tmp_path), "", 3, True, "chromium")

            call_kwargs = mock_rp.call_args[1]
            assert call_kwargs["target_url"] is None

    def test_pipeline_exception(self):
        """Exception → error JSON."""
        with patch("rodski_agent.pipeline.orchestrator.run_pipeline", side_effect=Exception("broken")):
            result = _execute_pipeline("test", "/tmp", "", 3, True, "chromium")

        data = json.loads(result)
        assert data["status"] == "error"
        assert "Pipeline failed" in data["error"]


# ============================================================
# Tool: rodski_diagnose
# ============================================================


class TestExecuteDiagnose:
    """_execute_diagnose 工具实现测试。"""

    def test_successful_diagnose(self, tmp_path):
        """Diagnose with valid result → JSON diagnosis."""
        summary_file = tmp_path / "execution_summary.json"
        summary_file.write_text(json.dumps({
            "overall_status": "FAIL",
            "cases": [
                {"id": "c001", "title": "Login", "status": "FAIL", "error": "timeout", "time": 5.0}
            ],
        }), encoding="utf-8")

        with patch("rodski_agent.execution.nodes.diagnose") as mock_diag:
            mock_diag.return_value = {
                "diagnosis": {
                    "skipped": True,
                    "reason": "LLM unavailable",
                }
            }

            result = _execute_diagnose(str(summary_file))

        data = json.loads(result)
        assert data["status"] == "success"
        assert "diagnosis" in data

    def test_diagnose_invalid_path(self):
        """Invalid path → error JSON."""
        result = _execute_diagnose("/nonexistent/result.json")
        data = json.loads(result)
        assert data["status"] == "error"
        assert "Cannot load result" in data["error"]

    def test_diagnose_exception(self, tmp_path):
        """Exception during diagnosis → error JSON."""
        with patch("rodski_agent.cli._load_result_data", side_effect=Exception("broken")):
            result = _execute_diagnose(str(tmp_path))

        data = json.loads(result)
        assert data["status"] == "error"


# ============================================================
# Resource: config
# ============================================================


class TestConfigResource:
    """config 资源测试。"""

    def test_config_loaded(self):
        """Config resource returns YAML."""
        mock_cfg = MagicMock()
        mock_cfg.to_dict.return_value = {
            "rodski": {"cli_path": "rodski"},
            "llm": {"provider": "claude"},
        }
        with patch("rodski_agent.common.config.AgentConfig") as MockConfig:
            MockConfig.load.return_value = mock_cfg
            result = _get_config_resource()

        assert "rodski" in result
        assert "claude" in result

    def test_config_error(self):
        """Config load fails → error JSON."""
        with patch("rodski_agent.common.config.AgentConfig") as MockConfig:
            MockConfig.load.side_effect = Exception("no config")
            result = _get_config_resource()

        assert "error" in result.lower() or "Cannot load" in result


# ============================================================
# main() entry point
# ============================================================


class TestMain:
    """MCP server main 入口测试。"""

    def test_main_mcp_unavailable(self):
        """main() with no MCP → SystemExit(1)."""
        from rodski_agent.mcp_server import main

        with patch("rodski_agent.mcp_server.create_mcp_server", side_effect=MCPUnavailableError("no mcp")):
            with pytest.raises((SystemExit, MCPUnavailableError)):
                main()

    def test_main_runs_server(self):
        """main() with MCP → calls mcp.run()."""
        from rodski_agent.mcp_server import main

        mock_mcp = MagicMock()
        with patch("rodski_agent.mcp_server.create_mcp_server", return_value=mock_mcp):
            main()

        mock_mcp.run.assert_called_once()
