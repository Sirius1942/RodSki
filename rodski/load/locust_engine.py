"""LocustLoadEngine — 接口压测执行引擎（api 模式）。
使用 Locust LocalRunner 编排 VU，驱动 RodskiLoadUser 并发执行。
"""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .context import SharedLoadContext
    from .stats import LoadStats


def _require_locust():
    try:
        import locust
        return locust
    except ImportError:
        try:
            from ..core.exceptions import LoadDependencyMissingError
        except ImportError:
            from core.exceptions import LoadDependencyMissingError
        raise LoadDependencyMissingError()


class LocustLoadEngine:
    """接口压测引擎（api 模式，Locust 后端）。"""

    def __init__(self, plan: dict, shared_ctx: "SharedLoadContext"):
        self.plan = plan
        self.shared_ctx = shared_ctx

    def run(self) -> "LoadStats":
        """执行压测，返回 LoadStats。"""
        _require_locust()

        # gevent monkey-patch 按需执行（仅在压测模式）
        import gevent.monkey
        gevent.monkey.patch_all()

        import gevent
        from locust.env import Environment
        from locust import FastHttpUser, task, between, constant

        from .stats import LoadStats, RequestRecord
        from .user import RodskiLoadUser

        try:
            from ..core.exceptions import LoadModeUnsupportedCaseError
        except ImportError:
            from core.exceptions import LoadModeUnsupportedCaseError

        profile = self.plan.get("load_profile", {})
        concurrency    = int(profile.get("concurrency", 1))
        duration       = int(profile.get("duration_seconds", 30))
        ramp_up        = int(profile.get("ramp_up_seconds", 0))
        think_min_ms   = int(profile.get("think_time_ms", {}).get("min", 0))
        think_max_ms   = int(profile.get("think_time_ms", {}).get("max", 0))
        host           = profile.get("host") or self._resolve_host()

        # 校验：所有 case 必须是 component_type="接口"
        plan_cases = [c for c in self.plan.get("cases", []) if c.get("execute") == "是"]
        self._validate_cases(plan_cases)

        # 动态生成 RodskiLoadUser 子类
        user_class = self._build_user_class(
            host, think_min_ms, think_max_ms, plan_cases
        )

        # 初始化 Locust 环境
        env = Environment(user_classes=[user_class])
        env.create_local_runner()

        # 爬坡策略
        spawn_rate = max(1, concurrency // max(ramp_up, 1)) if ramp_up > 0 else concurrency

        # 启动 VU
        env.runner.start(user_count=concurrency, spawn_rate=spawn_rate)

        # 持续运行 duration 秒后停止
        gevent.spawn_later(duration, lambda: env.runner.quit())
        env.runner.greenlet.join()

        # 采集指标
        return self._collect_stats(env)

    def _resolve_host(self) -> str:
        gv = self.shared_ctx.global_values
        return gv.get("DefaultValue", {}).get("URL", "http://localhost")

    def _validate_cases(self, plan_cases: list) -> None:
        try:
            from ..core.exceptions import LoadModeUnsupportedCaseError
        except ImportError:
            from core.exceptions import LoadModeUnsupportedCaseError

        for case_cfg in plan_cases:
            case_id = case_cfg["id"]
            case_def = self.shared_ctx.case_registry.get(case_id, {})
            comp_type = case_def.get("component_type", "")
            if comp_type and comp_type != "接口":
                raise LoadModeUnsupportedCaseError(
                    f"压测计划（api 模式）不支持 component_type='{comp_type}' 的 case: {case_id}"
                )

    def _build_user_class(self, host, think_min_ms, think_max_ms, plan_cases):
        from locust import FastHttpUser, task, between, constant

        if think_max_ms <= think_min_ms:
            think_max_ms = think_min_ms + 1

        shared_ctx = self.shared_ctx
        task_methods = {}
        for case_cfg in plan_cases:
            case_id = case_cfg["id"]
            weight = int(case_cfg.get("weight", 1))

            def make_task(cid, w):
                def task_fn(self_user):
                    self_user._execute_case(cid)
                task_fn.__name__ = f"task_{cid}"
                return task(w)(task_fn)

            task_methods[f"task_{case_id}"] = make_task(case_id, weight)

        from locust import FastHttpUser, between
        from .user import RodskiLoadUser

        DynamicUser = type(
            "DynamicRodskiUser",
            (RodskiLoadUser, FastHttpUser),
            {
                "host": host,
                "wait_time": between(think_min_ms / 1000, think_max_ms / 1000),
                "_shared_ctx": shared_ctx,
                "abstract": False,
                **task_methods,
            },
        )
        return DynamicUser

    def _collect_stats(self, env) -> "LoadStats":
        from .stats import LoadStats, RequestRecord

        stats = LoadStats()
        locust_stats = env.stats

        for entry_key, entry in locust_stats.entries.items():
            name = entry_key[1] if isinstance(entry_key, tuple) else str(entry_key)
            # 从 Locust stats 重建 RequestRecord 列表（近似：用响应时间分布）
            # Locust stats 是聚合数据，我们只能从 total 取汇总值
            # 对于精确 per-request 数据，需要 events hook；v8.0 用聚合数据足够
            pass

        # 直接从 Locust total stats 构造摘要
        total = locust_stats.total
        # 用 Locust 内置的百分位方法
        p50  = total.get_response_time_percentile(0.50) or 0
        p75  = total.get_response_time_percentile(0.75) or 0
        p95  = total.get_response_time_percentile(0.95) or 0
        p99  = total.get_response_time_percentile(0.99) or 0

        # 将 Locust 汇总填充到 LoadStats（通过内部 _summary 覆盖方式）
        # 注：LoadStats 默认从 records 计算，这里直接赋予预计算摘要
        stats._locust_summary = {
            "total_requests": total.num_requests,
            "total_failures": total.num_failures,
            "error_rate_pct": round(
                total.num_failures / max(total.num_requests, 1) * 100, 3
            ),
            "rps_avg": round(getattr(total, "total_rps", 0.0), 2),
            "rps_peak": round(getattr(total, "max_rps", 0.0), 2),
            "p50_ms":  int(p50),
            "p75_ms":  int(p75),
            "p95_ms":  int(p95),
            "p99_ms":  int(p99),
            "avg_ms":  round(total.avg_response_time or 0, 1),
            "max_ms":  int(total.max_response_time or 0),
        }
        stats._locust_endpoints = []
        for entry_key, entry in locust_stats.entries.items():
            name = entry_key[1] if isinstance(entry_key, tuple) else str(entry_key)
            ep_p95 = entry.get_response_time_percentile(0.95) or 0
            stats._locust_endpoints.append({
                "name":      name,
                "requests":  entry.num_requests,
                "failures":  entry.num_failures,
                "rps_avg":   round(getattr(entry, "total_rps", 0.0), 2),
                "p95_ms":    int(ep_p95),
            })

        return stats
