"""错误分类体系 + CLI 错误处理测试。"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from rodski_agent.cli import main
from rodski_agent.common.errors import (
    AgentError,
    ConfigError,
    ErrorCategory,
    ExecutionError,
    InternalError,
    LLMError,
    ParseError,
    TimeoutError_,
    ValidationError,
)


class TestErrorCategory:
    def test_枚举值(self):
        assert ErrorCategory.CONFIG_ERROR.value == "config_error"
        assert ErrorCategory.INTERNAL_ERROR.value == "internal_error"

    def test_所有成员(self):
        assert len(ErrorCategory) == 7


class TestAgentError:
    def test_基础属性(self):
        err = AgentError(
            code="E_TEST",
            category=ErrorCategory.EXECUTION_ERROR,
            message="test error",
            details={"key": "val"},
            suggestion="fix it",
        )
        assert err.code == "E_TEST"
        assert err.category == ErrorCategory.EXECUTION_ERROR
        assert err.message == "test error"
        assert str(err) == "test error"
        assert err.details == {"key": "val"}
        assert err.suggestion == "fix it"

    def test_to_dict_完整(self):
        err = AgentError(
            code="E_X",
            category=ErrorCategory.PARSE_ERROR,
            message="bad xml",
            details={"file": "a.xml"},
            suggestion="check format",
        )
        d = err.to_dict()
        assert d["code"] == "E_X"
        assert d["category"] == "parse_error"
        assert d["message"] == "bad xml"
        assert d["details"]["file"] == "a.xml"
        assert d["suggestion"] == "check format"

    def test_to_dict_省略None字段(self):
        err = AgentError(code="E", category=ErrorCategory.LLM_ERROR, message="oops")
        d = err.to_dict()
        assert "details" not in d
        assert "suggestion" not in d

    def test_isinstance_Exception(self):
        err = AgentError(code="E", category=ErrorCategory.INTERNAL_ERROR, message="x")
        assert isinstance(err, Exception)


class TestErrorSubclasses:
    def test_config_error(self):
        err = ConfigError("missing config")
        assert err.code == "E_CONFIG"
        assert err.category == ErrorCategory.CONFIG_ERROR

    def test_validation_error(self):
        err = ValidationError("bad path", code="E_VAL_PATH")
        assert err.code == "E_VAL_PATH"
        assert err.category == ErrorCategory.VALIDATION_ERROR

    def test_execution_error(self):
        err = ExecutionError("rodski crash")
        assert err.category == ErrorCategory.EXECUTION_ERROR

    def test_parse_error(self):
        err = ParseError("invalid xml", details={"line": 42})
        assert err.details == {"line": 42}
        assert err.category == ErrorCategory.PARSE_ERROR

    def test_llm_error(self):
        err = LLMError("API timeout", suggestion="retry later")
        assert err.suggestion == "retry later"
        assert err.category == ErrorCategory.LLM_ERROR

    def test_timeout_error(self):
        err = TimeoutError_("execution timed out after 300s")
        assert err.category == ErrorCategory.TIMEOUT_ERROR
        assert err.code == "E_TIMEOUT"

    def test_internal_error(self):
        err = InternalError("unexpected None")
        assert err.category == ErrorCategory.INTERNAL_ERROR

    def test_all_subclasses_inherit_AgentError(self):
        classes = [ConfigError, ValidationError, ExecutionError, ParseError, LLMError, TimeoutError_, InternalError]
        for cls in classes:
            err = cls("test")
            assert isinstance(err, AgentError)


class TestCLIErrorHandling:
    """CLI 层错误处理集成测试。"""

    def test_run_unexpected_exception_json格式(self, cli_runner: CliRunner, sample_project_dir):
        """Graph.invoke 抛出未预期异常时，JSON 模式应返回结构化 error。"""
        with patch("rodski_agent.cli.build_execution_graph") as mock_build:
            mock_build.return_value.invoke.side_effect = RuntimeError("boom")
            result = cli_runner.invoke(
                main,
                ["--format", "json", "run", "--case", str(sample_project_dir)],
            )

        parsed = json.loads(result.output.strip())
        assert parsed["status"] == "error"
        assert parsed["command"] == "run"
        assert "boom" in parsed["error"]
        assert parsed["metadata"]["error_code"] == "E_INTERNAL"
        assert result.exit_code == 2

    def test_run_unexpected_exception_human格式(self, cli_runner: CliRunner, sample_project_dir):
        """Graph.invoke 抛出未预期异常时，human 模式应显示错误信息。"""
        with patch("rodski_agent.cli.build_execution_graph") as mock_build:
            mock_build.return_value.invoke.side_effect = ValueError("bad value")
            result = cli_runner.invoke(
                main,
                ["--format", "human", "run", "--case", str(sample_project_dir)],
            )

        assert "bad value" in result.output
        assert result.exit_code == 2

    def test_run_agent_error_json格式(self, cli_runner: CliRunner, sample_project_dir):
        """AgentError 被正确捕获并输出结构化 JSON。"""
        with patch("rodski_agent.cli.build_execution_graph") as mock_build:
            mock_build.return_value.invoke.side_effect = ConfigError(
                "config not found",
                suggestion="run 'rodski-agent config show'",
            )
            result = cli_runner.invoke(
                main,
                ["--format", "json", "run", "--case", str(sample_project_dir)],
            )

        parsed = json.loads(result.output.strip())
        assert parsed["status"] == "error"
        assert parsed["metadata"]["error_category"] == "config_error"
        assert result.exit_code == 2
