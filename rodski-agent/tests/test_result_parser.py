"""result_parser 模块测试 — 覆盖各解析函数和边界情况。"""

from __future__ import annotations

import json
import os

import pytest

from rodski_agent.common.result_parser import (
    collect_screenshots,
    extract_cases_from_summary,
    find_latest_result,
    parse_execution_summary,
    parse_result_xml,
)


class TestParseExecutionSummary:
    def test_正常解析(self, tmp_path):
        summary_data = {"cases": [{"case_id": "c001", "status": "PASS"}]}
        path = tmp_path / "execution_summary.json"
        path.write_text(json.dumps(summary_data))
        result = parse_execution_summary(str(path))
        assert result["cases"][0]["case_id"] == "c001"

    def test_目录路径(self, tmp_path):
        """传入目录路径，自动拼接 execution_summary.json。"""
        summary_data = {"cases": [{"case_id": "c002", "status": "FAIL"}]}
        (tmp_path / "execution_summary.json").write_text(json.dumps(summary_data))
        result = parse_execution_summary(str(tmp_path))
        assert result["cases"][0]["case_id"] == "c002"

    def test_文件不存在返回空字典(self, tmp_path):
        result = parse_execution_summary(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_无效JSON返回空字典(self, tmp_path):
        bad_file = tmp_path / "execution_summary.json"
        bad_file.write_text("not json {{{")
        result = parse_execution_summary(str(tmp_path))
        assert result == {}

    def test_非字典JSON返回空字典(self, tmp_path):
        """JSON 内容为列表而非字典时返回空。"""
        (tmp_path / "execution_summary.json").write_text("[1, 2, 3]")
        result = parse_execution_summary(str(tmp_path))
        assert result == {}


class TestExtractCasesFromSummary:
    def test_cases字段(self):
        summary = {"cases": [
            {"case_id": "c001", "title": "Login", "status": "PASS", "execution_time": 2.5},
            {"case_id": "c002", "title": "Logout", "status": "FAIL", "error": "timeout"},
        ]}
        results = extract_cases_from_summary(summary)
        assert len(results) == 2
        assert results[0]["id"] == "c001"
        assert results[0]["time"] == 2.5
        assert results[1]["status"] == "FAIL"
        assert results[1]["error"] == "timeout"

    def test_results字段(self):
        """兼容 results 键名。"""
        summary = {"results": [
            {"id": "r001", "title": "Test", "status": "PASS", "time": 1.0},
        ]}
        results = extract_cases_from_summary(summary)
        assert len(results) == 1
        assert results[0]["id"] == "r001"

    def test_空summary(self):
        results = extract_cases_from_summary({})
        assert results == []

    def test_默认值填充(self):
        """缺失字段应有默认值。"""
        summary = {"cases": [{}]}
        results = extract_cases_from_summary(summary)
        assert results[0]["id"] == "unknown"
        assert results[0]["status"] == "UNKNOWN"
        assert results[0]["time"] == 0


class TestParseResultXml:
    def test_正常XML(self, tmp_path):
        xml_content = """\
<testresult>
  <summary total="2" passed="1" failed="1"/>
  <results>
    <result case_id="c001" title="Login" status="PASS" execution_time="2.3"/>
    <result case_id="c002" title="Search" status="FAIL" execution_time="5.0" error_message="element not found"/>
  </results>
</testresult>"""
        xml_file = tmp_path / "result_20240101.xml"
        xml_file.write_text(xml_content)
        results = parse_result_xml(str(xml_file))
        assert len(results) == 2
        assert results[0]["id"] == "c001"
        assert results[0]["time"] == 2.3
        assert results[1]["error"] == "element not found"

    def test_文件不存在返回空(self, tmp_path):
        results = parse_result_xml(str(tmp_path / "nonexistent.xml"))
        assert results == []

    def test_无效XML返回空(self, tmp_path):
        bad_file = tmp_path / "result_bad.xml"
        bad_file.write_text("<broken xml <<<")
        results = parse_result_xml(str(bad_file))
        assert results == []

    def test_空results节点(self, tmp_path):
        xml_content = """\
<testresult>
  <summary total="0"/>
  <results/>
</testresult>"""
        xml_file = tmp_path / "result_empty.xml"
        xml_file.write_text(xml_content)
        results = parse_result_xml(str(xml_file))
        assert results == []


class TestFindLatestResult:
    def test_找到最新文件(self, tmp_path):
        # 创建两个文件，让第二个更新
        f1 = tmp_path / "result_001.xml"
        f1.write_text("<testresult/>")
        import time
        time.sleep(0.05)  # 确保时间差
        f2 = tmp_path / "result_002.xml"
        f2.write_text("<testresult/>")

        latest = find_latest_result(str(tmp_path))
        assert latest is not None
        assert "result_002" in latest

    def test_无匹配文件(self, tmp_path):
        (tmp_path / "other.txt").write_text("nothing")
        assert find_latest_result(str(tmp_path)) is None

    def test_目录不存在(self, tmp_path):
        assert find_latest_result(str(tmp_path / "nonexistent")) is None

    def test_忽略非result前缀文件(self, tmp_path):
        (tmp_path / "summary.xml").write_text("<x/>")
        assert find_latest_result(str(tmp_path)) is None


class TestCollectScreenshots:
    def test_收集png和jpg(self, tmp_path):
        ss_dir = tmp_path / "screenshots"
        ss_dir.mkdir()
        (ss_dir / "step1.png").write_text("fake")
        (ss_dir / "step2.jpg").write_text("fake")
        (ss_dir / "log.txt").write_text("not screenshot")

        results = collect_screenshots(str(tmp_path))
        assert len(results) == 2
        filenames = [os.path.basename(p) for p in results]
        assert "step1.png" in filenames
        assert "step2.jpg" in filenames
        assert "log.txt" not in filenames

    def test_无screenshots目录(self, tmp_path):
        results = collect_screenshots(str(tmp_path))
        assert results == []

    def test_空screenshots目录(self, tmp_path):
        (tmp_path / "screenshots").mkdir()
        results = collect_screenshots(str(tmp_path))
        assert results == []

    def test_排序一致(self, tmp_path):
        ss_dir = tmp_path / "screenshots"
        ss_dir.mkdir()
        (ss_dir / "b.png").write_text("fake")
        (ss_dir / "a.png").write_text("fake")
        results = collect_screenshots(str(tmp_path))
        filenames = [os.path.basename(p) for p in results]
        assert filenames == ["a.png", "b.png"]
