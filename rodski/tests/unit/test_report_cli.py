"""report 子命令与 run --report 集成的单元测试"""
import json
import sys
import types
import argparse
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def result_dir(tmp_path):
    """创建一个包含 results.json 的临时结果目录"""
    data = {
        "summary": {
            "total": 3,
            "passed": 2,
            "failed": 1,
            "pass_rate": 66.7,
            "duration": 5.2,
        },
        "results": [
            {"step": "TC-001", "keyword": "login", "success": True, "message": "", "duration": 1.0},
            {"step": "TC-002", "keyword": "search", "success": True, "message": "", "duration": 2.0},
            {"step": "TC-003", "keyword": "checkout", "success": False, "message": "timeout", "duration": 2.2},
        ],
        "timestamp": "2026-04-16T10:00:00",
    }
    (tmp_path / "results.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return tmp_path


@pytest.fixture
def history_dir(tmp_path):
    """创建一个包含多次运行历史的目录"""
    hist = tmp_path / "history"
    hist.mkdir()
    for i in range(5):
        entry = {
            "summary": {"total": 10, "passed": 10 - i, "failed": i, "pass_rate": (10 - i) * 10.0, "duration": 3.0 + i},
            "timestamp": f"2026-04-{10 + i:02d}T12:00:00",
        }
        (hist / f"result_2026041{i}_120000.json").write_text(
            json.dumps(entry, ensure_ascii=False), encoding="utf-8",
        )
    return hist


# ---------------------------------------------------------------------------
# report generate 测试
# ---------------------------------------------------------------------------

class TestReportGenerate:
    """测试 report generate 子命令"""

    def test_generate_html_from_result_dir(self, result_dir):
        """从结果目录生成 HTML 报告"""
        from rodski_cli.report import _handle_generate

        output_path = str(result_dir / "output.html")
        args = argparse.Namespace(
            result_dir=str(result_dir),
            single_file=False,
            output=output_path,
        )
        rc = _handle_generate(args)
        assert rc == 0
        assert Path(output_path).exists()
        content = Path(output_path).read_text(encoding="utf-8")
        assert "<html" in content
        assert "TC-001" in content

    def test_generate_nonexistent_dir(self):
        """目标目录不存在时返回错误"""
        from rodski_cli.report import _handle_generate

        args = argparse.Namespace(
            result_dir="/nonexistent/path",
            single_file=False,
            output=None,
        )
        rc = _handle_generate(args)
        assert rc == 1

    def test_generate_empty_dir(self, tmp_path):
        """空目录中无结果文件时返回错误"""
        from rodski_cli.report import _handle_generate

        args = argparse.Namespace(
            result_dir=str(tmp_path),
            single_file=False,
            output=None,
        )
        rc = _handle_generate(args)
        assert rc == 1

    def test_generate_single_file(self, result_dir):
        """--single-file 模式生成报告"""
        from rodski_cli.report import _handle_generate

        output_path = str(result_dir / "single.html")
        args = argparse.Namespace(
            result_dir=str(result_dir),
            single_file=True,
            output=output_path,
        )
        rc = _handle_generate(args)
        assert rc == 0
        assert Path(output_path).exists()

    def test_generate_default_output_path(self, result_dir):
        """不指定 --output 时默认输出到 result_dir/report.html"""
        from rodski_cli.report import _handle_generate

        args = argparse.Namespace(
            result_dir=str(result_dir),
            single_file=False,
            output=None,
        )
        rc = _handle_generate(args)
        assert rc == 0
        assert (result_dir / "report.html").exists()


# ---------------------------------------------------------------------------
# report trend 测试
# ---------------------------------------------------------------------------

class TestReportTrend:
    """测试 report trend 子命令"""

    def test_trend_with_history(self, history_dir, capsys):
        """有历史数据时输出趋势表格"""
        from rodski_cli.report import _handle_trend

        args = argparse.Namespace(
            result_dir=str(history_dir),
            last=3,
        )
        rc = _handle_trend(args)
        assert rc == 0
        captured = capsys.readouterr()
        assert "3" in captured.out  # 最近 3 次

    def test_trend_no_history(self, tmp_path):
        """无历史数据时返回错误"""
        from rodski_cli.report import _handle_trend

        args = argparse.Namespace(
            result_dir=str(tmp_path),
            last=10,
        )
        rc = _handle_trend(args)
        assert rc == 1


# ---------------------------------------------------------------------------
# generate_html_from_run_results (run --report html 集成)
# ---------------------------------------------------------------------------

class TestRunReportIntegration:
    """测试 run --report html 集成入口"""

    def test_generate_html_from_run_results(self, tmp_path, monkeypatch):
        """从 run 结果列表生成 HTML 文件"""
        monkeypatch.chdir(tmp_path)
        from rodski_cli.report import generate_html_from_run_results

        results = [
            {"case_id": "TC-001", "title": "Login", "status": "PASS", "execution_time": 1.5},
            {"case_id": "TC-002", "title": "Search", "status": "FAIL", "error": "element not found", "execution_time": 2.0},
        ]
        report_path = generate_html_from_run_results(
            results=results, total=2, passed=1, failed=1, duration=3.5,
        )
        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding="utf-8")
        assert "TC-001" in content
        assert "TC-002" in content
        assert "50.0%" in content  # pass rate

    def test_generate_report_empty_results(self, tmp_path, monkeypatch):
        """空结果列表也能生成报告（不崩溃）"""
        monkeypatch.chdir(tmp_path)
        from rodski_cli.report import generate_html_from_run_results

        report_path = generate_html_from_run_results(
            results=[], total=0, passed=0, failed=0, duration=0.0,
        )
        assert Path(report_path).exists()


# ---------------------------------------------------------------------------
# handle 分发测试
# ---------------------------------------------------------------------------

class TestReportHandle:
    """测试 report handle 分发逻辑"""

    def test_handle_no_action(self, capsys):
        """未指定 report_action 时打印用法提示"""
        from rodski_cli.report import handle

        args = argparse.Namespace(report_action=None)
        rc = handle(args)
        assert rc == 1

    def test_handle_dispatches_generate(self, result_dir):
        """handle 正确分发到 generate"""
        from rodski_cli.report import handle

        output_path = str(result_dir / "dispatched.html")
        args = argparse.Namespace(
            report_action="generate",
            result_dir=str(result_dir),
            single_file=False,
            output=output_path,
        )
        rc = handle(args)
        assert rc == 0


# ---------------------------------------------------------------------------
# _parse_result_xml 测试
# ---------------------------------------------------------------------------

class TestParseResultXml:
    """测试从 result.xml 解析结果"""

    def test_parse_valid_xml(self, tmp_path):
        """解析合法的 result.xml"""
        from rodski_cli.report import _parse_result_xml

        xml_content = '''<?xml version="1.0" ?>
<testresult>
  <summary total="2" passed="1" failed="1" pass_rate="50.0%" total_time="3.5s"/>
  <results>
    <result case_id="TC-001" title="Login" status="PASS" execution_time="1.5" error_message=""/>
    <result case_id="TC-002" title="Search" status="FAIL" execution_time="2.0" error_message="timeout"/>
  </results>
</testresult>'''
        xml_path = tmp_path / "result.xml"
        xml_path.write_text(xml_content, encoding="utf-8")

        data = _parse_result_xml(xml_path)
        assert data is not None
        assert data["summary"]["total"] == 2
        assert data["summary"]["passed"] == 1
        assert len(data["results"]) == 2
        assert data["results"][0]["success"] is True
        assert data["results"][1]["success"] is False

    def test_parse_invalid_xml(self, tmp_path):
        """无效 XML 返回 None"""
        from rodski_cli.report import _parse_result_xml

        xml_path = tmp_path / "result.xml"
        xml_path.write_text("not xml at all", encoding="utf-8")
        assert _parse_result_xml(xml_path) is None


# ---------------------------------------------------------------------------
# _normalize_run_results 测试
# ---------------------------------------------------------------------------

class TestNormalizeRunResults:
    """测试 SKIExecutor 结果归一化"""

    def test_normalize(self):
        """将 SKIExecutor 格式转为报告格式"""
        from rodski_cli.report import _normalize_run_results

        results = [
            {"case_id": "TC-001", "title": "Login", "status": "PASS", "execution_time": 1.5},
            {"case_id": "TC-002", "title": "Search", "status": "FAIL", "error": "timeout"},
        ]
        normalized = _normalize_run_results(results)
        assert len(normalized) == 2
        assert normalized[0]["step"] == "TC-001"
        assert normalized[0]["success"] is True
        assert normalized[1]["success"] is False
        assert normalized[1]["message"] == "timeout"
