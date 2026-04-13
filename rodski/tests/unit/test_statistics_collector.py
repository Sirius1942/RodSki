"""StatisticsCollector 单元测试

测试 core/statistics_collector.py 中的统计收集和聚合模块。
覆盖：StepStatistics 百分位计算、CaseStatistics 通过率、RunStatistics、
      StatisticsCollector 的 add_result / aggregate / get_flaky_cases / export_json / daily_trend。
"""
import json
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path
from core.statistics_collector import (
    StepStatistics, CaseStatistics, RunStatistics,
    AggregatedStatistics, StatisticsCollector,
)


# =====================================================================
# StepStatistics 数据类
# =====================================================================
class TestStepStatistics:
    """StepStatistics 百分位和均值计算"""

    def test_avg_with_data(self):
        """有数据时 avg 应为均值"""
        stats = StepStatistics(keyword="type", durations_ms=[100, 200, 300])
        assert stats.avg == 200.0

    def test_avg_empty(self):
        """无数据时 avg 应为 0"""
        stats = StepStatistics(keyword="type")
        assert stats.avg == 0.0

    def test_p50_median(self):
        """p50 应为中位数"""
        stats = StepStatistics(keyword="type", durations_ms=[10, 20, 30, 40, 50])
        assert stats.p50 == 30  # 中间值

    def test_p95(self):
        """p95 应为第 95 百分位
        实现使用 int(len*0.95) 作为索引，100 个元素时 idx=95，
        0-indexed 对应第 96 个值"""
        stats = StepStatistics(keyword="type", durations_ms=list(range(1, 101)))
        assert stats.p95 == 96  # sorted[95] = 96（0-indexed）

    def test_p99(self):
        """p99 应为第 99 百分位
        实现使用 int(len*0.99) 作为索引，100 个元素时 idx=99，
        0-indexed 对应第 100 个值"""
        stats = StepStatistics(keyword="type", durations_ms=list(range(1, 101)))
        assert stats.p99 == 100  # sorted[99] = 100（0-indexed）

    def test_percentiles_empty(self):
        """无数据时所有百分位应为 0"""
        stats = StepStatistics(keyword="type")
        assert stats.p50 == 0.0
        assert stats.p95 == 0.0
        assert stats.p99 == 0.0

    def test_count_tracking(self):
        """count / passed / failed / skipped 应可独立累加"""
        stats = StepStatistics(keyword="verify", count=10, passed=7, failed=2, skipped=1)
        assert stats.count == 10
        assert stats.passed == 7


# =====================================================================
# CaseStatistics 数据类
# =====================================================================
class TestCaseStatistics:
    """CaseStatistics 通过率和均值计算"""

    def test_pass_rate(self):
        """通过率 = passed / (passed + failed) * 100"""
        stats = CaseStatistics(case_id="c001", passed=8, failed=2)
        assert stats.pass_rate == 80.0

    def test_pass_rate_all_passed(self):
        """全部通过时通过率 100%"""
        stats = CaseStatistics(case_id="c001", passed=10, failed=0)
        assert stats.pass_rate == 100.0

    def test_pass_rate_no_runs(self):
        """无运行时通过率 0%"""
        stats = CaseStatistics(case_id="c001", passed=0, failed=0)
        assert stats.pass_rate == 0.0

    def test_avg_duration(self):
        """avg_duration 应为所有步骤耗时的均值"""
        stats = CaseStatistics(case_id="c001")
        stats.step_stats["type"] = StepStatistics(keyword="type", durations_ms=[100, 200])
        stats.step_stats["verify"] = StepStatistics(keyword="verify", durations_ms=[300])
        # (100+200+300)/3 = 200
        assert stats.avg_duration == 200.0

    def test_avg_duration_empty(self):
        """无步骤统计时 avg_duration 为 0"""
        stats = CaseStatistics(case_id="c001")
        assert stats.avg_duration == 0.0


# =====================================================================
# RunStatistics 数据类
# =====================================================================
class TestRunStatistics:
    """RunStatistics 通过率"""

    def test_pass_rate(self):
        """运行通过率"""
        rs = RunStatistics(run_id="r1", run_time="2026-04-01T10:00:00",
                          passed=9, failed=1)
        assert rs.pass_rate == 90.0


# =====================================================================
# StatisticsCollector 完整流程
# =====================================================================
@pytest.fixture
def result_xml(tmp_path):
    """创建一个完整的 result XML 文件"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testresult>
  <summary total="2" passed="1" failed="1" skipped="0" start_time="2026-04-01T10:00:00" total_time="5.0"/>
  <results>
    <result case_id="c001" status="PASS">
      <step action="type" duration_ms="150" status="PASS"/>
      <step action="verify" duration_ms="80" status="PASS"/>
    </result>
    <result case_id="c002" status="FAIL">
      <step action="navigate" duration_ms="200" status="PASS"/>
      <step action="type" duration_ms="100" status="FAIL"/>
    </result>
  </results>
</testresult>"""
    f = tmp_path / "result_20260401_100000.xml"
    f.write_text(xml_content, encoding="utf-8")
    return str(f)


class TestStatisticsCollectorAddResult:
    """add_result —— 解析 result XML 并累积统计"""

    def test_run_stats_populated(self, result_xml):
        """添加结果后 run_stats 应包含运行统计"""
        collector = StatisticsCollector()
        collector.add_result(result_xml)
        assert len(collector.run_stats) == 1
        assert collector.run_stats[0].total == 2
        assert collector.run_stats[0].passed == 1
        assert collector.run_stats[0].failed == 1

    def test_case_stats_populated(self, result_xml):
        """添加结果后 case_stats 应包含用例统计"""
        collector = StatisticsCollector()
        collector.add_result(result_xml)
        assert "c001" in collector.case_stats
        assert "c002" in collector.case_stats
        assert collector.case_stats["c001"].passed == 1
        assert collector.case_stats["c002"].failed == 1

    def test_global_step_stats(self, result_xml):
        """全局步骤统计应聚合所有用例的步骤"""
        collector = StatisticsCollector()
        collector.add_result(result_xml)
        # type 在两个用例中都出现
        assert "type" in collector.global_step_stats
        assert collector.global_step_stats["type"].count == 2


class TestStatisticsCollectorAggregate:
    """aggregate —— 聚合所有统计数据"""

    def test_aggregate_returns_correct_type(self, result_xml):
        """aggregate 应返回 AggregatedStatistics"""
        collector = StatisticsCollector()
        collector.add_result(result_xml)
        agg = collector.aggregate()
        assert isinstance(agg, AggregatedStatistics)
        assert agg.total_runs == 1


class TestGetFlakyCases:
    """get_flaky_cases —— 识别不稳定用例"""

    def test_flaky_case_detected(self, result_xml, tmp_path):
        """通过率低于阈值且 >0% 的用例应被标记为 flaky
        注意：get_flaky_cases 要求 0 < pass_rate < threshold*100，
        即 pass_rate=0 的用例不算 flaky（而是"稳定失败"），
        只有间歇性失败（通过率 >0 但低于阈值）才是 flaky"""
        # 创建第二个 result XML，让 c002 在此次通过
        xml_pass = """<?xml version="1.0" encoding="UTF-8"?>
<testresult>
  <summary total="2" passed="2" failed="0" skipped="0" start_time="2026-04-02T10:00:00" total_time="4.0"/>
  <results>
    <result case_id="c001" status="PASS">
      <step action="type" duration_ms="120" status="PASS"/>
    </result>
    <result case_id="c002" status="PASS">
      <step action="navigate" duration_ms="180" status="PASS"/>
    </result>
  </results>
</testresult>"""
        f2 = tmp_path / "result_20260402_100000.xml"
        f2.write_text(xml_pass, encoding="utf-8")

        collector = StatisticsCollector()
        collector.add_result(result_xml)   # c002 FAIL
        collector.add_result(result_xml)   # c002 FAIL
        collector.add_result(str(f2))      # c002 PASS
        # c002: passed=1, failed=2 → pass_rate=33.3%
        # 但阈值 0.5 意味着 <50% 都算 flaky
        flaky = collector.get_flaky_cases(threshold=0.5)
        assert "c002" in flaky

    def test_stable_case_not_flaky(self, result_xml):
        """通过率高于阈值的用例不应被标记"""
        collector = StatisticsCollector()
        collector.add_result(result_xml)
        collector.add_result(result_xml)
        # c001: passed=2, failed=0 → pass_rate=100% → 不 flaky
        flaky = collector.get_flaky_cases(threshold=0.3)
        assert "c001" not in flaky


class TestExportJson:
    """export_json —— 导出 JSON 统计文件"""

    def test_export_creates_file(self, result_xml, tmp_path):
        """应生成有效的 JSON 文件"""
        collector = StatisticsCollector()
        collector.add_result(result_xml)
        output = tmp_path / "stats.json"
        collector.export_json(str(output))

        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert "total_runs" in data
        assert "cases" in data
        assert "runs" in data


class TestDailyTrend:
    """daily_trend —— 每日趋势统计"""

    def test_daily_trend(self, result_xml):
        """每日趋势应按日期聚合"""
        collector = StatisticsCollector()
        collector.add_result(result_xml)
        trend = collector.daily_trend()
        # start_time 为 "2026-04-01T10:00:00"，日期为 "2026-04-01"
        assert "2026-04-01" in trend
        assert trend["2026-04-01"]["total"] == 2
