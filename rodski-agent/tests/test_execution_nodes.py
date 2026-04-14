"""Execution nodes unit tests."""
from __future__ import annotations

import json
import os
import pytest
from rodski_agent.execution.nodes import pre_check, parse_result, report


class TestPreCheck:
    def test_missing_path_returns_error(self, tmp_path):
        """Non-existent path -> error."""
        result = pre_check({"case_path": str(tmp_path / "nonexistent")})
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_valid_module_dir(self, sample_project_dir):
        """Valid module dir (with case/model/data) -> running."""
        result = pre_check({"case_path": str(sample_project_dir)})
        assert result["status"] == "running"

    def test_case_file_in_module(self, sample_project_dir):
        """case/xxx.xml file within valid module -> running."""
        case_file = sample_project_dir / "case" / "test.xml"
        case_file.write_text("<cases/>")
        result = pre_check({"case_path": str(case_file)})
        assert result["status"] == "running"

    def test_missing_required_dirs(self, tmp_path):
        """Directory without case/model/data -> error."""
        result = pre_check({"case_path": str(tmp_path)})
        assert result["status"] == "error"
        assert "Missing" in result["error"]

    def test_case_dir_path(self, sample_project_dir):
        """Passing the case/ subdir itself (parent has model/data) -> running."""
        result = pre_check({"case_path": str(sample_project_dir / "case")})
        assert result["status"] == "running"


class TestParseResult:
    def test_no_result_dir_fallback_to_exit_code(self):
        """Without result_dir, infer from exit_code."""
        state = {
            "execution_result": {"exit_code": 0, "result_dir": None, "result_files": []},
        }
        result = parse_result(state)
        assert len(result["case_results"]) == 1
        assert result["case_results"][0]["status"] == "PASS"

    def test_exit_code_failure(self):
        """exit_code=1 -> FAIL."""
        state = {
            "execution_result": {"exit_code": 1, "result_dir": None, "result_files": [], "stderr": "timeout"},
        }
        result = parse_result(state)
        assert result["case_results"][0]["status"] == "FAIL"

    def test_summary_json_parsing(self, tmp_path):
        """Parse execution_summary.json correctly."""
        summary = {"cases": [
            {"case_id": "c001", "title": "Login", "status": "PASS", "execution_time": 2.5},
            {"case_id": "c002", "title": "Logout", "status": "FAIL", "error": "timeout"},
        ]}
        (tmp_path / "execution_summary.json").write_text(json.dumps(summary))
        state = {
            "execution_result": {"exit_code": 1, "result_dir": str(tmp_path), "result_files": []},
        }
        result = parse_result(state)
        assert len(result["case_results"]) == 2
        assert result["case_results"][0]["id"] == "c001"
        assert result["case_results"][1]["status"] == "FAIL"

    def test_error_state_short_circuits(self):
        """If status is error, returns empty."""
        result = parse_result({"status": "error"})
        assert result == {}

    def test_screenshots_collected(self, tmp_path):
        """Screenshots from result_dir/screenshots/ are collected."""
        ss_dir = tmp_path / "screenshots"
        ss_dir.mkdir()
        (ss_dir / "step1.png").write_text("fake")
        (ss_dir / "step2.jpg").write_text("fake")
        (ss_dir / "log.txt").write_text("not a screenshot")
        state = {
            "execution_result": {"exit_code": 0, "result_dir": str(tmp_path), "result_files": []},
        }
        result = parse_result(state)
        assert len(result["screenshots"]) == 2


class TestReport:
    def test_all_pass(self):
        result = report({"case_results": [
            {"status": "PASS"}, {"status": "PASS"}
        ]})
        assert result["status"] == "pass"
        assert result["report"]["total"] == 2
        assert result["report"]["passed"] == 2
        assert result["report"]["failed"] == 0

    def test_all_fail(self):
        result = report({"case_results": [
            {"status": "FAIL"}, {"status": "FAIL"}
        ]})
        assert result["status"] == "fail"

    def test_partial(self):
        result = report({"case_results": [
            {"status": "PASS"}, {"status": "FAIL"}
        ]})
        assert result["status"] == "partial"

    def test_error_status_preserved(self):
        result = report({"status": "error", "case_results": []})
        assert result["status"] == "error"

    def test_empty_results(self):
        result = report({"case_results": []})
        assert result["report"]["total"] == 0
        assert result["status"] == "pass"  # 0 failed = pass
