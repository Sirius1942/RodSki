"""诊断功能单元测试。

覆盖:
  - diagnose 节点 with mock LLM
  - LLM 失败直接报错
  - 诊断提示词包含必要元素
  - 更新后的执行图包含 diagnose 节点
  - diagnose CLI 命令
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from rodski_agent.cli import main
from rodski_agent.execution.nodes import (
    diagnose,
    _parse_diagnosis_response,
    _enforce_confidence_rule,
)
from rodski_agent.execution.prompts import (
    DIAGNOSE_SYSTEM_PROMPT,
    DIAGNOSE_USER_TEMPLATE,
    COMMON_FAILURE_PATTERNS,
)
from rodski_agent.execution.graph import build_execution_graph, _parse_result_router
from rodski_agent.common.errors import LLMError


# ================================================================
# T04-006a: diagnose 节点 with mock LLM
# ================================================================


class TestDiagnoseNodeWithMockLLM:
    """使用 mock LLM 测试 diagnose 节点。"""

    def _mock_llm_response(self) -> str:
        """构造一个合法的 LLM 诊断响应。"""
        return json.dumps({
            "root_cause": "ElementNotFound: 登录按钮定位器过期",
            "confidence": 0.85,
            "category": "CASE_DEFECT",
            "suggestion": "更新登录按钮的 CSS selector",
            "evidence": "错误日志显示 selector #login-btn 未找到",
            "recommended_action": "insert",
        })

    def test_diagnose_with_mock_llm(self):
        """Mock LLM 返回合法 JSON 时，diagnose 应产生正确结果。"""
        state = {
            "case_results": [
                {"id": "c001", "status": "FAIL", "error": "ElementNotFound: #login-btn"},
            ],
            "screenshots": [],
        }
        with patch(
            "rodski_agent.common.llm_bridge.call_llm_text",
            return_value=self._mock_llm_response(),
        ):
            result = diagnose(state)

        diag = result["diagnosis"]
        assert diag["skipped"] is False
        assert len(diag["cases"]) == 1
        case_diag = diag["cases"][0]
        assert case_diag["case_id"] == "c001"
        assert case_diag["category"] == "CASE_DEFECT"
        assert case_diag["confidence"] == 0.85
        assert case_diag["recommended_action"] == "insert"

    def test_diagnose_multiple_failures(self):
        """多个失败用例应逐个诊断。"""
        state = {
            "case_results": [
                {"id": "c001", "status": "FAIL", "error": "timeout"},
                {"id": "c002", "status": "PASS"},
                {"id": "c003", "status": "FAIL", "error": "assertion failed"},
            ],
            "screenshots": [],
        }
        with patch(
            "rodski_agent.common.llm_bridge.call_llm_text",
            return_value=self._mock_llm_response(),
        ):
            result = diagnose(state)

        diag = result["diagnosis"]
        assert diag["skipped"] is False
        # Only 2 failures (c002 is PASS)
        assert len(diag["cases"]) == 2
        case_ids = [c["case_id"] for c in diag["cases"]]
        assert "c001" in case_ids
        assert "c003" in case_ids
        assert "c002" not in case_ids

    def test_diagnose_no_failures(self):
        """所有用例通过时，diagnose 应跳过。"""
        state = {
            "case_results": [
                {"id": "c001", "status": "PASS"},
                {"id": "c002", "status": "PASS"},
            ],
        }
        result = diagnose(state)
        assert result["diagnosis"]["skipped"] is True
        assert "No failed" in result["diagnosis"]["reason"]

    def test_diagnose_empty_results(self):
        """无用例结果时，diagnose 应跳过。"""
        result = diagnose({"case_results": []})
        assert result["diagnosis"]["skipped"] is True

    def test_diagnose_with_screenshots(self):
        """有截图时，prompt 中应包含截图描述。"""
        state = {
            "case_results": [
                {"id": "c001", "status": "FAIL", "error": "error"},
            ],
            "screenshots": ["/tmp/step1.png", "/tmp/step2.png"],
        }
        captured_prompt = []

        def mock_call(prompt, agent_type="design"):
            captured_prompt.append(prompt)
            return self._mock_llm_response()

        with patch("rodski_agent.common.llm_bridge.call_llm_text", side_effect=mock_call):
            diagnose(state)

        assert len(captured_prompt) == 1
        assert "step1.png" in captured_prompt[0]
        assert "2 张截图" in captured_prompt[0]


# ================================================================
# T04-006b: LLM 失败直接报错
# ================================================================


class TestDiagnoseLLMError:
    """LLM 不可用时直接报错。"""

    def test_llm_error_propagates(self):
        """LLM 错误应直接抛出 LLMError。"""
        state = {
            "case_results": [
                {"id": "c001", "status": "FAIL", "error": "some error"},
            ],
            "screenshots": [],
        }
        with patch(
            "rodski_agent.common.llm_bridge.call_llm_text",
            side_effect=LLMError("No API key", code="E_LLM_KEY_MISSING"),
        ):
            with pytest.raises(LLMError):
                diagnose(state)


# ================================================================
# T04-006c: 诊断提示词包含必要元素
# ================================================================


class TestDiagnosisPrompts:
    """诊断提示词完整性测试。"""

    def test_system_prompt_contains_constraint_summary(self):
        """系统提示词应嵌入 RODSKI_CONSTRAINT_SUMMARY。"""
        from rodski_agent.common.rodski_knowledge import RODSKI_CONSTRAINT_SUMMARY

        assert "RodSki 框架约束摘要" in DIAGNOSE_SYSTEM_PROMPT
        # Verify key constraint sections are present
        assert "关键字规则" in DIAGNOSE_SYSTEM_PROMPT
        assert "Case XML 格式" in DIAGNOSE_SYSTEM_PROMPT
        assert "目录结构" in DIAGNOSE_SYSTEM_PROMPT

    def test_system_prompt_contains_failure_patterns(self):
        """系统提示词应包含常见失败模式映射。"""
        assert "常见失败模式映射" in DIAGNOSE_SYSTEM_PROMPT
        assert "ElementNotFound" in DIAGNOSE_SYSTEM_PROMPT
        assert "CASE_DEFECT" in DIAGNOSE_SYSTEM_PROMPT
        assert "ENV_DEFECT" in DIAGNOSE_SYSTEM_PROMPT
        assert "PRODUCT_DEFECT" in DIAGNOSE_SYSTEM_PROMPT

    def test_system_prompt_output_format(self):
        """系统提示词应定义 JSON 输出格式。"""
        assert "root_cause" in DIAGNOSE_SYSTEM_PROMPT
        assert "confidence" in DIAGNOSE_SYSTEM_PROMPT
        assert "category" in DIAGNOSE_SYSTEM_PROMPT
        assert "suggestion" in DIAGNOSE_SYSTEM_PROMPT
        assert "evidence" in DIAGNOSE_SYSTEM_PROMPT
        assert "recommended_action" in DIAGNOSE_SYSTEM_PROMPT

    def test_system_prompt_confidence_rule(self):
        """系统提示词应包含置信度规则。"""
        assert "confidence < 0.6" in DIAGNOSE_SYSTEM_PROMPT
        assert "pause" in DIAGNOSE_SYSTEM_PROMPT
        assert "escalate" in DIAGNOSE_SYSTEM_PROMPT

    def test_user_template_placeholders(self):
        """用户提示词模板应包含所有占位符。"""
        assert "{case_id}" in DIAGNOSE_USER_TEMPLATE
        assert "{error_message}" in DIAGNOSE_USER_TEMPLATE
        assert "{action}" in DIAGNOSE_USER_TEMPLATE
        assert "{model}" in DIAGNOSE_USER_TEMPLATE
        assert "{screenshot_desc}" in DIAGNOSE_USER_TEMPLATE

    def test_user_template_formatting(self):
        """用户提示词模板应可正常格式化。"""
        formatted = DIAGNOSE_USER_TEMPLATE.format(
            case_id="c001",
            error_message="timeout",
            action="type",
            model="login_model",
            screenshot_desc="无截图",
        )
        assert "c001" in formatted
        assert "timeout" in formatted
        assert "type" in formatted
        assert "login_model" in formatted
        assert "无截图" in formatted


# ================================================================
# T04-006d: 执行图包含 diagnose 节点
# ================================================================


class TestExecutionGraphWithDiagnose:
    """更新后的执行图测试。"""

    def test_parse_result_router_failures(self):
        """有失败用例时，路由到 diagnose。"""
        state = {
            "case_results": [
                {"id": "c001", "status": "PASS"},
                {"id": "c002", "status": "FAIL"},
            ]
        }
        assert _parse_result_router(state) == "diagnose"

    def test_parse_result_router_all_pass(self):
        """全部通过时，路由到 report。"""
        state = {
            "case_results": [
                {"id": "c001", "status": "PASS"},
                {"id": "c002", "status": "PASS"},
            ]
        }
        assert _parse_result_router(state) == "report"

    def test_parse_result_router_empty(self):
        """空结果时，路由到 report（无失败）。"""
        assert _parse_result_router({"case_results": []}) == "report"

    def test_graph_all_pass_skips_diagnose(self):
        """全通过时，diagnose 节点不应被执行。"""
        call_log = []

        def mock_pre_check(s):
            call_log.append("pre_check")
            return {"status": "running"}

        def mock_execute(s):
            call_log.append("execute")
            return {"execution_result": {"exit_code": 0}}

        def mock_parse_result(s):
            call_log.append("parse_result")
            return {"case_results": [{"id": "c001", "status": "PASS"}]}

        def mock_diagnose(s):
            call_log.append("diagnose")
            return {"diagnosis": {"skipped": True}}

        def mock_report(s):
            call_log.append("report")
            return {"report": {"total": 1, "passed": 1, "failed": 0}, "status": "pass"}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result, mock_diagnose, mock_report
        )
        result = g.invoke({"case_path": "/fake", "headless": True})

        assert "diagnose" not in call_log
        assert result["status"] == "pass"

    def test_graph_with_failure_runs_diagnose(self):
        """有失败用例时，diagnose 节点应被执行。"""
        call_log = []

        def mock_pre_check(s):
            call_log.append("pre_check")
            return {"status": "running"}

        def mock_execute(s):
            call_log.append("execute")
            return {"execution_result": {"exit_code": 1}}

        def mock_parse_result(s):
            call_log.append("parse_result")
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "timeout"}]}

        def mock_diagnose(s):
            call_log.append("diagnose")
            return {"diagnosis": {"cases": [{"case_id": "c001", "category": "ENV_DEFECT"}], "skipped": False}}

        def mock_report(s):
            call_log.append("report")
            cases = s.get("case_results", [])
            failed = sum(1 for c in cases if c.get("status") != "PASS")
            return {"report": {"total": len(cases), "passed": 0, "failed": failed}, "status": "fail"}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result, mock_diagnose, mock_report
        )
        result = g.invoke({"case_path": "/fake", "headless": True})

        assert "diagnose" in call_log
        assert result["status"] == "fail"
        assert result.get("diagnosis") is not None
        assert result["diagnosis"]["skipped"] is False

    def test_graph_pre_check_error_skips_all(self):
        """pre_check 失败时，execute/parse_result/diagnose 都应跳过。"""
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

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result, mock_diagnose, mock_report
        )
        result = g.invoke({"case_path": "/bad"})

        assert "pre_check" in call_log
        assert "report" in call_log
        assert "execute" not in call_log
        assert "diagnose" not in call_log


# ================================================================
# T04-006e: 诊断结果解析与规则
# ================================================================


class TestDiagnosisResultParsing:
    """诊断结果解析和规则执行测试。"""

    def test_parse_valid_json(self):
        """合法 JSON 应正确解析。"""
        response = json.dumps({
            "root_cause": "selector expired",
            "confidence": 0.9,
            "category": "CASE_DEFECT",
            "suggestion": "update selector",
            "evidence": "log shows #btn not found",
            "recommended_action": "insert",
        })
        result = _parse_diagnosis_response(response)
        assert result["category"] == "CASE_DEFECT"
        assert result["confidence"] == 0.9

    def test_parse_json_in_markdown_block(self):
        """从 markdown 代码块中提取 JSON。"""
        response = '```json\n{"root_cause":"x","confidence":0.7,"category":"ENV_DEFECT","suggestion":"y","evidence":"z","recommended_action":"pause"}\n```'
        result = _parse_diagnosis_response(response)
        assert result["category"] == "ENV_DEFECT"

    def test_parse_invalid_json_fallback(self):
        """非 JSON 文本应降级为 UNKNOWN。"""
        result = _parse_diagnosis_response("This is not JSON at all")
        assert result["category"] == "UNKNOWN"
        assert result["confidence"] < 0.6
        assert result["recommended_action"] in ("pause", "escalate")

    def test_parse_missing_fields(self):
        """缺少字段时应补充默认值。"""
        response = json.dumps({"root_cause": "something"})
        result = _parse_diagnosis_response(response)
        assert "category" in result
        assert "confidence" in result
        assert "recommended_action" in result

    def test_parse_invalid_category(self):
        """非法 category 应被纠正为 UNKNOWN。"""
        response = json.dumps({
            "root_cause": "x", "confidence": 0.5,
            "category": "INVALID_TYPE",
            "suggestion": "y", "evidence": "z",
            "recommended_action": "pause",
        })
        result = _parse_diagnosis_response(response)
        assert result["category"] == "UNKNOWN"

    def test_confidence_rule_low_confidence(self):
        """confidence < 0.6 时，recommended_action 只能是 pause 或 escalate。"""
        diag = {
            "confidence": 0.4,
            "recommended_action": "insert",
        }
        result = _enforce_confidence_rule(diag)
        assert result["recommended_action"] == "pause"

    def test_confidence_rule_high_confidence(self):
        """confidence >= 0.6 时，recommended_action 不受限制。"""
        diag = {
            "confidence": 0.8,
            "recommended_action": "insert",
        }
        result = _enforce_confidence_rule(diag)
        assert result["recommended_action"] == "insert"

    def test_confidence_rule_boundary(self):
        """confidence == 0.6 时（边界），recommended_action 不受限制。"""
        diag = {
            "confidence": 0.6,
            "recommended_action": "terminate",
        }
        result = _enforce_confidence_rule(diag)
        assert result["recommended_action"] == "terminate"


# ================================================================
# T04-006f: diagnose CLI 命令
# ================================================================


class TestDiagnoseCLI:
    """diagnose CLI 命令测试。"""

    def test_diagnose_help(self, cli_runner: CliRunner):
        """diagnose --help 应显示帮助文本。"""
        result = cli_runner.invoke(main, ["diagnose", "--help"])
        assert result.exit_code == 0
        assert "--result" in result.output

    def test_diagnose_nonexistent_path(self, cli_runner: CliRunner, tmp_path):
        """不存在的路径应报错。"""
        result = cli_runner.invoke(
            main, ["--format", "json", "diagnose", "--result", str(tmp_path / "nonexistent")]
        )
        parsed = json.loads(result.output.strip())
        assert parsed["status"] == "error"

    def test_diagnose_with_all_pass(self, cli_runner: CliRunner, tmp_path):
        """所有用例通过时，diagnose 应跳过。"""
        summary = {
            "cases": [
                {"case_id": "c001", "title": "Login", "status": "PASS"},
            ]
        }
        (tmp_path / "execution_summary.json").write_text(json.dumps(summary))

        result = cli_runner.invoke(
            main, ["--format", "json", "diagnose", "--result", str(tmp_path)]
        )

        parsed = json.loads(result.output.strip())
        assert parsed["status"] == "success"
        assert parsed["output"]["skipped"] is True


# ================================================================
# T04-006g: LLM Bridge 测试
# ================================================================


class TestLLMBridge:
    """LLM 桥接层测试。"""

    def test_llm_error_is_importable(self):
        """LLMError 应可正常导入。"""
        from rodski_agent.common.errors import LLMError
        assert issubclass(LLMError, Exception)

    def test_get_chat_model_raises_without_api_key(self, monkeypatch):
        """API key 缺失时，get_chat_model 应抛 LLMError。"""
        from rodski_agent.common.llm_bridge import get_chat_model, reset_cache
        reset_cache()
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(LLMError, match="API key not found"):
            get_chat_model("design")

    def test_call_llm_text_raises_on_error(self, monkeypatch):
        """LLM 调用失败时，call_llm_text 应抛 LLMError。"""
        from rodski_agent.common.llm_bridge import call_llm_text, reset_cache
        reset_cache()
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(LLMError):
            call_llm_text("test prompt")

    def test_analyze_screenshot_raises_on_error(self, monkeypatch):
        """LLM 不可用时，analyze_screenshot 应抛 LLMError。"""
        from rodski_agent.common.llm_bridge import analyze_screenshot, reset_cache
        reset_cache()
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(LLMError):
            analyze_screenshot("/fake/image.png", "What is shown?")
