"""单元测试：LoadStats 指标聚合模块。"""
import sys
import os

# 确保 rodski 包可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest
from rodski.load.stats import LoadStats, RequestRecord


class TestEmptyStats:
    """空 stats 返回零值摘要。"""

    def test_empty_summary_returns_zeros(self):
        stats = LoadStats()
        s = stats.summary()
        assert s["total_requests"] == 0
        assert s["total_failures"] == 0
        assert s["error_rate_pct"] == 0.0
        assert s["p50_ms"] == 0
        assert s["p75_ms"] == 0
        assert s["p95_ms"] == 0
        assert s["p99_ms"] == 0
        assert s["avg_ms"] == 0.0
        assert s["max_ms"] == 0

    def test_empty_per_endpoint_returns_empty_list(self):
        stats = LoadStats()
        assert stats.per_endpoint() == []

    def test_empty_total_requests(self):
        stats = LoadStats()
        assert stats.total_requests == 0

    def test_empty_total_failures(self):
        stats = LoadStats()
        assert stats.total_failures == 0


class TestPercentileCalculation:
    """5 条记录的 p50/p95/p99 计算正确性。"""

    def setup_method(self):
        self.stats = LoadStats()
        # 5 条记录，elapsed_ms: 100, 200, 300, 400, 500
        for ms in [100, 200, 300, 400, 500]:
            self.stats.record(RequestRecord(name="api_a", elapsed_ms=ms, success=True))

    def test_p50(self):
        # n=5, ceil(5*0.50)-1 = ceil(2.5)-1 = 3-1 = 2 → sorted[2] = 300
        s = self.stats.summary()
        assert s["p50_ms"] == 300

    def test_p75(self):
        # n=5, ceil(5*0.75)-1 = ceil(3.75)-1 = 4-1 = 3 → sorted[3] = 400
        s = self.stats.summary()
        assert s["p75_ms"] == 400

    def test_p95(self):
        # n=5, ceil(5*0.95)-1 = ceil(4.75)-1 = 5-1 = 4 → sorted[4] = 500
        s = self.stats.summary()
        assert s["p95_ms"] == 500

    def test_p99(self):
        # n=5, ceil(5*0.99)-1 = ceil(4.95)-1 = 5-1 = 4 → sorted[4] = 500
        s = self.stats.summary()
        assert s["p99_ms"] == 500

    def test_avg_ms(self):
        # (100+200+300+400+500)/5 = 300.0
        s = self.stats.summary()
        assert s["avg_ms"] == 300.0

    def test_max_ms(self):
        s = self.stats.summary()
        assert s["max_ms"] == 500

    def test_total_requests(self):
        s = self.stats.summary()
        assert s["total_requests"] == 5


class TestErrorRate:
    """error_rate_pct 计算：3/10 次失败 = 30.000%。"""

    def setup_method(self):
        self.stats = LoadStats()
        for i in range(10):
            success = i >= 3  # 前 3 条失败
            self.stats.record(RequestRecord(
                name="api_b",
                elapsed_ms=100 + i * 10,
                success=success,
                failure_reason="timeout" if not success else None,
            ))

    def test_error_rate_pct(self):
        s = self.stats.summary()
        assert s["error_rate_pct"] == 30.0

    def test_total_failures(self):
        s = self.stats.summary()
        assert s["total_failures"] == 3

    def test_total_requests(self):
        s = self.stats.summary()
        assert s["total_requests"] == 10

    def test_total_failures_property(self):
        assert self.stats.total_failures == 3


class TestPerEndpoint:
    """per_endpoint 按名称分组正确。"""

    def setup_method(self):
        self.stats = LoadStats()
        # api_login: 3 条，全成功
        for ms in [50, 80, 120]:
            self.stats.record(RequestRecord(name="api_login", elapsed_ms=ms, success=True))
        # api_order: 2 条，1 条失败
        self.stats.record(RequestRecord(name="api_order", elapsed_ms=200, success=True))
        self.stats.record(RequestRecord(name="api_order", elapsed_ms=300, success=False, failure_reason="500"))

    def test_per_endpoint_count(self):
        result = self.stats.per_endpoint()
        assert len(result) == 2

    def test_per_endpoint_sorted_by_name(self):
        result = self.stats.per_endpoint()
        names = [r["name"] for r in result]
        assert names == sorted(names)

    def test_api_login_stats(self):
        result = {r["name"]: r for r in self.stats.per_endpoint()}
        login = result["api_login"]
        assert login["requests"] == 3
        assert login["failures"] == 0
        assert login["error_rate_pct"] == 0.0
        # avg = (50+80+120)/3 = 83.3
        assert login["avg_ms"] == pytest.approx(83.3, abs=0.1)

    def test_api_order_stats(self):
        result = {r["name"]: r for r in self.stats.per_endpoint()}
        order = result["api_order"]
        assert order["requests"] == 2
        assert order["failures"] == 1
        assert order["error_rate_pct"] == 50.0

    def test_per_endpoint_p95(self):
        result = {r["name"]: r for r in self.stats.per_endpoint()}
        login = result["api_login"]
        # n=3, ceil(3*0.95)-1 = ceil(2.85)-1 = 3-1 = 2 → sorted[2] = 120
        assert login["p95_ms"] == 120


class TestMixedRecords:
    """混合成功/失败记录。"""

    def test_mixed_summary(self):
        stats = LoadStats()
        records = [
            RequestRecord("ep1", 100, True),
            RequestRecord("ep1", 200, False, "conn_error"),
            RequestRecord("ep2", 150, True),
            RequestRecord("ep2", 250, False, "timeout"),
            RequestRecord("ep1", 300, True),
        ]
        for r in records:
            stats.record(r)

        s = stats.summary()
        assert s["total_requests"] == 5
        assert s["total_failures"] == 2
        assert s["error_rate_pct"] == 40.0
        assert s["max_ms"] == 300

    def test_record_with_failure_reason(self):
        stats = LoadStats()
        r = RequestRecord("ep1", 500, False, "HTTP 503")
        stats.record(r)
        assert stats.total_failures == 1
        assert stats.total_requests == 1

    def test_all_failures(self):
        stats = LoadStats()
        for ms in [100, 200, 300]:
            stats.record(RequestRecord("ep1", ms, False, "error"))
        s = stats.summary()
        assert s["error_rate_pct"] == 100.0
        assert s["total_failures"] == 3

    def test_all_success(self):
        stats = LoadStats()
        for ms in [100, 200, 300]:
            stats.record(RequestRecord("ep1", ms, True))
        s = stats.summary()
        assert s["error_rate_pct"] == 0.0
        assert s["total_failures"] == 0
