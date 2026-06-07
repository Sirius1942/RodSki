"""LocustLoadEngine 单元测试。

所有 locust / gevent 依赖通过 mock 隔离，不发起真实网络请求。
覆盖：
- _validate_cases() 对非接口 case 抛 LoadModeUnsupportedCaseError
- _build_user_class() 返回类有正确 host / wait_time / task 方法
- _collect_stats() 从 mock env.stats 正确提取指标
- summary() / per_endpoint() 优先使用 _locust_summary / _locust_endpoints
"""
from __future__ import annotations
import sys
import types
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# 最小 stub：确保 locust / gevent 在无安装时也能 import
# ---------------------------------------------------------------------------

def _make_locust_stub():
    locust_mod = types.ModuleType("locust")

    class _FHU:
        abstract = True
        host = ""
        wait_time = None

    locust_mod.FastHttpUser = _FHU
    locust_mod.task = lambda w=1: (lambda f: f)
    locust_mod.between = lambda a, b: (lambda: None)
    locust_mod.constant = lambda t: (lambda: None)

    env_mod = types.ModuleType("locust.env")

    class _Env:
        def __init__(self, user_classes=None):
            self.user_classes = user_classes or []
            self.stats = MagicMock()
            self.runner = MagicMock()

        def create_local_runner(self):
            pass

    env_mod.Environment = _Env
    locust_mod.env = env_mod

    return locust_mod, env_mod


def _ensure_stubs():
    if "locust" not in sys.modules:
        locust_mod, env_mod = _make_locust_stub()
        sys.modules["locust"] = locust_mod
        sys.modules["locust.env"] = env_mod
    if "gevent" not in sys.modules:
        gevent_mod = types.ModuleType("gevent")
        gevent_mod.monkey = MagicMock()
        gevent_mod.spawn_later = MagicMock()
        sys.modules["gevent"] = gevent_mod
        sys.modules["gevent.monkey"] = gevent_mod.monkey


_ensure_stubs()


# ---------------------------------------------------------------------------
# 导入被测模块
# ---------------------------------------------------------------------------

from rodski.load.locust_engine import LocustLoadEngine  # noqa: E402
from rodski.load.stats import LoadStats  # noqa: E402


# ---------------------------------------------------------------------------
# 辅助工厂
# ---------------------------------------------------------------------------

def _make_shared_ctx(case_registry: dict | None = None, global_values: dict | None = None):
    ctx = MagicMock()
    ctx.case_registry = case_registry or {}
    ctx.global_values = global_values or {}
    return ctx


def _make_plan(cases=None, profile: dict | None = None):
    return {
        "load_profile": profile or {
            "concurrency": 2,
            "duration_seconds": 5,
            "ramp_up_seconds": 0,
            "think_time_ms": {"min": 0, "max": 100},
            "host": "http://test.local",
        },
        "cases": cases or [],
    }


# ---------------------------------------------------------------------------
# _validate_cases 测试
# ---------------------------------------------------------------------------

class TestValidateCases:
    def test_passes_for_api_case(self):
        ctx = _make_shared_ctx(case_registry={
            "tc001": {"component_type": "接口"},
        })
        engine = LocustLoadEngine(_make_plan(), ctx)
        # 不应抛出
        engine._validate_cases([{"id": "tc001", "execute": "是"}])

    def test_passes_for_case_without_component_type(self):
        ctx = _make_shared_ctx(case_registry={
            "tc002": {},
        })
        engine = LocustLoadEngine(_make_plan(), ctx)
        engine._validate_cases([{"id": "tc002", "execute": "是"}])

    def test_raises_for_ui_case(self):
        from rodski.core.exceptions import LoadModeUnsupportedCaseError
        ctx = _make_shared_ctx(case_registry={
            "tc003": {"component_type": "UI"},
        })
        engine = LocustLoadEngine(_make_plan(), ctx)
        with pytest.raises(LoadModeUnsupportedCaseError):
            engine._validate_cases([{"id": "tc003", "execute": "是"}])

    def test_raises_for_browser_case(self):
        from rodski.core.exceptions import LoadModeUnsupportedCaseError
        ctx = _make_shared_ctx(case_registry={
            "tc004": {"component_type": "浏览器"},
        })
        engine = LocustLoadEngine(_make_plan(), ctx)
        with pytest.raises(LoadModeUnsupportedCaseError):
            engine._validate_cases([{"id": "tc004", "execute": "是"}])

    def test_raises_error_message_contains_case_id(self):
        from rodski.core.exceptions import LoadModeUnsupportedCaseError
        ctx = _make_shared_ctx(case_registry={
            "tc_ui_99": {"component_type": "UI"},
        })
        engine = LocustLoadEngine(_make_plan(), ctx)
        with pytest.raises(LoadModeUnsupportedCaseError, match="tc_ui_99"):
            engine._validate_cases([{"id": "tc_ui_99", "execute": "是"}])


# ---------------------------------------------------------------------------
# _build_user_class 测试
# ---------------------------------------------------------------------------

class TestBuildUserClass:
    def _engine(self):
        ctx = _make_shared_ctx()
        return LocustLoadEngine(_make_plan(), ctx)

    def test_host_is_set(self):
        engine = self._engine()
        plan_cases = [{"id": "tc001", "weight": 1}]
        cls = engine._build_user_class("http://myhost:8080", 0, 200, plan_cases)
        assert cls.host == "http://myhost:8080"

    def test_task_method_exists_for_each_case(self):
        engine = self._engine()
        plan_cases = [
            {"id": "tc001", "weight": 1},
            {"id": "tc002", "weight": 3},
        ]
        cls = engine._build_user_class("http://h", 0, 100, plan_cases)
        assert hasattr(cls, "task_tc001")
        assert hasattr(cls, "task_tc002")

    def test_class_name(self):
        engine = self._engine()
        cls = engine._build_user_class("http://h", 0, 100, [])
        assert cls.__name__ == "DynamicRodskiUser"

    def test_think_max_adjusted_when_equal_to_min(self):
        """think_max_ms == think_min_ms 时应自动 +1 避免 between() 报错。"""
        engine = self._engine()
        # 只要不抛异常即可
        cls = engine._build_user_class("http://h", 500, 500, [])
        assert cls is not None

    def test_wait_time_callable(self):
        engine = self._engine()
        cls = engine._build_user_class("http://h", 100, 500, [])
        assert callable(cls.wait_time)

    def test_abstract_is_false(self):
        engine = self._engine()
        cls = engine._build_user_class("http://h", 0, 100, [])
        assert cls.abstract is False


# ---------------------------------------------------------------------------
# _collect_stats 测试
# ---------------------------------------------------------------------------

def _mock_stat_entry(num_requests=100, num_failures=5, total_rps=10.0, max_rps=15.0,
                     avg_response_time=120.0, max_response_time=800,
                     p50=100, p75=150, p95=300, p99=500):
    entry = MagicMock()
    entry.num_requests = num_requests
    entry.num_failures = num_failures
    entry.total_rps = total_rps
    entry.max_rps = max_rps
    entry.avg_response_time = avg_response_time
    entry.max_response_time = max_response_time

    def get_pct(p):
        mapping = {0.50: p50, 0.75: p75, 0.95: p95, 0.99: p99}
        return mapping.get(p, 0)

    entry.get_response_time_percentile = MagicMock(side_effect=get_pct)
    return entry


def _make_mock_env(total_entry=None, endpoint_entries: dict | None = None):
    env = MagicMock()
    total = total_entry or _mock_stat_entry()
    entries = {}
    if endpoint_entries:
        for name, entry in endpoint_entries.items():
            entries[("GET", name)] = entry
    env.stats.total = total
    env.stats.entries = entries
    return env


class TestCollectStats:
    def _engine(self):
        ctx = _make_shared_ctx()
        return LocustLoadEngine(_make_plan(), ctx)

    def test_returns_load_stats(self):
        engine = self._engine()
        env = _make_mock_env()
        result = engine._collect_stats(env)
        assert isinstance(result, LoadStats)

    def test_summary_total_requests(self):
        engine = self._engine()
        total = _mock_stat_entry(num_requests=200, num_failures=10)
        env = _make_mock_env(total_entry=total)
        result = engine._collect_stats(env)
        summary = result.summary()
        assert summary["total_requests"] == 200

    def test_summary_total_failures(self):
        engine = self._engine()
        total = _mock_stat_entry(num_requests=200, num_failures=10)
        env = _make_mock_env(total_entry=total)
        result = engine._collect_stats(env)
        assert result.summary()["total_failures"] == 10

    def test_summary_error_rate(self):
        engine = self._engine()
        total = _mock_stat_entry(num_requests=100, num_failures=5)
        env = _make_mock_env(total_entry=total)
        summary = engine._collect_stats(env).summary()
        assert summary["error_rate_pct"] == 5.0

    def test_summary_percentiles(self):
        engine = self._engine()
        total = _mock_stat_entry(p50=100, p75=150, p95=300, p99=500)
        env = _make_mock_env(total_entry=total)
        summary = engine._collect_stats(env).summary()
        assert summary["p50_ms"] == 100
        assert summary["p75_ms"] == 150
        assert summary["p95_ms"] == 300
        assert summary["p99_ms"] == 500

    def test_summary_avg_and_max(self):
        engine = self._engine()
        total = _mock_stat_entry(avg_response_time=123.456, max_response_time=999)
        env = _make_mock_env(total_entry=total)
        summary = engine._collect_stats(env).summary()
        assert summary["avg_ms"] == 123.5
        assert summary["max_ms"] == 999

    def test_summary_rps(self):
        engine = self._engine()
        total = _mock_stat_entry(total_rps=25.5, max_rps=40.0)
        env = _make_mock_env(total_entry=total)
        summary = engine._collect_stats(env).summary()
        assert summary["rps_avg"] == 25.5
        assert summary["rps_peak"] == 40.0

    def test_per_endpoint_entries(self):
        engine = self._engine()
        ep1 = _mock_stat_entry(num_requests=50, num_failures=2, p95=200)
        ep2 = _mock_stat_entry(num_requests=30, num_failures=0, p95=150)
        env = _make_mock_env(endpoint_entries={
            "/api/login": ep1,
            "/api/order": ep2,
        })
        result = engine._collect_stats(env)
        endpoints = result.per_endpoint()
        names = {ep["name"] for ep in endpoints}
        assert "/api/login" in names
        assert "/api/order" in names

    def test_per_endpoint_p95(self):
        engine = self._engine()
        ep = _mock_stat_entry(num_requests=80, num_failures=4, p95=350)
        env = _make_mock_env(endpoint_entries={"/api/test": ep})
        endpoints = engine._collect_stats(env).per_endpoint()
        ep_data = next(e for e in endpoints if e["name"] == "/api/test")
        assert ep_data["p95_ms"] == 350

    def test_zero_requests_no_division_error(self):
        engine = self._engine()
        total = _mock_stat_entry(num_requests=0, num_failures=0,
                                 avg_response_time=0, max_response_time=0,
                                 p50=0, p75=0, p95=0, p99=0)
        env = _make_mock_env(total_entry=total)
        summary = engine._collect_stats(env).summary()
        # 0 / max(0, 1) = 0，不应 ZeroDivisionError
        assert summary["error_rate_pct"] == 0.0


# ---------------------------------------------------------------------------
# LoadStats._locust_summary / _locust_endpoints 优先级测试
# ---------------------------------------------------------------------------

class TestLoadStatsPriority:
    def test_summary_uses_locust_summary_when_present(self):
        stats = LoadStats()
        stats._locust_summary = {"total_requests": 999, "custom": True}
        assert stats.summary() == {"total_requests": 999, "custom": True}

    def test_summary_falls_back_to_records(self):
        from rodski.load.stats import RequestRecord
        stats = LoadStats()
        stats.record(RequestRecord(name="ep", elapsed_ms=100, success=True))
        summary = stats.summary()
        assert summary["total_requests"] == 1

    def test_per_endpoint_uses_locust_endpoints_when_present(self):
        stats = LoadStats()
        stats._locust_endpoints = [{"name": "/api/x", "requests": 10}]
        assert stats.per_endpoint() == [{"name": "/api/x", "requests": 10}]

    def test_per_endpoint_falls_back_to_records(self):
        from rodski.load.stats import RequestRecord
        stats = LoadStats()
        stats.record(RequestRecord(name="/api/y", elapsed_ms=50, success=True))
        endpoints = stats.per_endpoint()
        assert len(endpoints) == 1
        assert endpoints[0]["name"] == "/api/y"


# ---------------------------------------------------------------------------
# _resolve_host 测试
# ---------------------------------------------------------------------------

class TestResolveHost:
    def test_resolves_from_global_values(self):
        ctx = _make_shared_ctx(global_values={"DefaultValue": {"URL": "http://gv.host"}})
        engine = LocustLoadEngine(_make_plan(profile={"host": None}), ctx)
        assert engine._resolve_host() == "http://gv.host"

    def test_defaults_to_localhost_when_no_gv(self):
        ctx = _make_shared_ctx(global_values={})
        engine = LocustLoadEngine(_make_plan(), ctx)
        assert engine._resolve_host() == "http://localhost"
