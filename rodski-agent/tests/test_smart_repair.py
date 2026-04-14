"""智能修复策略单元测试 (Iteration 09)。

覆盖:
  - apply_fix 主入口的策略分发
  - wait 修复策略（XML 修改 + 降级）
  - locator 修复策略（LLM + fallback）
  - data 修复策略（LLM + fallback）
  - 辅助函数（文件查找、备份、XML 修改）
  - 端到端修复重试流程
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

import pytest

from rodski_agent.execution.fixer import (
    apply_fix,
    _apply_wait_fix,
    _apply_locator_fix,
    _apply_data_fix,
    _insert_wait_step,
    _update_model_locator,
    _update_data_value,
    _find_case_xml_files,
    _find_model_xml_files,
    _find_data_xml_files,
    _backup_file,
)


# ============================================================
# Helper: create standard project structure with XML files
# ============================================================


def _create_project(tmp_path, case_xml=None, model_xml=None, data_xml=None):
    """Create standard project dir with case/model/data XML files."""
    case_dir = tmp_path / "case"
    model_dir = tmp_path / "model"
    data_dir = tmp_path / "data"
    case_dir.mkdir()
    model_dir.mkdir()
    data_dir.mkdir()

    if case_xml:
        (case_dir / "c001.xml").write_text(case_xml, encoding="utf-8")
    if model_xml:
        (model_dir / "model.xml").write_text(model_xml, encoding="utf-8")
    if data_xml:
        (data_dir / "data.xml").write_text(data_xml, encoding="utf-8")

    return str(tmp_path)


SAMPLE_CASE_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testcases>
  <testcase id="c001" title="Login Test">
    <step>
      <action>open</action>
      <data>https://example.com</data>
      <phase>setup</phase>
    </step>
    <step>
      <action>type</action>
      <model>username</model>
      <data>admin</data>
      <phase>test_case</phase>
    </step>
    <step>
      <action>click</action>
      <model>login_btn</model>
      <phase>test_case</phase>
    </step>
  </testcase>
</testcases>
"""

SAMPLE_MODEL_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<models>
  <model name="login_page">
    <element name="username">
      <location type="id">user-input</location>
    </element>
    <element name="login_btn">
      <location type="css">.btn-login</location>
    </element>
  </model>
</models>
"""

SAMPLE_DATA_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<datatables>
  <datatable name="login_data">
    <row id="r001">
      <username>admin</username>
      <password>old_password</password>
    </row>
  </datatable>
</datatables>
"""


# ============================================================
# apply_fix main entry tests
# ============================================================


class TestApplyFix:
    """apply_fix 主入口测试。"""

    def test_timeout_strategy_selected(self, tmp_path):
        """timeout root_cause → wait fix strategy."""
        project_dir = _create_project(tmp_path, case_xml=SAMPLE_CASE_XML)
        state = {
            "diagnosis": {"root_cause": "Timeout waiting for element", "suggestion": "add wait"},
            "fixes_applied": [],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "wait" in result["fixes_applied"][0].lower()
        assert result["status"] == "running"

    def test_timeout_chinese_strategy(self, tmp_path):
        """中文「超时」→ wait fix strategy."""
        project_dir = _create_project(tmp_path, case_xml=SAMPLE_CASE_XML)
        state = {
            "diagnosis": {"root_cause": "页面加载超时", "suggestion": "增加等待"},
            "fixes_applied": [],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "wait" in result["fixes_applied"][0].lower()

    def test_element_strategy_selected(self, tmp_path):
        """element root_cause → locator fix strategy."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        state = {
            "diagnosis": {"root_cause": "Element not found: login_btn", "suggestion": "update selector"},
            "fixes_applied": [],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "locator" in result["fixes_applied"][0].lower()

    def test_locator_strategy_selected(self):
        """locator root_cause → locator fix strategy."""
        state = {
            "diagnosis": {"root_cause": "Invalid locator type", "suggestion": "use css"},
            "fixes_applied": [],
            "case_path": "",
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "locator" in result["fixes_applied"][0].lower()

    def test_chinese_element_strategy(self, tmp_path):
        """中文「元素」→ locator fix strategy."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        state = {
            "diagnosis": {"root_cause": "找不到元素", "suggestion": "检查定位器"},
            "fixes_applied": [],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1

    def test_chinese_locator_strategy(self, tmp_path):
        """中文「定位」→ locator fix strategy."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        state = {
            "diagnosis": {"root_cause": "元素定位失败", "suggestion": "更新定位器"},
            "fixes_applied": [],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1

    def test_data_strategy_selected(self, tmp_path):
        """data root_cause → data fix strategy."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        state = {
            "diagnosis": {"root_cause": "Test data mismatch", "suggestion": "update password"},
            "fixes_applied": [],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1
        assert "data" in result["fixes_applied"][0].lower()

    def test_chinese_data_strategy(self, tmp_path):
        """中文「数据」→ data fix strategy."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        state = {
            "diagnosis": {"root_cause": "测试数据不正确", "suggestion": "更新密码"},
            "fixes_applied": [],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1

    def test_value_strategy(self, tmp_path):
        """value/值 root_cause → data fix strategy."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        state = {
            "diagnosis": {"root_cause": "Expected value mismatch", "suggestion": "fix value"},
            "fixes_applied": [],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 1

    def test_unknown_cause_no_fix(self):
        """Unrecognized root_cause → no fix applied."""
        state = {
            "diagnosis": {"root_cause": "assertion failed", "suggestion": "check logic"},
            "fixes_applied": [],
            "case_path": "",
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 0
        assert result["status"] == "running"

    def test_preserves_existing_fixes(self, tmp_path):
        """Previous fixes are preserved."""
        project_dir = _create_project(tmp_path, case_xml=SAMPLE_CASE_XML)
        state = {
            "diagnosis": {"root_cause": "Timeout", "suggestion": "wait"},
            "fixes_applied": ["prev_fix_1", "prev_fix_2"],
            "case_path": project_dir,
        }
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 3
        assert result["fixes_applied"][0] == "prev_fix_1"

    def test_empty_diagnosis(self):
        """Empty diagnosis → no fix."""
        state = {"diagnosis": {}, "fixes_applied": [], "case_path": ""}
        result = apply_fix(state)
        assert len(result["fixes_applied"]) == 0


# ============================================================
# Wait fix strategy tests
# ============================================================


class TestWaitFix:
    """wait 修复策略测试。"""

    def test_insert_wait_step_into_xml(self, tmp_path):
        """Wait step is inserted into case XML."""
        project_dir = _create_project(tmp_path, case_xml=SAMPLE_CASE_XML)
        case_file = os.path.join(project_dir, "case", "c001.xml")

        result = _insert_wait_step(case_file, wait_seconds=5)
        assert result is True

        # Verify the XML was modified
        tree = ET.parse(case_file)
        root = tree.getroot()
        steps = root.findall(".//testcase/step")
        actions = [s.findtext("action", "") for s in steps]
        assert "wait" in actions

    def test_insert_wait_creates_backup(self, tmp_path):
        """Wait insertion creates .bak backup."""
        project_dir = _create_project(tmp_path, case_xml=SAMPLE_CASE_XML)
        case_file = os.path.join(project_dir, "case", "c001.xml")

        _insert_wait_step(case_file, wait_seconds=3)
        assert os.path.exists(case_file + ".bak")

    def test_wait_fix_no_case_files(self, tmp_path):
        """No case files → fallback description."""
        project_dir = str(tmp_path / "empty")
        os.makedirs(project_dir, exist_ok=True)
        result = _apply_wait_fix(project_dir, {"root_cause": "timeout"})
        assert result is not None
        assert "no XML found" in result

    def test_wait_fix_empty_case_path(self):
        """Empty case_path → fallback."""
        result = _apply_wait_fix("", {"root_cause": "timeout"})
        assert result is not None

    def test_insert_wait_invalid_xml(self, tmp_path):
        """Invalid XML → returns False."""
        bad_file = tmp_path / "bad.xml"
        bad_file.write_text("not xml at all", encoding="utf-8")
        result = _insert_wait_step(str(bad_file))
        assert result is False

    def test_insert_wait_no_testcases(self, tmp_path):
        """XML without testcase elements → returns False."""
        xml_content = '<?xml version="1.0"?><root><something/></root>'
        xml_file = tmp_path / "empty_tc.xml"
        xml_file.write_text(xml_content, encoding="utf-8")
        result = _insert_wait_step(str(xml_file))
        assert result is False


# ============================================================
# Locator fix strategy tests
# ============================================================


class TestLocatorFix:
    """locator 修复策略测试。"""

    def test_update_model_locator(self, tmp_path):
        """Update locator in model XML."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        model_file = os.path.join(project_dir, "model", "model.xml")

        result = _update_model_locator(model_file, "username", "css", "#new-input")
        assert result is True

        # Verify
        tree = ET.parse(model_file)
        root = tree.getroot()
        for elem in root.iter("element"):
            if elem.get("name") == "username":
                loc = elem.find("location")
                assert loc is not None
                assert loc.get("type") == "css"
                assert loc.text == "#new-input"

    def test_update_creates_backup(self, tmp_path):
        """Locator update creates .bak backup."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        model_file = os.path.join(project_dir, "model", "model.xml")

        _update_model_locator(model_file, "username", "css", "#new")
        assert os.path.exists(model_file + ".bak")

    def test_update_nonexistent_element(self, tmp_path):
        """Non-existent element → returns False."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        model_file = os.path.join(project_dir, "model", "model.xml")

        result = _update_model_locator(model_file, "nonexistent", "css", "#foo")
        assert result is False

    def test_update_invalid_locator_type(self, tmp_path):
        """Invalid locator type in LLM fix → not applied."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        diagnosis = {
            "root_cause": "Element not found",
            "suggestion": "update selector",
        }

        llm_response = '{"element_name": "username", "locator_type": "invalid_type", "locator_value": "#x"}'
        with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=llm_response):
            result = _apply_locator_fix(project_dir, diagnosis)

        # Should fallback to suggestion since invalid locator type
        assert "locator_fix_suggested" in result

    def test_llm_locator_fix_success(self, tmp_path):
        """LLM returns valid fix → applied to model XML."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        diagnosis = {
            "root_cause": "Element not found: login_btn",
            "suggestion": "update CSS selector",
        }

        llm_response = '{"element_name": "login_btn", "locator_type": "css", "locator_value": "#new-login-btn"}'
        with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=llm_response):
            result = _apply_locator_fix(project_dir, diagnosis)

        assert result is not None
        assert "locator_fixed" in result
        assert "login_btn" in result

    def test_llm_unavailable_fallback(self, tmp_path):
        """LLM not available → fallback to suggestion recording."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        diagnosis = {
            "root_cause": "Element not found",
            "suggestion": "use XPath instead",
        }

        with patch("rodski_agent.common.llm_bridge.call_llm_text", side_effect=Exception("LLM down")):
            result = _apply_locator_fix(project_dir, diagnosis)

        assert "locator_fix_suggested" in result
        assert "XPath" in result

    def test_no_model_files(self, tmp_path):
        """No model directory → fallback."""
        project_dir = str(tmp_path / "nomodel")
        os.makedirs(project_dir, exist_ok=True)
        diagnosis = {"root_cause": "Element error", "suggestion": "fix it"}
        result = _apply_locator_fix(project_dir, diagnosis)
        assert "locator_fix_suggested" in result


# ============================================================
# Data fix strategy tests
# ============================================================


class TestDataFix:
    """data 修复策略测试。"""

    def test_update_data_value(self, tmp_path):
        """Update data value in data XML."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        data_file = os.path.join(project_dir, "data", "data.xml")

        result = _update_data_value(data_file, "password", "old_password", "new_password")
        assert result is True

        # Verify
        tree = ET.parse(data_file)
        root = tree.getroot()
        for elem in root.iter("password"):
            assert elem.text == "new_password"

    def test_update_data_creates_backup(self, tmp_path):
        """Data update creates .bak backup."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        data_file = os.path.join(project_dir, "data", "data.xml")

        _update_data_value(data_file, "password", "old_password", "new_pw")
        assert os.path.exists(data_file + ".bak")

    def test_update_nonexistent_field(self, tmp_path):
        """Non-existent field → returns False."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        data_file = os.path.join(project_dir, "data", "data.xml")

        result = _update_data_value(data_file, "nonexistent_field", "", "value")
        assert result is False

    def test_update_with_old_value_mismatch(self, tmp_path):
        """old_value doesn't match → returns False."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        data_file = os.path.join(project_dir, "data", "data.xml")

        result = _update_data_value(data_file, "password", "wrong_old_value", "new_value")
        assert result is False

    def test_update_without_old_value(self, tmp_path):
        """Empty old_value → match first occurrence."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        data_file = os.path.join(project_dir, "data", "data.xml")

        result = _update_data_value(data_file, "password", "", "new_password")
        assert result is True

    def test_llm_data_fix_success(self, tmp_path):
        """LLM returns valid data fix → applied."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        diagnosis = {
            "root_cause": "Test data mismatch",
            "suggestion": "update password to correct value",
        }

        llm_response = '{"field_name": "password", "old_value": "old_password", "new_value": "correct_password"}'
        with patch("rodski_agent.common.llm_bridge.call_llm_text", return_value=llm_response):
            result = _apply_data_fix(project_dir, diagnosis)

        assert result is not None
        assert "data_fixed" in result
        assert "correct_password" in result

    def test_llm_data_fix_failure(self, tmp_path):
        """LLM fails → fallback to suggestion."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        diagnosis = {
            "root_cause": "Test data error",
            "suggestion": "update data values",
        }

        with patch("rodski_agent.common.llm_bridge.call_llm_text", side_effect=Exception("LLM down")):
            result = _apply_data_fix(project_dir, diagnosis)

        assert "data_fix_suggested" in result

    def test_no_data_files(self, tmp_path):
        """No data directory → fallback."""
        project_dir = str(tmp_path / "nodata")
        os.makedirs(project_dir, exist_ok=True)
        diagnosis = {"root_cause": "Data error", "suggestion": "fix it"}
        result = _apply_data_fix(project_dir, diagnosis)
        assert "data_fix_suggested" in result


# ============================================================
# File discovery tests
# ============================================================


class TestFileDiscovery:
    """文件查找辅助函数测试。"""

    def test_find_case_files(self, tmp_path):
        """Find case XML files in project dir."""
        project_dir = _create_project(tmp_path, case_xml=SAMPLE_CASE_XML)
        files = _find_case_xml_files(project_dir)
        assert len(files) == 1
        assert files[0].endswith(".xml")

    def test_find_model_files(self, tmp_path):
        """Find model XML files in project dir."""
        project_dir = _create_project(tmp_path, model_xml=SAMPLE_MODEL_XML)
        files = _find_model_xml_files(project_dir)
        assert len(files) == 1

    def test_find_data_files(self, tmp_path):
        """Find data XML files in project dir."""
        project_dir = _create_project(tmp_path, data_xml=SAMPLE_DATA_XML)
        files = _find_data_xml_files(project_dir)
        assert len(files) == 1

    def test_find_from_file_path(self, tmp_path):
        """Find files when case_path is a file (not dir)."""
        project_dir = _create_project(tmp_path, case_xml=SAMPLE_CASE_XML)
        case_file = os.path.join(project_dir, "case", "c001.xml")
        files = _find_case_xml_files(case_file)
        assert len(files) == 1

    def test_find_empty_dir(self, tmp_path):
        """Empty project dir → no files."""
        assert _find_case_xml_files(str(tmp_path)) == []

    def test_find_nonexistent_path(self):
        """Non-existent path → empty list."""
        assert _find_case_xml_files("/nonexistent/path") == []

    def test_find_empty_string(self):
        """Empty string → empty list."""
        assert _find_case_xml_files("") == []

    def test_find_multiple_files(self, tmp_path):
        """Multiple XML files → sorted list."""
        case_dir = tmp_path / "case"
        case_dir.mkdir()
        (case_dir / "a.xml").write_text("<x/>", encoding="utf-8")
        (case_dir / "b.xml").write_text("<x/>", encoding="utf-8")
        (case_dir / "c.txt").write_text("not xml", encoding="utf-8")

        files = _find_case_xml_files(str(tmp_path))
        assert len(files) == 2
        assert os.path.basename(files[0]) == "a.xml"
        assert os.path.basename(files[1]) == "b.xml"


# ============================================================
# Backup tests
# ============================================================


class TestBackup:
    """文件备份测试。"""

    def test_backup_created(self, tmp_path):
        """Backup is created."""
        f = tmp_path / "test.xml"
        f.write_text("<root/>", encoding="utf-8")
        _backup_file(str(f))
        assert (tmp_path / "test.xml.bak").exists()

    def test_backup_not_overwritten(self, tmp_path):
        """Existing backup is not overwritten."""
        f = tmp_path / "test.xml"
        f.write_text("<root/>", encoding="utf-8")
        bak = tmp_path / "test.xml.bak"
        bak.write_text("original backup", encoding="utf-8")

        _backup_file(str(f))
        assert bak.read_text() == "original backup"

    def test_backup_nonexistent_file(self, tmp_path):
        """Backup of non-existent file → no crash."""
        _backup_file(str(tmp_path / "missing.xml"))
        assert not (tmp_path / "missing.xml.bak").exists()


# ============================================================
# End-to-end fix + retry integration
# ============================================================


class TestFixRetryIntegration:
    """修复 + 重试集成测试。"""

    def test_timeout_fix_then_retry_passes(self, tmp_path):
        """Timeout → wait fix → retry → pass."""
        from rodski_agent.execution.graph import build_execution_graph

        project_dir = _create_project(tmp_path, case_xml=SAMPLE_CASE_XML)
        execute_count = [0]

        def mock_pre_check(s):
            return {"status": "running"}

        def mock_execute(s):
            execute_count[0] += 1
            if execute_count[0] == 1:
                return {"execution_result": {"exit_code": 1}}
            return {"execution_result": {"exit_code": 0}}

        def mock_parse_result(s):
            ec = s.get("execution_result", {}).get("exit_code", -1)
            if ec == 0:
                return {"case_results": [{"id": "c001", "status": "PASS", "time": 1.0}]}
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "timeout", "time": 1.0}]}

        def mock_diagnose(s):
            return {
                "diagnosis": {
                    "category": "CASE_DEFECT",
                    "confidence": 0.9,
                    "root_cause": "Timeout waiting for element",
                    "suggestion": "add wait step",
                    "cases": [{"case_id": "c001"}],
                    "skipped": False,
                },
            }

        def mock_report(s):
            cases = s.get("case_results", [])
            passed = sum(1 for c in cases if c.get("status") == "PASS")
            status = "pass" if passed == len(cases) else "fail"
            return {"report": {"total": len(cases), "passed": passed, "failed": len(cases) - passed}, "status": status}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
        )
        result = g.invoke({
            "case_path": project_dir,
            "headless": True,
            "max_retry": 3,
        })

        assert execute_count[0] == 2
        assert result["status"] == "pass"
        assert len(result.get("fixes_applied", [])) >= 1
        assert any("wait" in f.lower() for f in result["fixes_applied"])

    def test_locator_fix_then_retry(self, tmp_path):
        """Element error → locator fix suggested → retry → pass."""
        from rodski_agent.execution.graph import build_execution_graph

        project_dir = _create_project(
            tmp_path,
            case_xml=SAMPLE_CASE_XML,
            model_xml=SAMPLE_MODEL_XML,
        )
        execute_count = [0]

        def mock_pre_check(s):
            return {"status": "running"}

        def mock_execute(s):
            execute_count[0] += 1
            if execute_count[0] == 1:
                return {"execution_result": {"exit_code": 1}}
            return {"execution_result": {"exit_code": 0}}

        def mock_parse_result(s):
            ec = s.get("execution_result", {}).get("exit_code", -1)
            if ec == 0:
                return {"case_results": [{"id": "c001", "status": "PASS", "time": 1.0}]}
            return {"case_results": [{"id": "c001", "status": "FAIL", "error": "element not found", "time": 1.0}]}

        def mock_diagnose(s):
            return {
                "diagnosis": {
                    "category": "CASE_DEFECT",
                    "confidence": 0.85,
                    "root_cause": "Element not found: login_btn",
                    "suggestion": "update locator",
                    "cases": [{"case_id": "c001"}],
                    "skipped": False,
                },
            }

        def mock_report(s):
            cases = s.get("case_results", [])
            passed = sum(1 for c in cases if c.get("status") == "PASS")
            status = "pass" if passed == len(cases) else "fail"
            return {"report": {"total": len(cases), "passed": passed, "failed": len(cases) - passed}, "status": status}

        g = build_execution_graph(
            mock_pre_check, mock_execute, mock_parse_result,
            mock_diagnose, mock_report,
        )
        result = g.invoke({
            "case_path": project_dir,
            "headless": True,
            "max_retry": 3,
        })

        assert execute_count[0] == 2
        assert result["status"] == "pass"
        assert len(result.get("fixes_applied", [])) >= 1
