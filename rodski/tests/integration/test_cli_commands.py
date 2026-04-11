"""CLI 命令集成测试"""
import json
import subprocess
import sys
import pytest
from pathlib import Path
from unittest.mock import patch
from io import StringIO


PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_cli(*args):
    """运行 CLI 命令并返回结果"""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "cli_main.py")] + list(args),
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    return result


class TestCLIHelp:
    def test_help(self):
        r = run_cli("--help")
        assert r.returncode == 0
        assert "RodSki" in r.stdout

    def test_version(self):
        from cli_main import VERSION
        r = run_cli("--version")
        assert r.returncode == 0
        assert VERSION in r.stdout

    def test_no_args(self):
        r = run_cli()
        assert r.returncode == 0


class TestCLIConfig:
    def test_config_set_get(self, tmp_path, monkeypatch):
        monkeypatch.chdir(PROJECT_ROOT)
        r = run_cli("config", "list")
        assert r.returncode == 0

    def test_config_list(self):
        r = run_cli("config", "list")
        assert r.returncode == 0
        assert "driver" in r.stdout


class TestCLILog:
    def test_log_clear(self):
        r = run_cli("log", "clear")
        assert r.returncode == 0

    def test_log_view_empty(self):
        run_cli("log", "clear")
        r = run_cli("log", "view")
        # either shows logs or says no logs
        assert r.returncode == 0


class TestCLIRun:
    def test_run_nonexistent_file(self):
        r = run_cli("run", "/nonexistent/file.xlsx")
        assert r.returncode == 1
        assert "不存在" in r.stderr


class TestCLIReport:
    def test_report_no_results(self):
        r = run_cli("report", "--input", "/nonexistent/results.json")
        assert r.returncode == 1

    def test_report_json(self, tmp_path):
        results = {
            "summary": {"total": 2, "passed": 1, "failed": 1, "duration": 1.0, "pass_rate": 50.0},
            "results": [
                {"step": "S1", "keyword": "click", "success": True},
                {"step": "S2", "keyword": "type", "success": False},
            ],
            "timestamp": "2024-01-01T00:00:00",
        }
        results_file = tmp_path / "results.json"
        results_file.write_text(json.dumps(results))
        output_file = tmp_path / "report.json"
        r = run_cli("report", "--format", "json",
                     "--input", str(results_file),
                     "--output", str(output_file))
        assert r.returncode == 0
        assert output_file.exists()

    def test_report_html(self, tmp_path):
        results = {
            "summary": {"total": 1, "passed": 1, "failed": 0, "duration": 0.5, "pass_rate": 100.0},
            "results": [{"step": "S1", "keyword": "click", "success": True}],
            "timestamp": "2024-01-01T00:00:00",
        }
        results_file = tmp_path / "results.json"
        results_file.write_text(json.dumps(results))
        output_file = tmp_path / "report.html"
        r = run_cli("report", "--format", "html",
                     "--input", str(results_file),
                     "--output", str(output_file))
        assert r.returncode == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "SKI" in content
        assert "PASS" in content
