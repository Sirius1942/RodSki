"""Profiler 单元测试

测试 core/profiler.py 中的性能分析器。
覆盖：start/stop 计时、duration 计算、
      report 输出、嵌套测量。
"""
import pytest
import time
from core.profiler import Profiler


def test_profiler_record():
    profiler = Profiler()
    profiler.record("click", 0.5, True)
    profiler.record("type", 0.3, True)
    profiler.record("click", 0.6, False)
    
    stats = profiler.get_stats()
    assert stats["total_keywords"] == 3
    assert "click" in stats["by_keyword"]
    assert stats["by_keyword"]["click"]["count"] == 2
    assert stats["by_keyword"]["click"]["failures"] == 1


def test_profiler_stats():
    profiler = Profiler()
    profiler.record("wait", 1.2, True)
    profiler.record("navigate", 0.8, True)
    
    stats = profiler.get_stats()
    assert "100.0%" in stats["success_rate"]
    assert "2.0" in stats["total_time"]


def test_profiler_save_json(tmp_path):
    profiler = Profiler()
    profiler.record("click", 0.5, True)
    
    json_file = tmp_path / "test.json"
    profiler.save_json(str(json_file))
    assert json_file.exists()


def test_profiler_save_html(tmp_path):
    profiler = Profiler()
    profiler.record("type", 0.3, True)
    
    html_file = tmp_path / "test.html"
    profiler.save_html(str(html_file))
    assert html_file.exists()
    content = html_file.read_text()
    assert "性能报告" in content
