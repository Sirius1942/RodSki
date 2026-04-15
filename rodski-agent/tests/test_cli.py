"""CLI 入口单元测试。

测试 src/rodski_agent/cli.py 中各子命令的基本行为。
覆盖：版本输出、帮助文本、输出格式切换（human/json）、子命令路由。
所有测试均通过 Click CliRunner 隔离，不涉及真实网络或文件系统。
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from rodski_agent import __version__
from rodski_agent.cli import main
from rodski_agent.common.rodski_tools import RodskiResult


class TestMainGroup:
    """main CLI 组 —— 全局选项与版本"""

    def test_version_输出版本号(self, cli_runner: CliRunner):
        """--version 标志应输出当前版本号并以 0 退出。"""
        result = cli_runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help_显示帮助文本(self, cli_runner: CliRunner):
        """--help 标志应显示帮助信息并以 0 退出。"""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "rodski-agent" in result.output.lower() or "Usage" in result.output

    def test_no_args_显示帮助(self, cli_runner: CliRunner):
        """不提供任何参数应显示帮助信息（Click group 默认行为）。"""
        result = cli_runner.invoke(main, [])
        # Click group 默认在没有子命令时返回 0 并打印 usage
        assert result.exit_code == 0


class TestRunCommand:
    """run 子命令测试"""

    def test_run_help_显示帮助(self, cli_runner: CliRunner):
        """run --help 应显示 run 子命令的帮助文本。"""
        result = cli_runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        assert "--case" in result.output

    def test_run_format_json_输出合法JSON(self, cli_runner: CliRunner, sample_project_dir):
        """--format json run --case <path> 应输出一行合法 JSON 对象。"""
        mock_result = RodskiResult(success=True, exit_code=0, stdout="", stderr="")
        with patch("rodski_agent.common.rodski_tools.rodski_run", return_value=mock_result):
            case_path = str(sample_project_dir)
            result = cli_runner.invoke(main, ["--format", "json", "run", "--case", case_path])
        parsed = json.loads(result.output.strip())
        assert isinstance(parsed, dict)
        assert "status" in parsed

    def test_run_nonexistent_path_error(self, cli_runner: CliRunner, tmp_path):
        """Non-existent case path should exit with error status."""
        case_path = str(tmp_path / "nonexistent")
        result = cli_runner.invoke(main, ["--format", "json", "run", "--case", case_path])
        parsed = json.loads(result.output.strip())
        assert parsed["status"] == "error"

    def test_run_format_human_输出可读文本(self, cli_runner: CliRunner, tmp_path):
        """--format human run --case <path> 应输出人类可读文本（非 JSON）。"""
        case_path = str(tmp_path / "nonexistent")
        result = cli_runner.invoke(main, ["--format", "human", "run", "--case", case_path])
        assert result.output.strip() != ""
        try:
            json.loads(result.output.strip())
            is_json = True
        except (json.JSONDecodeError, ValueError):
            is_json = False
        assert not is_json, "human 格式不应输出 JSON"

    def test_run_缺少case选项报错(self, cli_runner: CliRunner):
        """run 命令缺少必填 --case 选项时应以非 0 退出。"""
        result = cli_runner.invoke(main, ["run"])
        assert result.exit_code != 0

    def test_run_valid_project_dir(self, cli_runner: CliRunner, sample_project_dir):
        """Valid project dir with mocked rodski_run should return pass."""
        mock_result = RodskiResult(success=True, exit_code=0, stdout="", stderr="")
        with patch("rodski_agent.common.rodski_tools.rodski_run", return_value=mock_result):
            result = cli_runner.invoke(main, ["--format", "json", "run", "--case", str(sample_project_dir)])
        parsed = json.loads(result.output.strip())
        assert parsed["status"] == "success"


class TestDesignCommand:
    """design 子命令测试"""

    def test_design_help_显示帮助(self, cli_runner: CliRunner):
        """design --help 应显示帮助文本，包含 --requirement 选项。"""
        result = cli_runner.invoke(main, ["design", "--help"])
        assert result.exit_code == 0
        assert "--requirement" in result.output

    def test_design_缺少必填选项报错(self, cli_runner: CliRunner):
        """design 命令缺少 --requirement 或 --output 时应以非 0 退出。"""
        result = cli_runner.invoke(main, ["design"])
        assert result.exit_code != 0

    def test_design_placeholder_输出(self, cli_runner: CliRunner, tmp_path):
        """提供必填参数后 design 命令应返回 placeholder 输出。"""
        import json as _json
        output_path = str(tmp_path / "out")

        scenarios = _json.dumps([{"scenario_name": "t", "description": "Test", "type": "ui", "steps_outline": ["a"]}])
        case_plan = _json.dumps([{
            "id": "c001", "title": "Test",
            "steps": [{"phase": "test_case", "action": "type", "model": "Login", "data": "D001"}],
        }])
        test_data = _json.dumps({
            "datatables": [{"name": "Login", "rows": [{"id": "D001", "fields": [{"name": "f1", "value": "v1"}]}]}],
            "verify_tables": [],
        })
        responses = [scenarios, case_plan, test_data]
        counter = {"n": 0}

        def mock_llm(prompt, agent_type="design"):
            idx = counter["n"]
            counter["n"] += 1
            return responses[idx] if idx < len(responses) else "[]"

        with patch("rodski_agent.common.llm_bridge.call_llm_text", side_effect=mock_llm):
            result = cli_runner.invoke(main, [
                "design",
                "--requirement", "测试登录功能",
                "--output", output_path,
            ])
        assert result.exit_code == 0
        assert result.output.strip() != ""


class TestConfigCommand:
    """config 子命令组测试"""

    def test_config_help_显示帮助(self, cli_runner: CliRunner):
        """config --help 应显示 config 子命令组的帮助文本。"""
        result = cli_runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output

    def test_config_show_正常返回(self, cli_runner: CliRunner):
        """config show 应正常执行并输出内容。"""
        result = cli_runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        assert result.output.strip() != ""

    def test_config_show_json格式(self, cli_runner: CliRunner):
        """--format json config show 应输出合法 JSON 对象。"""
        result = cli_runner.invoke(main, ["--format", "json", "config", "show"])
        assert result.exit_code == 0
        parsed = json.loads(result.output.strip())
        assert isinstance(parsed, dict)
        assert parsed.get("status") == "success"
        assert "output" in parsed


class TestPipelineCommand:
    """pipeline 子命令测试"""

    def test_pipeline_help_显示帮助(self, cli_runner: CliRunner):
        """pipeline --help 应显示帮助文本。"""
        result = cli_runner.invoke(main, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "--requirement" in result.output

    def test_pipeline_runs_and_produces_output(self, cli_runner: CliRunner, tmp_path):
        """pipeline 命令应执行并产生输出（无真实环境时预期非零退出）。"""
        output_path = str(tmp_path / "out")
        result = cli_runner.invoke(main, [
            "pipeline",
            "--requirement", "测试购物车功能",
            "--output", output_path,
        ])
        # Pipeline runs design + execution; without a real test env, non-zero is expected
        assert result.output.strip() != ""


class TestDiagnoseCommand:
    """diagnose 子命令测试"""

    def test_diagnose_help_显示帮助(self, cli_runner: CliRunner):
        """diagnose --help 应显示帮助文本，包含 --result 选项。"""
        result = cli_runner.invoke(main, ["diagnose", "--help"])
        assert result.exit_code == 0
        assert "--result" in result.output

    def test_diagnose_nonexistent_result_报错(self, cli_runner: CliRunner, tmp_path):
        """提供不存在的 --result 路径后 diagnose 命令应以非 0 退出。"""
        result_path = str(tmp_path / "result.xml")
        result = cli_runner.invoke(main, ["diagnose", "--result", result_path])
        assert result.exit_code != 0
        assert result.output.strip() != ""
