"""Benchmark 运行器单元测试。

测试 src/rodski_agent/common/benchmark.py 中 BenchmarkRunner 的所有公开方法。
覆盖：运行基准测试、结果序列化/反序列化、历史管理、运行对比。
所有文件系统操作通过 pytest tmp_path 隔离。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rodski_agent.common.benchmark import (
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkRunner,
)
from rodski_agent.common.kpi import (
    EfficiencyMetrics,
    KPIMetrics,
    QualityMetrics,
    SelfHealingMetrics,
)


# ============================================================
# 测试数据
# ============================================================


def _make_span(
    name: str,
    start_ns: int,
    end_ns: int,
    status: str = "ok",
    attributes: dict | None = None,
) -> dict:
    return {
        "name": name,
        "traceId": "aabbccdd" * 4,
        "spanId": "11223344" * 2,
        "startTimeUnixNano": start_ns,
        "endTimeUnixNano": end_ns,
        "attributes": attributes or {},
        "status": status,
    }


def _make_token_record(
    purpose: str = "design",
    total_tokens: int = 1000,
    cost_usd: float = 0.01,
) -> dict:
    return {
        "timestamp": "2025-01-01T00:00:00",
        "provider": "claude",
        "model": "claude-sonnet-4-20250514",
        "purpose": purpose,
        "input_tokens": total_tokens // 2,
        "output_tokens": total_tokens // 2,
        "total_tokens": total_tokens,
        "duration_ms": 500,
        "cost_usd": cost_usd,
        "success": True,
    }


def _sample_executor():
    """返回示例 spans 和 token_records 的 executor 回调。"""
    sec = 1_000_000_000
    base = 1_000_000_000_000_000_000

    spans = [
        _make_span("design_case", base, base + 10 * sec),
        _make_span(
            "execute_case_1", base + 10 * sec, base + 13 * sec,
            attributes={"retry_count": 0},
        ),
    ]
    token_records = [
        _make_token_record("design", 2000, 0.02),
    ]
    return spans, token_records


@pytest.fixture
def runner(tmp_path: Path) -> BenchmarkRunner:
    """创建一个使用临时目录的 BenchmarkRunner 实例。"""
    return BenchmarkRunner(results_dir=tmp_path / "benchmark_results")


# ============================================================
# BenchmarkConfig
# ============================================================


class TestBenchmarkConfig:
    """BenchmarkConfig — 配置数据模型"""

    def test_默认值(self):
        """BenchmarkConfig 默认值应合理。"""
        config = BenchmarkConfig()
        assert config.suite_dir == ""
        assert config.repetitions == 1
        assert config.tags == []

    def test_自定义值(self):
        """BenchmarkConfig 应接受自定义值。"""
        config = BenchmarkConfig(
            suite_dir="/path/to/suite",
            repetitions=5,
            tags=["nightly", "smoke"],
            extra={"timeout": 30},
        )
        assert config.suite_dir == "/path/to/suite"
        assert config.repetitions == 5
        assert "nightly" in config.tags


# ============================================================
# BenchmarkResult — 序列化
# ============================================================


class TestBenchmarkResult:
    """BenchmarkResult — 序列化与反序列化"""

    def test_to_dict_结构(self):
        """to_dict 应包含所有必要字段。"""
        result = BenchmarkResult(
            run_id="abc123",
            suite_name="login_suite",
            timestamp="2025-01-01T00:00:00+00:00",
            kpi=KPIMetrics(efficiency=EfficiencyMetrics(t_design=5.0)),
        )
        d = result.to_dict()
        assert d["run_id"] == "abc123"
        assert d["suite_name"] == "login_suite"
        assert d["kpi"]["efficiency"]["t_design"] == 5.0

    def test_to_json_可解析(self):
        """to_json 输出应为合法 JSON。"""
        result = BenchmarkResult(run_id="x", suite_name="s")
        text = result.to_json()
        parsed = json.loads(text)
        assert parsed["run_id"] == "x"

    def test_from_dict_往返(self):
        """to_dict → from_dict 应还原所有字段。"""
        original = BenchmarkResult(
            run_id="test123",
            suite_name="my_suite",
            timestamp="2025-06-01T12:00:00+00:00",
            config={"suite_dir": "/s", "repetitions": 3},
            kpi=KPIMetrics(
                efficiency=EfficiencyMetrics(t_design=8.0, cost_per_case=0.05),
                quality=QualityMetrics(first_pass_rate=90.0),
                self_healing=SelfHealingMetrics(fix_success_pct=75.0),
            ),
            metadata={"span_count": 10},
        )
        d = original.to_dict()
        restored = BenchmarkResult.from_dict(d)
        assert restored.run_id == "test123"
        assert restored.suite_name == "my_suite"
        assert restored.kpi.efficiency.t_design == 8.0
        assert restored.kpi.quality.first_pass_rate == 90.0
        assert restored.kpi.self_healing.fix_success_pct == 75.0

    def test_from_dict_处理缺失字段(self):
        """from_dict 在缺少字段时应使用默认值而非报错。"""
        data = {"run_id": "partial", "suite_name": "s"}
        result = BenchmarkResult.from_dict(data)
        assert result.run_id == "partial"
        assert result.kpi.efficiency.t_design == 0.0


# ============================================================
# BenchmarkRunner — 运行基准测试
# ============================================================


class TestRunBenchmark:
    """BenchmarkRunner.run_benchmark — 运行基准测试"""

    def test_无executor运行返回空KPI(self, runner: BenchmarkRunner):
        """不提供 executor 时应返回全零 KPI 的结果。"""
        result = runner.run_benchmark("/path/to/suite")
        assert result.run_id != ""
        assert result.suite_name == "suite"
        assert result.kpi.efficiency.t_design == 0.0

    def test_有executor运行计算KPI(self, runner: BenchmarkRunner):
        """提供 executor 时应正确计算 KPI。"""
        result = runner.run_benchmark(
            "/path/to/my_suite",
            executor=_sample_executor,
        )
        assert result.suite_name == "my_suite"
        assert result.kpi.efficiency.t_design > 0
        assert result.metadata["span_count"] == 2
        assert result.metadata["token_record_count"] == 1

    def test_自定义config(self, runner: BenchmarkRunner):
        """自定义 config 应正确反映在结果中。"""
        config = BenchmarkConfig(
            suite_dir="/suite",
            repetitions=5,
            tags=["nightly"],
        )
        result = runner.run_benchmark("/suite", config=config)
        assert result.config["repetitions"] == 5
        assert "nightly" in result.config["tags"]

    def test_运行后文件已保存(self, runner: BenchmarkRunner):
        """运行完成后结果 JSON 文件应已保存到 results_dir。"""
        result = runner.run_benchmark("/suite/login")
        files = list(runner.results_dir.glob("*.json"))
        assert len(files) == 1

        # 验证文件内容
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["run_id"] == result.run_id

    def test_timestamp_格式(self, runner: BenchmarkRunner):
        """timestamp 应为 ISO 格式且包含时区信息。"""
        result = runner.run_benchmark("/suite")
        assert "T" in result.timestamp
        assert "+" in result.timestamp or "Z" in result.timestamp


# ============================================================
# BenchmarkRunner — 对比
# ============================================================


class TestBenchmarkCompare:
    """BenchmarkRunner.compare — 运行结果对比"""

    def test_对比两次运行(self, runner: BenchmarkRunner):
        """compare 应返回包含 diff 和 summary 的字典。"""
        run_a = BenchmarkResult(
            run_id="aaa",
            suite_name="s",
            kpi=KPIMetrics(efficiency=EfficiencyMetrics(t_design=20.0)),
        )
        run_b = BenchmarkResult(
            run_id="bbb",
            suite_name="s",
            kpi=KPIMetrics(efficiency=EfficiencyMetrics(t_design=10.0)),
        )
        comparison = BenchmarkRunner.compare(run_a, run_b)
        assert comparison["baseline_run_id"] == "aaa"
        assert comparison["current_run_id"] == "bbb"
        assert "diff" in comparison
        assert "entries" in comparison["diff"]
        assert "summary" in comparison["diff"]

    def test_对比结果包含改善信息(self):
        """当指标改善时 diff 中应标记 improved。"""
        run_a = BenchmarkResult(
            run_id="baseline",
            suite_name="s",
            kpi=KPIMetrics(
                efficiency=EfficiencyMetrics(t_design=20.0),
                quality=QualityMetrics(first_pass_rate=50.0),
            ),
        )
        run_b = BenchmarkResult(
            run_id="current",
            suite_name="s",
            kpi=KPIMetrics(
                efficiency=EfficiencyMetrics(t_design=10.0),
                quality=QualityMetrics(first_pass_rate=80.0),
            ),
        )
        comparison = BenchmarkRunner.compare(run_a, run_b)
        assert comparison["diff"]["summary"]["improved"] >= 2


# ============================================================
# BenchmarkRunner — 历史管理
# ============================================================


class TestHistoryManagement:
    """BenchmarkRunner — 结果持久化与历史管理"""

    def test_load_result_找到结果(self, runner: BenchmarkRunner):
        """load_result 应能按 run_id 找到保存的结果。"""
        result = runner.run_benchmark("/suite/a")
        loaded = runner.load_result(result.run_id)
        assert loaded is not None
        assert loaded.run_id == result.run_id
        assert loaded.suite_name == result.suite_name

    def test_load_result_未找到返回None(self, runner: BenchmarkRunner):
        """load_result 查不到 run_id 时应返回 None。"""
        assert runner.load_result("nonexistent") is None

    def test_load_result_目录不存在返回None(self, tmp_path: Path):
        """results_dir 不存在时 load_result 应返回 None。"""
        runner = BenchmarkRunner(results_dir=tmp_path / "nonexistent_dir")
        assert runner.load_result("any") is None

    def test_list_results_返回所有结果(self, runner: BenchmarkRunner):
        """list_results 无过滤时应返回所有保存的结果。"""
        runner.run_benchmark("/suite/a")
        runner.run_benchmark("/suite/b")
        results = runner.list_results()
        assert len(results) == 2

    def test_list_results_按suite过滤(self, runner: BenchmarkRunner):
        """list_results(suite_name=...) 应只返回匹配的结果。"""
        runner.run_benchmark("/path/to/login")
        runner.run_benchmark("/path/to/checkout")
        runner.run_benchmark("/path/to/login")

        login_results = runner.list_results(suite_name="login")
        assert len(login_results) == 2

        checkout_results = runner.list_results(suite_name="checkout")
        assert len(checkout_results) == 1

    def test_list_results_按时间降序排列(self, runner: BenchmarkRunner):
        """list_results 返回的结果应按 timestamp 降序排列。"""
        runner.run_benchmark("/suite/a")
        runner.run_benchmark("/suite/b")
        results = runner.list_results()
        if len(results) >= 2:
            assert results[0].timestamp >= results[1].timestamp

    def test_list_results_目录不存在返回空列表(self, tmp_path: Path):
        """results_dir 不存在时 list_results 应返回空列表。"""
        runner = BenchmarkRunner(results_dir=tmp_path / "nonexistent")
        assert runner.list_results() == []

    def test_delete_result_成功删除(self, runner: BenchmarkRunner):
        """delete_result 应删除对应文件并返回 True。"""
        result = runner.run_benchmark("/suite/a")
        assert runner.delete_result(result.run_id) is True
        assert runner.load_result(result.run_id) is None

    def test_delete_result_未找到返回False(self, runner: BenchmarkRunner):
        """delete_result 找不到 run_id 时应返回 False。"""
        assert runner.delete_result("nonexistent") is False

    def test_delete_result_目录不存在返回False(self, tmp_path: Path):
        """results_dir 不存在时 delete_result 应返回 False。"""
        runner = BenchmarkRunner(results_dir=tmp_path / "nonexistent")
        assert runner.delete_result("any") is False

    def test_多次运行文件独立(self, runner: BenchmarkRunner):
        """每次 run_benchmark 应生成独立的 JSON 文件。"""
        runner.run_benchmark("/suite/a")
        runner.run_benchmark("/suite/a")
        runner.run_benchmark("/suite/b")
        files = list(runner.results_dir.glob("*.json"))
        assert len(files) == 3
