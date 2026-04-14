"""MCP Server — 为 Claude Code 等 AI 客户端提供 MCP 工具接口。

通过 Model Context Protocol 暴露 rodski-agent 的核心能力：
  - Tools: run / design / pipeline / diagnose
  - Resources: 配置信息 / 用例列表

依赖 ``mcp`` 库（需 Python >= 3.10）。当 mcp 不可用时，
``create_mcp_server()`` 抛出 ``MCPUnavailableError``。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class MCPUnavailableError(Exception):
    """MCP SDK 不可用。"""


def create_mcp_server() -> Any:
    """创建并配置 MCP Server 实例。

    Returns
    -------
    FastMCP
        配置好 tools 和 resources 的 MCP Server 实例。

    Raises
    ------
    MCPUnavailableError
        mcp 库不可用时。
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise MCPUnavailableError(
            f"MCP SDK not available (requires Python >= 3.10): {exc}"
        ) from exc

    mcp = FastMCP(
        "rodski-agent",
        description="AI Agent layer for RodSki test automation framework",
    )

    # ---- Register tools ----
    _register_tools(mcp)

    # ---- Register resources ----
    _register_resources(mcp)

    return mcp


# ==================================================================
# Tool definitions
# ==================================================================


def _register_tools(mcp: Any) -> None:
    """注册 MCP 工具。"""

    @mcp.tool()
    def rodski_run(
        case_path: str,
        max_retry: int = 3,
        headless: bool = True,
        browser: str = "chromium",
    ) -> str:
        """Execute a RodSki test case.

        Runs the specified test case through the execution pipeline with
        optional retry on failure.

        Args:
            case_path: Path to the test case file or directory.
            max_retry: Maximum number of retries on failure (default: 3).
            headless: Run browser in headless mode (default: True).
            browser: Browser engine to use (default: chromium).

        Returns:
            JSON string with execution results including status, report,
            and any fixes applied during retries.
        """
        return _execute_run(case_path, max_retry, headless, browser)

    @mcp.tool()
    def rodski_design(
        requirement: str,
        output_dir: str,
        target_url: str = "",
    ) -> str:
        """Design test cases from a natural-language requirement.

        Generates XML test case files (case/model/data) based on the
        provided requirement description.

        Args:
            requirement: Natural-language description of what to test.
            output_dir: Directory where generated XML files will be saved.
            target_url: Optional URL of the system under test for visual exploration.

        Returns:
            JSON string with generated file paths and design status.
        """
        return _execute_design(requirement, output_dir, target_url)

    @mcp.tool()
    def rodski_pipeline(
        requirement: str,
        output_dir: str,
        target_url: str = "",
        max_retry: int = 3,
        headless: bool = True,
        browser: str = "chromium",
    ) -> str:
        """Run the full design-then-execute pipeline.

        First designs test cases from the requirement, then executes them.
        Combines the design and run tools into a single workflow.

        Args:
            requirement: Natural-language description of what to test.
            output_dir: Directory for generated files and results.
            target_url: Optional URL of the system under test.
            max_retry: Maximum retries on execution failure (default: 3).
            headless: Run browser in headless mode (default: True).
            browser: Browser engine (default: chromium).

        Returns:
            JSON string with both design and execution results.
        """
        return _execute_pipeline(
            requirement, output_dir, target_url, max_retry, headless, browser
        )

    @mcp.tool()
    def rodski_diagnose(result_path: str) -> str:
        """Diagnose a failed test result.

        Analyzes test execution results to identify root causes and
        suggest fixes for failures.

        Args:
            result_path: Path to test result directory or file
                (execution_summary.json or result_*.xml).

        Returns:
            JSON string with diagnosis for each failed test case,
            including root cause, confidence, and suggested actions.
        """
        return _execute_diagnose(result_path)


# ==================================================================
# Resource definitions
# ==================================================================


def _register_resources(mcp: Any) -> None:
    """注册 MCP 资源。"""

    @mcp.resource("rodski://config")
    def get_config() -> str:
        """Get current rodski-agent configuration.

        Returns the current agent configuration as YAML text.
        """
        return _get_config_resource()

    @mcp.resource("rodski://version")
    def get_version() -> str:
        """Get rodski-agent version information.

        Returns version string for rodski-agent.
        """
        from rodski_agent import __version__
        return json.dumps({"version": __version__}, ensure_ascii=False)

    @mcp.resource("rodski://capabilities")
    def get_capabilities() -> str:
        """Get rodski-agent capabilities summary.

        Returns a description of available tools and their purposes.
        """
        return json.dumps({
            "tools": [
                {
                    "name": "rodski_run",
                    "description": "Execute test cases with retry support",
                },
                {
                    "name": "rodski_design",
                    "description": "Generate XML test cases from requirements",
                },
                {
                    "name": "rodski_pipeline",
                    "description": "Full design-then-execute workflow",
                },
                {
                    "name": "rodski_diagnose",
                    "description": "Diagnose failed test results",
                },
            ],
            "resources": [
                "rodski://config",
                "rodski://version",
                "rodski://capabilities",
            ],
        }, ensure_ascii=False, indent=2)


# ==================================================================
# Tool implementations
# ==================================================================


def _execute_run(
    case_path: str,
    max_retry: int,
    headless: bool,
    browser: str,
) -> str:
    """执行 run 工具逻辑。"""
    try:
        from rodski_agent.execution.graph import build_execution_graph

        abs_path = os.path.abspath(case_path)
        state = {
            "case_path": abs_path,
            "max_retry": max_retry,
            "headless": headless,
            "browser": browser,
        }

        graph = build_execution_graph()
        result = graph.invoke(state)

        status = result.get("status", "error")
        report = result.get("report", {})
        error = result.get("error", "")
        retry_count = result.get("retry_count", 0)
        fixes = result.get("fixes_applied", [])

        output = {
            "status": status,
            "report": report,
            "retry_count": retry_count,
            "fixes_applied": fixes,
        }
        if error:
            output["error"] = error

        return json.dumps(output, ensure_ascii=False, indent=2)

    except Exception as exc:
        return json.dumps({
            "status": "error",
            "error": f"Run failed: {exc}",
        }, ensure_ascii=False)


def _execute_design(
    requirement: str,
    output_dir: str,
    target_url: str,
) -> str:
    """执行 design 工具逻辑。"""
    try:
        from rodski_agent.design.graph import build_design_graph

        abs_output = os.path.abspath(output_dir)
        state: dict[str, Any] = {
            "requirement": requirement,
            "output_dir": abs_output,
        }
        if target_url:
            state["target_url"] = target_url

        graph = build_design_graph()
        result = graph.invoke(state)

        status = result.get("status", "error")
        generated_files = result.get("generated_files", [])
        validation_errors = result.get("validation_errors", [])
        error = result.get("error", "")

        output = {
            "status": "success" if status == "success" else "error",
            "generated_files": generated_files,
            "file_count": len(generated_files),
        }
        if validation_errors:
            output["validation_errors"] = validation_errors
        if error:
            output["error"] = error

        return json.dumps(output, ensure_ascii=False, indent=2)

    except Exception as exc:
        return json.dumps({
            "status": "error",
            "error": f"Design failed: {exc}",
        }, ensure_ascii=False)


def _execute_pipeline(
    requirement: str,
    output_dir: str,
    target_url: str,
    max_retry: int,
    headless: bool,
    browser: str,
) -> str:
    """执行 pipeline 工具逻辑。"""
    try:
        from rodski_agent.pipeline.orchestrator import run_pipeline

        abs_output = os.path.abspath(output_dir)
        result = run_pipeline(
            requirement=requirement,
            output_dir=abs_output,
            target_url=target_url or None,
            max_retry=max_retry,
            headless=headless,
            browser=browser,
        )

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as exc:
        return json.dumps({
            "status": "error",
            "error": f"Pipeline failed: {exc}",
        }, ensure_ascii=False)


def _execute_diagnose(result_path: str) -> str:
    """执行 diagnose 工具逻辑。"""
    try:
        from rodski_agent.cli import _load_result_data
        from rodski_agent.execution.nodes import diagnose as diagnose_node

        abs_path = os.path.abspath(result_path)
        case_results = _load_result_data(abs_path)

        if case_results is None:
            return json.dumps({
                "status": "error",
                "error": f"Cannot load result from {abs_path}",
            }, ensure_ascii=False)

        state: dict[str, Any] = {
            "case_results": case_results,
            "screenshots": [],
        }
        diagnosis_update = diagnose_node(state)
        diagnosis = diagnosis_update.get("diagnosis", {})

        return json.dumps({
            "status": "success",
            "diagnosis": diagnosis,
        }, ensure_ascii=False, indent=2)

    except Exception as exc:
        return json.dumps({
            "status": "error",
            "error": f"Diagnose failed: {exc}",
        }, ensure_ascii=False)


def _get_config_resource() -> str:
    """获取配置信息。"""
    try:
        from rodski_agent.common.config import AgentConfig
        import yaml

        cfg = AgentConfig.load()
        return yaml.dump(cfg.to_dict(), allow_unicode=True, default_flow_style=False)
    except Exception as exc:
        return json.dumps({"error": f"Cannot load config: {exc}"})


# ==================================================================
# CLI entry point for MCP server
# ==================================================================


def main() -> None:
    """MCP Server 启动入口。

    可通过 ``rodski-agent-mcp`` 命令或 ``python -m rodski_agent.mcp_server`` 启动。
    """
    try:
        mcp = create_mcp_server()
        mcp.run()
    except MCPUnavailableError as exc:
        logger.error("Cannot start MCP server: %s", exc)
        print(f"Error: {exc}")
        print("Install MCP SDK: pip install 'mcp>=1.0'")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
