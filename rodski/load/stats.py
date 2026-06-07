"""LoadStats — 压测指标聚合（api/browser 模式共用）。
接口压测（Locust）由 LocustLoadEngine 从 env.stats 转换填充；
浏览器压测（后续）由 PlaywrightLoadEngine 直接写入。
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RequestRecord:
    """单次请求记录。"""
    name: str           # 接口名/用例名，用于按接口分组统计
    elapsed_ms: int     # 响应耗时（毫秒）
    success: bool       # 是否成功
    failure_reason: Optional[str] = None


class LoadStats:
    """压测指标聚合容器。线程/协程安全（append-only）。"""

    def __init__(self):
        self._records: list[RequestRecord] = []

    def record(self, r: RequestRecord) -> None:
        self._records.append(r)

    @property
    def total_requests(self) -> int:
        return len(self._records)

    @property
    def total_failures(self) -> int:
        return sum(1 for r in self._records if not r.success)

    def summary(self) -> dict:
        """返回全局汇总指标。"""
        if hasattr(self, "_locust_summary"):
            return self._locust_summary
        if not self._records:
            return {
                "total_requests": 0, "total_failures": 0,
                "error_rate_pct": 0.0,
                "p50_ms": 0, "p75_ms": 0, "p95_ms": 0, "p99_ms": 0,
                "avg_ms": 0.0, "max_ms": 0,
            }
        times = sorted(r.elapsed_ms for r in self._records)
        n = len(times)
        failures = self.total_failures
        return {
            "total_requests": n,
            "total_failures": failures,
            "error_rate_pct": round(failures / n * 100, 3),
            "p50_ms":  self._percentile(times, 0.50),
            "p75_ms":  self._percentile(times, 0.75),
            "p95_ms":  self._percentile(times, 0.95),
            "p99_ms":  self._percentile(times, 0.99),
            "avg_ms":  round(sum(times) / n, 1),
            "max_ms":  max(times),
        }

    def per_endpoint(self) -> list[dict]:
        """按接口名分组统计。"""
        if hasattr(self, "_locust_endpoints"):
            return self._locust_endpoints
        groups: dict[str, list[RequestRecord]] = {}
        for r in self._records:
            groups.setdefault(r.name, []).append(r)

        result = []
        for name, records in groups.items():
            times = sorted(r.elapsed_ms for r in records)
            n = len(times)
            failures = sum(1 for r in records if not r.success)
            result.append({
                "name": name,
                "requests": n,
                "failures": failures,
                "error_rate_pct": round(failures / n * 100, 3),
                "p95_ms": self._percentile(times, 0.95),
                "avg_ms": round(sum(times) / n, 1),
            })
        return sorted(result, key=lambda x: x["name"])

    @staticmethod
    def _percentile(sorted_times: list[int], p: float) -> int:
        """计算百分位数（nearest rank 方法）。"""
        if not sorted_times:
            return 0
        n = len(sorted_times)
        idx = max(0, math.ceil(n * p) - 1)
        return sorted_times[idx]
