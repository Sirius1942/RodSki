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

        result_files = list(Path(result_dir).glob("result_*.xml"))
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

    def test_fail_result_with_error(self, result_dir):
        rw = ResultWriter(result_dir)
        rw.write_result({
            "case_id": "TC002",
            "title": "搜索测试",
            "status": "FAIL",
            "execution_time": 0.5,
            "error": "Element not found",
        })

        result_files = list(Path(result_dir).glob("result_*.xml"))
        tree = ET.parse(result_files[0])
        root = tree.getroot()

        result_elem = root.find("results/result")
        assert result_elem.get("status") == "FAIL"
        assert result_elem.get("error_message") == "Element not found"


class TestBatchWrite:
    def test_batch_write(self, result_dir):
        rw = ResultWriter(result_dir)
        results = [
            {"case_id": "TC001", "title": "登录测试", "status": "PASS", "execution_time": 1.0},
            {"case_id": "TC002", "title": "搜索测试", "status": "FAIL", "execution_time": 0.8, "error": "Timeout"},
        ]
        rw.write_results(results)

        result_files = list(Path(result_dir).glob("result_*.xml"))
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
        result_files = list(Path(result_dir).glob("result_*.xml"))
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

        result_files = list(Path(result_dir).glob("result_*.xml"))
        content = result_files[0].read_text(encoding="utf-8")
        assert '<?xml version="1.0" ?>' in content

        root = ET.fromstring(content)
        assert root.tag == "testresult"
