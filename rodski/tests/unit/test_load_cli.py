"""test_load_cli — 压测 CLI 接入层单元测试。

覆盖：
  - _get_plan_kind() 从 XML 读取 kind 属性
  - _print_load_summary() 正常打印不报错（mock LoadStats）
  - _handle_load_run() locust 未安装时返回 1
"""
from __future__ import annotations

import sys
import textwrap
import types
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 导入被测函数（兼容包模式和直接运行模式）
# ---------------------------------------------------------------------------
try:
    from rodski.rodski_cli.run import (
        _get_plan_kind,
        _handle_load_run,
        _print_load_summary,
    )
except ImportError:
    from rodski_cli.run import (  # type: ignore[no-redef]
        _get_plan_kind,
        _handle_load_run,
        _print_load_summary,
    )


# ===========================================================================
# _get_plan_kind
# ===========================================================================

class TestGetPlanKind:

    def test_reads_kind_attribute(self, tmp_path):
        """正常 XML：kind 属性应被正确读取。"""
        plan_xml = tmp_path / "my_plan.xml"
        plan_xml.write_text(
            textwrap.dedent("""\
                <?xml version="1.0" encoding="utf-8"?>
                <test_plan id="my_plan" kind="load" default_execute="是">
                </test_plan>
            """),
            encoding="utf-8",
        )
        assert _get_plan_kind(plan_xml) == "load"

    def test_returns_suite_when_kind_missing(self, tmp_path):
        """XML 中没有 kind 属性时，应返回默认值 'suite'。"""
        plan_xml = tmp_path / "suite_plan.xml"
        plan_xml.write_text(
            '<test_plan id="suite_plan" default_execute="是"></test_plan>',
            encoding="utf-8",
        )
        assert _get_plan_kind(plan_xml) == "suite"

    def test_returns_suite_on_parse_error(self, tmp_path):
        """XML 解析失败时不应抛异常，应返回 'suite'。"""
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("<<not valid xml>>", encoding="utf-8")
        result = _get_plan_kind(bad_xml)
        assert result == "suite"

    def test_returns_suite_on_missing_file(self, tmp_path):
        """文件不存在时不应抛异常，应返回 'suite'。"""
        missing = tmp_path / "nonexistent.xml"
        result = _get_plan_kind(missing)
        assert result == "suite"

    def test_reads_suite_kind(self, tmp_path):
        """kind=suite 时正确返回 'suite'（非 'load'）。"""
        plan_xml = tmp_path / "full.xml"
        plan_xml.write_text(
            '<test_plan id="full" kind="suite" default_execute="是"></test_plan>',
            encoding="utf-8",
        )
        assert _get_plan_kind(plan_xml) == "suite"


# ===========================================================================
# _print_load_summary
# ===========================================================================

class TestPrintLoadSummary:

    def _make_stats(self, **overrides):
        """构造 mock LoadStats，summary() 返回合理数据。"""
        defaults = {
            "total_requests": 1000,
            "total_failures": 20,
            "error_rate_pct": 2.0,
            "rps_avg": 50.5,
            "p50_ms": 120,
            "p95_ms": 480,
            "p99_ms": 900,
            "avg_ms": 150.3,
            "max_ms": 1200,
        }
        defaults.update(overrides)
        stats = MagicMock()
        stats.summary.return_value = defaults
        return stats

    def test_prints_without_error(self, capsys):
        """默认调用不应抛任何异常。"""
        stats = self._make_stats()
        _print_load_summary(stats)
        captured = capsys.readouterr()
        assert "压测结果摘要" in captured.out

    def test_prints_all_key_metrics(self, capsys):
        """输出中应包含各关键指标。"""
        stats = self._make_stats(
            total_requests=500,
            error_rate_pct=1.5,
            rps_avg=25.0,
            p50_ms=100,
            p95_ms=300,
            p99_ms=700,
        )
        _print_load_summary(stats)
        out = capsys.readouterr().out
        assert "500" in out
        assert "1.50%" in out
        assert "25.00" in out
        assert "100 ms" in out
        assert "300 ms" in out
        assert "700 ms" in out

    def test_prints_elapsed_when_provided(self, capsys):
        """传入 elapsed 时应打印总耗时。"""
        stats = self._make_stats()
        _print_load_summary(stats, elapsed=42.7)
        out = capsys.readouterr().out
        assert "42.7" in out

    def test_no_elapsed_section_when_zero(self, capsys):
        """elapsed=0 时不打印总耗时行。"""
        stats = self._make_stats()
        _print_load_summary(stats, elapsed=0)
        out = capsys.readouterr().out
        assert "总耗时" not in out

    def test_zero_requests_does_not_raise(self, capsys):
        """空数据不应崩溃。"""
        stats = self._make_stats(
            total_requests=0,
            total_failures=0,
            error_rate_pct=0.0,
            rps_avg=0.0,
            p50_ms=0,
            p95_ms=0,
            p99_ms=0,
        )
        _print_load_summary(stats)  # 不应抛异常
        out = capsys.readouterr().out
        assert "压测结果摘要" in out


# ===========================================================================
# _handle_load_run — locust 未安装
# ===========================================================================

class TestHandleLoadRunNoLocust:

    def test_returns_1_when_locust_missing(self, tmp_path, capsys):
        """locust 未安装时 _handle_load_run 应返回 1 并打印安装指引。"""
        plan_xml = tmp_path / "load_plan.xml"
        plan_xml.write_text(
            '<test_plan id="load_plan" kind="load" default_execute="是"></test_plan>',
            encoding="utf-8",
        )
        args = MagicMock()
        args.no_compile = False

        # 通过将 'locust' 注册为 None 模拟未安装状态
        with patch.dict(sys.modules, {"locust": None}):
            result = _handle_load_run(plan_xml, tmp_path, args)

        assert result == 1
        err = capsys.readouterr().err
        assert "pip install locust" in err

    def test_stderr_contains_install_hint(self, tmp_path, capsys):
        """错误信息中应包含安装提示。"""
        plan_xml = tmp_path / "p.xml"
        plan_xml.write_text(
            '<test_plan id="p" kind="load" default_execute="是"></test_plan>',
            encoding="utf-8",
        )
        args = MagicMock()
        args.no_compile = False

        with patch.dict(sys.modules, {"locust": None}):
            _handle_load_run(plan_xml, tmp_path, args)

        err = capsys.readouterr().err
        assert "locust" in err.lower()
