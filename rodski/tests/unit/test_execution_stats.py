"""ExecutionStats 单元测试

测试 core/execution_stats.py 中的执行统计分析模块。
覆盖：calculate_case_success_rate（正常/无记录/部分失败）、
      get_all_case_stats（多用例/多运行目录）、_get_case_results（内部方法）。
"""
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path
from core.execution_stats import ExecutionStats


@pytest.fixture
def result_dir(tmp_path):
    """创建包含多次运行结果的临时 result 目录"""
    # 第一次运行：c001 PASS, c002 FAIL
    run1 = tmp_path / "20260401_100000"
    run1.mkdir()
    _write_result(run1, [("c001", "PASS"), ("c002", "FAIL")])

    # 第二次运行：c001 PASS, c002 PASS
    run2 = tmp_path / "20260402_100000"
    run2.mkdir()
    _write_result(run2, [("c001", "PASS"), ("c002", "PASS")])

    # 第三次运行：c001 FAIL, c002 PASS
    run3 = tmp_path / "20260403_100000"
    run3.mkdir()
    _write_result(run3, [("c001", "FAIL"), ("c002", "PASS")])

    return tmp_path


def _write_result(run_dir: Path, cases: list):
    """辅助函数：写入一个 result.xml 文件"""
    root = ET.Element("testresult")
    results = ET.SubElement(root, "results")
    for case_id, status in cases:
        ET.SubElement(results, "result", case_id=case_id, status=status)
    tree = ET.ElementTree(root)
    tree.write(str(run_dir / "result.xml"), encoding="unicode")


class TestCalculateCaseSuccessRate:
    """calculate_case_success_rate —— 单个用例成功率计算"""

    def test_success_rate_two_of_three(self, result_dir):
        """c001 有 2 次 PASS / 1 次 FAIL，成功率应为 66.67%"""
        rate = ExecutionStats.calculate_case_success_rate(result_dir, "c001")
        assert rate is not None
        assert abs(rate - 66.67) < 1  # 约 66.67%

    def test_success_rate_nonexistent_case(self, result_dir):
        """不存在的 case_id 应返回 None"""
        rate = ExecutionStats.calculate_case_success_rate(result_dir, "c999")
        assert rate is None

    def test_success_rate_empty_dir(self, tmp_path):
        """空目录应返回 None"""
        rate = ExecutionStats.calculate_case_success_rate(tmp_path, "c001")
        assert rate is None

    def test_success_rate_last_n(self, result_dir):
        """last_n=2 时只统计最近两次"""
        # 最近两次：20260403(FAIL), 20260402(PASS) → 50%
        rate = ExecutionStats.calculate_case_success_rate(result_dir, "c001", last_n=2)
        assert rate is not None
        assert abs(rate - 50.0) < 0.1

    def test_success_rate_all_pass(self, result_dir):
        """c002 有 2 次 PASS / 1 次 FAIL，但 last_n=2 时最近两次全 PASS"""
        rate = ExecutionStats.calculate_case_success_rate(result_dir, "c002", last_n=2)
        assert rate is not None
        assert abs(rate - 100.0) < 0.1


class TestGetAllCaseStats:
    """get_all_case_stats —— 所有用例统计信息"""

    def test_returns_all_cases(self, result_dir):
        """应返回所有用例的统计信息"""
        stats = ExecutionStats.get_all_case_stats(result_dir)
        assert "c001" in stats
        assert "c002" in stats

    def test_stats_structure(self, result_dir):
        """每个用例的统计应包含 success_rate、total_runs、last_status"""
        stats = ExecutionStats.get_all_case_stats(result_dir)
        c001 = stats["c001"]
        assert "success_rate" in c001
        assert "total_runs" in c001
        assert "last_status" in c001

    def test_total_runs_count(self, result_dir):
        """total_runs 应等于实际运行次数"""
        stats = ExecutionStats.get_all_case_stats(result_dir)
        assert stats["c001"]["total_runs"] == 3
        assert stats["c002"]["total_runs"] == 3

    def test_last_status_is_latest_run(self, result_dir):
        """last_status 应为最近一次运行的状态"""
        stats = ExecutionStats.get_all_case_stats(result_dir)
        # 最近运行 20260403：c001=FAIL, c002=PASS
        assert stats["c001"]["last_status"] == "FAIL"
        assert stats["c002"]["last_status"] == "PASS"

    def test_empty_dir(self, tmp_path):
        """空目录应返回空字典"""
        stats = ExecutionStats.get_all_case_stats(tmp_path)
        assert stats == {}
