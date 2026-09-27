"""ResultWriter 单元测试 - XML 版本"""
import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from core.result_writer import ResultWriter


@pytest.fixture
def result_dir(tmp_path):
    d = tmp_path / "result"
    d.mkdir()
    return str(d)


class TestResultWriterInit:
    def test_creates_dir_if_missing(self, tmp_path):
        d = tmp_path / "new_result"
        assert not d.exists()
        ResultWriter(str(d))
        assert d.exists()

    def test_init_ok(self, result_dir):
        rw = ResultWriter(result_dir)
        assert rw.result_dir == Path(result_dir)


class TestWriteResult:
    def test_single_pass_result(self, result_dir):
        rw = ResultWriter(result_dir)
        rw.write_result({"case_id": "TC001", "title": "登录测试", "status": "PASS", "execution_time": 1.23})

        result_files = list(Path(result_dir).glob("rodski_*/result.xml"))
        assert len(result_files) == 1

        tree = ET.parse(result_files[0])
        root = tree.getroot()
        assert root.tag == "testresult"

        summary = root.find("summary")
        assert summary.get("total") == "1"
        assert summary.get("passed") == "1"
        assert summary.get("failed") == "0"

        results = root.find("results")
        result_elem = results.find("result")
        assert result_elem.get("case_id") == "TC001"
        assert result_elem.get("status") == "PASS"

    def test_recording_metadata_written(self, result_dir):
        rw = ResultWriter(result_dir)
        rw.write_result({
            "case_id": "TC010",
            "title": "录制测试",
            "status": "PASS",
            "execution_time": 1.23,
            "recording_path": "recordings/TC010_01.webm",
            "recordings": [
                {"index": 1, "path": "recordings/TC010_01.webm", "backend": "playwright"},
                {"index": 2, "path": "recordings/TC010_02.webm", "backend": "playwright"},
            ],
        })

        result_files = list(Path(result_dir).glob("rodski_*/result.xml"))
        tree = ET.parse(result_files[0])
        root = tree.getroot()
        result_elem = root.find("results/result")
        assert result_elem.get("recording_path") == "recordings/TC010_01.webm"
        recording_elems = result_elem.findall("recordings/recording")
        assert len(recording_elems) == 2
        assert recording_elems[0].get("path") == "recordings/TC010_01.webm"
        assert recording_elems[1].get("path") == "recordings/TC010_02.webm"

    def test_fail_result_with_error(self, result_dir):
        rw = ResultWriter(result_dir)
        rw.write_result({
            "case_id": "TC002",
            "title": "搜索测试",
            "status": "FAIL",
            "execution_time": 0.5,
            "error": "Element not found",
        })

        result_files = list(Path(result_dir).glob("rodski_*/result.xml"))
        tree = ET.parse(result_files[0])
        root = tree.getroot()

        result_elem = root.find("results/result")
        assert result_elem.get("status") == "FAIL"
        assert result_elem.get("error_message") == "Element not found"


    def test_business_result_written_and_schema_valid(self, result_dir):
        """business_call step 的完整结果应落盘，并由 result.xsd 校验。"""
        rw = ResultWriter(result_dir)
        rw.write_result({
            "case_id": "TC-BM-LOGIN-OK",
            "status": "PASS",
            "steps": [{
                "index": 1,
                "phase": "test_case",
                "action": "business_call",
                "model": "login_flow",
                "status": "ok",
                "business_result": {
                    "id": "login_success",
                    "ref": "login_flow",
                    "flow": "F_LOGIN_SUCCESS",
                    "input": "LOGIN_OK_01",
                    "expect": "LOGIN_SUCCESS_01",
                    "passed": True,
                    "actual_path": ["open_login", "submit_login", "validate_login", "home"],
                    "expected_path": ["open_login", "submit_login", "validate_login", "home"],
                    "actual": {"login_status": "success", "message": "登录成功"},
                    "expected": {"login_status": "success", "message": "登录成功"},
                    "nodes": [{
                        "node_id": "validate_login",
                        "steps": [{"login_status": "success"}],
                    }],
                    "assertion_errors": [],
                },
            }],
        })

        result_file = next(Path(result_dir).glob("rodski_*/result.xml"))
        business = ET.parse(result_file).find("results/result/steps/step/business_result")
        assert business is not None
        assert business.attrib["flow"] == "F_LOGIN_SUCCESS"
        assert business.attrib["input"] == "LOGIN_OK_01"
        assert business.attrib["expect"] == "LOGIN_SUCCESS_01"
        assert business.attrib["passed"] == "true"
        assert [node.get("id") for node in business.findall("actual_path/node")] == [
            "open_login", "submit_login", "validate_login", "home"
        ]
        assert [node.get("id") for node in business.findall("expected_path/node")] == [
            "open_login", "submit_login", "validate_login", "home"
        ]
        assert {
            field.get("name"): field.get("value")
            for field in business.findall("actual/field")
        } == {"login_status": "success", "message": "登录成功"}
        assert {
            field.get("name"): field.get("value")
            for field in business.findall("expected/field")
        } == {"login_status": "success", "message": "登录成功"}
        assert business.find("nodes/node[@id='validate_login']") is not None
        assert business.find("assertion_errors") is not None
        assert business.find("assertion_errors").findall("error") == []

    def test_business_result_failure_keeps_assertion_errors(self, result_dir):
        """路径/字段断言失败也必须保留可追溯的结构化结果。"""
        rw = ResultWriter(result_dir)
        rw.write_result({
            "case_id": "TC-BM-LOGIN-MISMATCH",
            "status": "FAIL",
            "steps": [{
                "index": 1,
                "action": "business_call",
                "status": "fail",
                "business_result": {
                    "flow": "F_LOGIN_SUCCESS",
                    "input": "LOGIN_BAD_01",
                    "expect": "LOGIN_SUCCESS_01",
                    "actual_path": ["open_login", "submit_login", "validate_login", "error"],
                    "expected_path": ["open_login", "submit_login", "validate_login", "home"],
                    "actual": {"login_status": "invalid_credentials"},
                    "expected": {"login_status": "success"},
                    "nodes": [{"node_id": "error", "steps": []}],
                    "assertion_errors": [
                        "Path mismatch: expected home, got error",
                        "Field 'login_status': expected 'success', got 'invalid_credentials'",
                    ],
                },
            }],
        })

        business = ET.parse(next(Path(result_dir).glob("rodski_*/result.xml"))).find(
            "results/result/steps/step/business_result"
        )
        assert [error.text for error in business.findall("assertion_errors/error")] == [
            "Path mismatch: expected home, got error",
            "Field 'login_status': expected 'success', got 'invalid_credentials'",
        ]
        assert business.find("actual_path/node[@id='error']") is not None

    def test_legacy_step_result_remains_schema_compatible(self, result_dir):
        """没有 business_result 的旧步骤结果仍按原结构写入。"""
        rw = ResultWriter(result_dir)
        rw.write_result({
            "case_id": "TC-LEGACY",
            "status": "PASS",
            "steps": [{
                "index": 1,
                "action": "navigate",
                "model": "",
                "data": "https://example.com",
                "status": "OK",
            }],
        })

        step = ET.parse(next(Path(result_dir).glob("rodski_*/result.xml"))).find(
            "results/result/steps/step"
        )
        assert step.get("action") == "navigate"
        assert step.find("business_result") is None


class TestBatchWrite:
    def test_batch_write(self, result_dir):
        rw = ResultWriter(result_dir)
        results = [
            {"case_id": "TC001", "title": "登录测试", "status": "PASS", "execution_time": 1.0},
            {"case_id": "TC002", "title": "搜索测试", "status": "FAIL", "execution_time": 0.8, "error": "Timeout"},
        ]
        rw.write_results(results)

        result_files = list(Path(result_dir).glob("rodski_*/result.xml"))
        tree = ET.parse(result_files[0])
        root = tree.getroot()

        summary = root.find("summary")
        assert summary.get("total") == "2"
        assert summary.get("passed") == "1"
        assert summary.get("failed") == "1"
        assert summary.get("pass_rate") == "50.0%"

        result_elems = root.findall("results/result")
        assert len(result_elems) == 2

    def test_empty_list_no_file(self, result_dir):
        rw = ResultWriter(result_dir)
        rw.write_results([])
        result_files = list(Path(result_dir).glob("rodski_*/result.xml"))
        assert len(result_files) == 0


class TestSummary:
    def test_summary_stats(self, result_dir):
        rw = ResultWriter(result_dir)
        results = [
            {"case_id": "TC001", "status": "PASS", "execution_time": 1.0},
            {"case_id": "TC002", "status": "PASS", "execution_time": 2.0},
            {"case_id": "TC003", "status": "FAIL", "execution_time": 0.5, "error": "err"},
        ]
        rw.write_results(results)

        summary = rw.get_summary()
        assert summary.total == 3
        assert summary.passed == 2
        assert summary.failed == 1
        assert summary.pass_rate == pytest.approx(66.7, abs=0.1)


class TestXMLValidity:
    def test_xml_is_well_formed(self, result_dir):
        rw = ResultWriter(result_dir)
        rw.write_result({"case_id": "TC001", "status": "PASS"})

        result_files = list(Path(result_dir).glob("rodski_*/result.xml"))
        content = result_files[0].read_text(encoding="utf-8")
        assert '<?xml version="1.0" ?>' in content

        root = ET.fromstring(content)
        assert root.tag == "testresult"
