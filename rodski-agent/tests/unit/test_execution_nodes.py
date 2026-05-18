"""Unit tests for rodski_agent.execution.nodes"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# pre_check
# ---------------------------------------------------------------------------

def test_pre_check_missing_case_path(tmp_path):
    from rodski_agent.execution.nodes import pre_check

    state = {"case_path": str(tmp_path / "nonexistent")}
    result = pre_check(state)

    assert result["status"] == "error"
    assert "not found" in result["error"].lower() or "nonexistent" in result["error"]


# ---------------------------------------------------------------------------
# parse_result
# ---------------------------------------------------------------------------

def test_parse_result_all_pass():
    from rodski_agent.execution.nodes import parse_result

    state = {
        "execution_result": {
            "exit_code": 0,
            "result_dir": None,
            "result_files": [],
            "stderr": "",
        }
    }
    result = parse_result(state)
    case_results = result["case_results"]
    has_failures = any(c.get("status") != "PASS" for c in case_results)
    assert not has_failures


def test_parse_result_has_failures():
    from rodski_agent.execution.nodes import parse_result

    state = {
        "execution_result": {
            "exit_code": 1,
            "result_dir": None,
            "result_files": [],
            "stderr": "assertion failed",
        }
    }
    result = parse_result(state)
    case_results = result["case_results"]
    has_failures = any(c.get("status") != "PASS" for c in case_results)
    assert has_failures


# ---------------------------------------------------------------------------
# diagnose
# ---------------------------------------------------------------------------

def test_diagnose_sets_diagnosis():
    from rodski_agent.execution.nodes import diagnose

    fake_response = '{"category": "timeout", "root_cause": "slow network", "suggestion": "add wait", "confidence": "high"}'

    with patch("rodski_agent.execution.nodes.diagnose") as _:
        pass  # just ensure import works

    with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=fake_response), \
         patch("rodski_agent.execution.nodes.call_llm_text", return_value=fake_response, create=True):

        # Patch at the module level where it's imported
        with patch("rodski_agent.execution.nodes.__builtins__", {}):
            pass

    # Use importlib to patch inside the function scope
    import importlib
    import rodski_agent.execution.nodes as nodes_mod

    with patch.object(nodes_mod, "diagnose", wraps=nodes_mod.diagnose):
        with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=fake_response):
            state = {
                "case_results": [
                    {"id": "c001", "status": "FAIL", "error": "timeout", "action": "click", "model": "login"}
                ],
                "screenshots": [],
            }
            # Patch call_llm_text inside the nodes module's closure
            import sys
            llm_mod = sys.modules.get("rodski_agent.common.llm_bridge")
            if llm_mod:
                original = llm_mod.call_llm_text
                llm_mod.call_llm_text = MagicMock(return_value=fake_response)
                try:
                    result = nodes_mod.diagnose(state)
                finally:
                    llm_mod.call_llm_text = original
            else:
                # llm_bridge not yet imported; patch via sys.modules stub
                fake_llm = MagicMock()
                fake_llm.call_llm_text = MagicMock(return_value=fake_response)
                fake_errors = MagicMock()
                fake_errors.LLMError = Exception
                fake_prompts = MagicMock()
                fake_prompts.DIAGNOSE_SYSTEM_PROMPT = "sys"
                fake_prompts.DIAGNOSE_USER_TEMPLATE = (
                    "case:{case_id} err:{error_message} act:{action} mod:{model} ss:{screenshot_desc}"
                )
                sys.modules.setdefault("rodski_agent.common.llm_bridge", fake_llm)
                sys.modules.setdefault("rodski_agent.common.errors", fake_errors)
                sys.modules.setdefault("rodski_agent.execution.prompts", fake_prompts)
                result = nodes_mod.diagnose(state)

    assert "diagnosis" in result
    diag = result["diagnosis"]
    assert not diag.get("skipped", True), f"diagnosis was skipped: {diag}"
    assert "cases" in diag
    assert len(diag["cases"]) == 1
