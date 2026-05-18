"""Unit tests for rodski_agent.execution.fixer"""
import os
import shutil
import xml.etree.ElementTree as ET
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_case_xml(tmp_path):
    """Create a minimal module dir with a case XML file."""
    module = tmp_path / "mod"
    case_dir = module / "case"
    case_dir.mkdir(parents=True)
    case_file = case_dir / "test.xml"
    case_file.write_text(
        '<?xml version="1.0"?>'
        '<cases>'
        '<testcase id="c001">'
        '<step><action>click</action><phase>pre_process</phase></step>'
        '<step><action>click</action><phase>test_case</phase></step>'
        '</testcase>'
        '</cases>',
        encoding="utf-8",
    )
    return str(case_file), str(module)


# ---------------------------------------------------------------------------
# test_wait_fix_inserts_wait_step
# ---------------------------------------------------------------------------

def test_wait_fix_inserts_wait_step(tmp_path):
    case_file, module_dir = _make_case_xml(tmp_path)

    with patch("rodski_agent.execution.fixer.validate_action", return_value=True):
        from rodski_agent.execution.fixer import apply_fix

        state = {
            "case_path": module_dir,
            "diagnosis": {
                "category": "timeout",
                "root_cause": "timeout waiting for element",
                "suggestion": "add wait",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)

    assert result["fixes_applied"], "should have at least one fix entry"
    assert any("wait" in f for f in result["fixes_applied"])

    # Verify wait step was inserted into the XML
    tree = ET.parse(case_file)
    actions = [s.findtext("action") for s in tree.getroot().findall(".//step")]
    assert "wait" in actions


# ---------------------------------------------------------------------------
# test_wait_fix_creates_backup
# ---------------------------------------------------------------------------

def test_wait_fix_creates_backup(tmp_path):
    case_file, module_dir = _make_case_xml(tmp_path)

    with patch("rodski_agent.execution.fixer.validate_action", return_value=True):
        from rodski_agent.execution.fixer import apply_fix

        state = {
            "case_path": module_dir,
            "diagnosis": {
                "category": "timeout",
                "root_cause": "timeout",
                "suggestion": "",
            },
            "fixes_applied": [],
        }
        apply_fix(state)

    assert os.path.exists(case_file + ".bak"), ".bak backup should be created"


# ---------------------------------------------------------------------------
# test_fallback_when_no_strategy_matches
# ---------------------------------------------------------------------------

def test_fallback_when_no_strategy_matches(tmp_path):
    with patch("rodski_agent.execution.fixer.validate_action", return_value=True):
        from rodski_agent.execution.fixer import apply_fix

        state = {
            "case_path": str(tmp_path / "nonexistent"),
            "diagnosis": {
                "category": "unknown",
                "root_cause": "something completely unrelated",
                "suggestion": "",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)  # must not raise

    assert isinstance(result, dict)
    assert result.get("status") == "running"


# ---------------------------------------------------------------------------
# test_fix_result_structure
# ---------------------------------------------------------------------------

def test_fix_result_structure(tmp_path):
    with patch("rodski_agent.execution.fixer.validate_action", return_value=True):
        from rodski_agent.execution.fixer import apply_fix

        state = {
            "case_path": str(tmp_path),
            "diagnosis": {
                "category": "timeout",
                "root_cause": "timeout",
                "suggestion": "wait more",
            },
            "fixes_applied": [],
        }
        result = apply_fix(state)

    assert "fixes_applied" in result
    assert "status" in result
    assert isinstance(result["fixes_applied"], list)
