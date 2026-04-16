"""TrendCalculator 单元测试

覆盖趋势计算、不稳定用例检测、缺陷聚合、新增失败/修复、诊断统计等。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from report.trend import TrendCalculator, _error_fingerprint


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _run(
    run_id="run_001",
    timestamp="2026-04-16T10:00:00",
    pass_rate=100.0,
    duration=10.0,
    cases=None,
):
    """辅助：构造单次运行摘要（同 history.json 中的格式）"""
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "total": len(cases) if cases else 0,
        "passed": sum(1 for c in (cases or {}).values() if c.get("status") == "PASS"),
        "failed": sum(1 for c in (cases or {}).values() if c.get("status") == "FAIL"),
        "skipped": 0,
        "pass_rate": pass_rate,
        "duration": duration,
        "cases": cases or {},
    }


# ------------------------------------------------------------------
# 通过率 / 耗时趋势
# ------------------------------------------------------------------


class TestPassRateTrend:
    """测试通过率趋势计算"""

    def test_empty_history(self):
        """空历史应返回空列表"""
        tc = TrendCalculator([])
        assert tc.pass_rate_trend() == []

    def test_basic_trend(self):
        """应返回每次运行的 run_id、timestamp、pass_rate"""
        history = [
            _run(run_id="r1", timestamp="2026-04-10", pass_rate=80.0),
            _run(run_id="r2", timestamp="2026-04-11", pass_rate=90.0),
        ]
        trend = TrendCalculator(history).pass_rate_trend()
        assert len(trend) == 2
        assert trend[0] == {"run_id": "r1", "timestamp": "2026-04-10", "pass_rate": 80.0}
        assert trend[1]["pass_rate"] == 90.0


class TestDurationTrend:
    """测试耗时趋势计算"""

    def test_duration_values(self):
        """应返回每次运行的耗时"""
        history = [
            _run(run_id="r1", duration=10.5),
            _run(run_id="r2", duration=8.3),
        ]
        trend = TrendCalculator(history).duration_trend()
        assert trend[0]["duration"] == 10.5
        assert trend[1]["duration"] == 8.3


# ------------------------------------------------------------------
# 不稳定用例
# ------------------------------------------------------------------


class TestFlakyCases:
    """测试不稳定用例检测"""

    def test_no_flaky_when_consistent(self):
        """所有运行都通过时不应有不稳定用例"""
        history = [
            _run(cases={"TC001": {"status": "PASS"}}),
            _run(cases={"TC001": {"status": "PASS"}}),
            _run(cases={"TC001": {"status": "PASS"}}),
        ]
        assert TrendCalculator(history).flaky_cases() == []

    def test_detects_flaky_case(self):
        """状态交替变化的用例应被检测为不稳定"""
        history = [
            _run(cases={"TC001": {"status": "PASS"}}),
            _run(cases={"TC001": {"status": "FAIL"}}),
            _run(cases={"TC001": {"status": "PASS"}}),
            _run(cases={"TC001": {"status": "FAIL"}}),
        ]
        result = TrendCalculator(history).flaky_cases()
        assert len(result) == 1
        assert result[0]["case_id"] == "TC001"
        # 3 次翻转 / 3 个间隔 = 1.0
        assert result[0]["flaky_rate"] == 1.0
        assert result[0]["runs_checked"] == 4

    def test_skip_status_ignored(self):
        """SKIP 状态不参与不稳定计算"""
        history = [
            _run(cases={"TC001": {"status": "PASS"}}),
            _run(cases={"TC001": {"status": "SKIP"}}),
            _run(cases={"TC001": {"status": "PASS"}}),
        ]
        # 只有两次 PASS，无翻转
        assert TrendCalculator(history).flaky_cases() == []

    def test_single_run_not_flaky(self):
        """只有一次运行时不应有不稳定用例"""
        history = [_run(cases={"TC001": {"status": "FAIL"}})]
        assert TrendCalculator(history).flaky_cases() == []

    def test_multiple_flaky_sorted(self):
        """多个不稳定用例应按 flaky_rate 降序排列"""
        history = [
            _run(cases={
                "TC001": {"status": "PASS"},
                "TC002": {"status": "PASS"},
            }),
            _run(cases={
                "TC001": {"status": "FAIL"},
                "TC002": {"status": "PASS"},
            }),
            _run(cases={
                "TC001": {"status": "PASS"},
                "TC002": {"status": "FAIL"},
            }),
        ]
        result = TrendCalculator(history).flaky_cases()
        # TC001: PASS->FAIL->PASS (2 flips / 2 = 1.0)
        # TC002: PASS->PASS->FAIL (1 flip / 2 = 0.5)
        assert result[0]["case_id"] == "TC001"
        assert result[0]["flaky_rate"] == 1.0
        assert result[1]["case_id"] == "TC002"
        assert result[1]["flaky_rate"] == 0.5


# ------------------------------------------------------------------
# 缺陷聚合
# ------------------------------------------------------------------


class TestDefectClusters:
    """测试缺陷聚合功能"""

    def test_no_errors_no_clusters(self):
        """无错误时应返回空列表"""
        history = [_run(cases={"TC001": {"status": "PASS"}})]
        assert TrendCalculator(history).defect_clusters() == []

    def test_same_error_grouped(self):
        """相同错误消息应聚合为一个 cluster"""
        history = [
            _run(run_id="r1", timestamp="2026-04-10", cases={
                "TC001": {"status": "FAIL", "error": "Element not found: #submit"},
            }),
            _run(run_id="r2", timestamp="2026-04-11", cases={
                "TC002": {"status": "FAIL", "error": "Element not found: #submit"},
            }),
        ]
        clusters = TrendCalculator(history).defect_clusters()
        assert len(clusters) == 1
        assert clusters[0]["count"] == 2
        assert set(clusters[0]["case_ids"]) == {"TC001", "TC002"}
        assert clusters[0]["first_seen"] == "2026-04-10"
        assert clusters[0]["last_seen"] == "2026-04-11"

    def test_different_errors_separate_clusters(self):
        """不同错误应产生不同 cluster"""
        history = [
            _run(cases={
                "TC001": {"status": "FAIL", "error": "Element not found"},
                "TC002": {"status": "FAIL", "error": "Timeout after waiting"},
            }),
        ]
        clusters = TrendCalculator(history).defect_clusters()
        assert len(clusters) == 2

    def test_dynamic_parts_normalized(self):
        """含动态部分的相似错误应聚合在一起"""
        history = [
            _run(cases={
                "TC001": {"status": "FAIL",
                           "error": "Timeout at 2026-04-10T12:00:00 for session abc12345"},
            }),
            _run(cases={
                "TC002": {"status": "FAIL",
                           "error": "Timeout at 2026-04-11T09:30:00 for session def67890"},
            }),
        ]
        clusters = TrendCalculator(history).defect_clusters()
        # 去除时间戳和十六进制ID后应聚合
        assert len(clusters) == 1
        assert clusters[0]["count"] == 2

    def test_sorted_by_count(self):
        """cluster 应按 count 降序排列"""
        history = [
            _run(cases={
                "TC001": {"status": "FAIL", "error": "Error A"},
                "TC002": {"status": "FAIL", "error": "Error B"},
                "TC003": {"status": "FAIL", "error": "Error B"},
            }),
        ]
        clusters = TrendCalculator(history).defect_clusters()
        assert clusters[0]["count"] >= clusters[-1]["count"]


# ------------------------------------------------------------------
# 新增失败 / 修复成功
# ------------------------------------------------------------------


class TestNewFailures:
    """测试新增失败检测"""

    def test_empty_history(self):
        """空历史应返回空列表"""
        assert TrendCalculator([]).new_failures() == []

    def test_single_run(self):
        """单次运行无法比较，应返回空列表"""
        history = [_run(cases={"TC001": {"status": "FAIL"}})]
        assert TrendCalculator(history).new_failures() == []

    def test_detects_new_failure(self):
        """上次通过本次失败的用例应被检测为新增失败"""
        history = [
            _run(cases={"TC001": {"status": "PASS"}, "TC002": {"status": "PASS"}}),
            _run(cases={"TC001": {"status": "FAIL"}, "TC002": {"status": "PASS"}}),
        ]
        assert TrendCalculator(history).new_failures() == ["TC001"]

    def test_persistent_failure_not_new(self):
        """连续失败的用例不是新增失败"""
        history = [
            _run(cases={"TC001": {"status": "FAIL"}}),
            _run(cases={"TC001": {"status": "FAIL"}}),
        ]
        assert TrendCalculator(history).new_failures() == []


class TestFixedCases:
    """测试修复成功检测"""

    def test_detects_fixed_case(self):
        """上次失败本次通过的用例应被检测为修复成功"""
        history = [
            _run(cases={"TC001": {"status": "FAIL"}, "TC002": {"status": "FAIL"}}),
            _run(cases={"TC001": {"status": "PASS"}, "TC002": {"status": "FAIL"}}),
        ]
        assert TrendCalculator(history).fixed_cases() == ["TC001"]

    def test_persistent_pass_not_fixed(self):
        """连续通过的用例不是修复成功"""
        history = [
            _run(cases={"TC001": {"status": "PASS"}}),
            _run(cases={"TC001": {"status": "PASS"}}),
        ]
        assert TrendCalculator(history).fixed_cases() == []


# ------------------------------------------------------------------
# WI-44: Agent 诊断统计
# ------------------------------------------------------------------


class TestDiagnosisSummary:
    """测试 Agent 诊断类别统计"""

    def test_empty_history(self):
        """空历史应返回空字典"""
        assert TrendCalculator([]).diagnosis_summary() == {}

    def test_counts_categories(self):
        """应正确统计各诊断类别出现次数"""
        history = [
            _run(cases={
                "TC001": {
                    "status": "FAIL",
                    "diagnosis": [
                        {"category": "ElementNotFound", "strategy": "wait"},
                        {"category": "ElementNotFound", "strategy": "wait"},
                    ],
                },
                "TC002": {
                    "status": "FAIL",
                    "diagnosis": [{"category": "Timeout", "strategy": "refresh"}],
                },
            }),
        ]
        summary = TrendCalculator(history).diagnosis_summary()
        assert summary == {"ElementNotFound": 2, "Timeout": 1}

    def test_across_multiple_runs(self):
        """应跨多次运行累加统计"""
        history = [
            _run(cases={"TC001": {
                "status": "FAIL",
                "diagnosis": [{"category": "Timeout"}],
            }}),
            _run(cases={"TC001": {
                "status": "FAIL",
                "diagnosis": [{"category": "Timeout"}],
            }}),
        ]
        assert TrendCalculator(history).diagnosis_summary() == {"Timeout": 2}


class TestFixSuccessRate:
    """测试修复成功率统计"""

    def test_empty_history(self):
        """空历史应返回空字典"""
        assert TrendCalculator([]).fix_success_rate() == {}

    def test_calculates_rate(self):
        """应正确计算各策略的成功率"""
        history = [
            _run(cases={
                "TC001": {
                    "status": "PASS",
                    "diagnosis": [
                        {"strategy": "wait", "fixed": True},
                        {"strategy": "wait", "fixed": True},
                        {"strategy": "wait", "fixed": False},
                    ],
                },
                "TC002": {
                    "status": "FAIL",
                    "diagnosis": [
                        {"strategy": "refresh", "fixed": False},
                    ],
                },
            }),
        ]
        rates = TrendCalculator(history).fix_success_rate()
        assert rates["wait"]["total"] == 3
        assert rates["wait"]["success"] == 2
        assert rates["wait"]["rate"] == pytest.approx(0.667, abs=0.001)
        assert rates["refresh"]["total"] == 1
        assert rates["refresh"]["success"] == 0
        assert rates["refresh"]["rate"] == 0

    def test_no_strategy_skipped(self):
        """没有 strategy 字段的诊断条目应被跳过"""
        history = [
            _run(cases={
                "TC001": {
                    "status": "FAIL",
                    "diagnosis": [{"category": "SomeError"}],
                },
            }),
        ]
        assert TrendCalculator(history).fix_success_rate() == {}


# ------------------------------------------------------------------
# 错误 fingerprint 工具函数
# ------------------------------------------------------------------


class TestErrorFingerprint:
    """测试错误消息指纹化"""

    def test_identical_messages_same_fp(self):
        """完全相同的错误消息应生成相同 fingerprint"""
        fp1 = _error_fingerprint("Element not found: #submit")
        fp2 = _error_fingerprint("Element not found: #submit")
        assert fp1 == fp2

    def test_different_messages_different_fp(self):
        """不同错误消息应生成不同 fingerprint"""
        fp1 = _error_fingerprint("Element not found")
        fp2 = _error_fingerprint("Timeout exceeded")
        assert fp1 != fp2

    def test_timestamp_normalized(self):
        """时间戳应被标准化，含不同时间戳的同类错误应有相同 fingerprint"""
        fp1 = _error_fingerprint("Error at 2026-04-10T12:00:00")
        fp2 = _error_fingerprint("Error at 2026-04-11T09:30:00")
        assert fp1 == fp2

    def test_uuid_normalized(self):
        """UUID 应被标准化"""
        fp1 = _error_fingerprint("Session 550e8400-e29b-41d4-a716-446655440000 failed")
        fp2 = _error_fingerprint("Session a1b2c3d4-e5f6-7890-abcd-ef1234567890 failed")
        assert fp1 == fp2

    def test_long_numbers_normalized(self):
        """长数字序列（>= 4 位）应被标准化"""
        fp1 = _error_fingerprint("Port 8080 connection refused")
        fp2 = _error_fingerprint("Port 9090 connection refused")
        assert fp1 == fp2

    def test_short_numbers_preserved(self):
        """短数字（< 4 位）应保留，不进行标准化"""
        fp1 = _error_fingerprint("Step 3 failed")
        fp2 = _error_fingerprint("Step 5 failed")
        assert fp1 != fp2

    def test_fingerprint_length(self):
        """fingerprint 应为 12 个十六进制字符"""
        fp = _error_fingerprint("any error message")
        assert len(fp) == 12
        assert all(c in "0123456789abcdef" for c in fp)
