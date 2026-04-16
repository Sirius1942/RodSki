"""Agent vs Generic Agent 对比实验框架单元测试。

测试 rodski-agent/benchmark/comparison.py 中的所有公开类与方法。
覆盖：ComparisonDimension 常量、ExperimentConfig、ComparisonExperiment
数据采集/报告生成/Markdown 输出。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# benchmark/ 目录不在 src/ 包内，需要将其加入 sys.path
_AGENT_ROOT = Path(__file__).resolve().parents[1]
_BENCHMARK_DIR = _AGENT_ROOT / "benchmark"
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

from benchmark.comparison import (
    ComparisonDimension,
    ComparisonExperiment,
    ComparisonResult,
    DimensionResult,
    ExperimentConfig,
)
from rodski_agent.common.kpi import (
    EfficiencyMetrics,
    KPIMetrics,
    QualityMetrics,
    SelfHealingMetrics,
)


# ============================================================
# 测试数据 fixtures
# ============================================================


def _make_span(
    name: str,
    start_ns: int,
    end_ns: int,
    status: str = "ok",
    attributes: dict | None = None,
) -> dict:
    """快速构建一个 span 字典。"""
    return {
        "name": name,
        "traceId": "aabbccdd" * 4,
        "spanId": "11223344" * 2,
        "startTimeUnixNano": start_ns,
        "endTimeUnixNano": end_ns,
        "attributes": attributes or {},
        "status": status,
    }


def _sample_kpi() -> KPIMetrics:
    """返回一个有代表性数值的 KPIMetrics。"""
    return KPIMetrics(
        efficiency=EfficiencyMetrics(
            t_design=12.0,
            t_execute=3.5,
            t_fix=5.0,
            token_per_case=1500.0,
            cost_per_case=0.05,
        ),
        quality=QualityMetrics(
            first_pass_rate=80.0,
            valid_assertion_pct=90.0,
            xml_validity_rate=95.0,
        ),
        self_healing=SelfHealingMetrics(
            fix_success_pct=70.0,
            mttr_auto=4.0,
        ),
    )


def _sample_generic_metrics() -> dict:
    """返回 generic agent 的手动录入指标。"""
    return {
        ComparisonDimension.GENERATION_SPEED: 45.0,
        ComparisonDimension.FIRST_SUCCESS_RATE: 55.0,
        ComparisonDimension.MAINTENANCE_COST: 120.0,
        ComparisonDimension.TOKEN_CONSUMPTION: 5000.0,
        ComparisonDimension.SELF_HEALING: 0.0,
        ComparisonDimension.CROSS_PLATFORM: 300.0,
    }


# ============================================================
# ComparisonDimension
# ============================================================


class TestComparisonDimension:
    """ComparisonDimension -- 维度常量与元数据"""

    def test_ALL_包含六个维度(self):
        """ALL 列表应包含全部 6 个对比维度。"""
        assert len(ComparisonDimension.ALL) == 6

    def test_所有维度有描述(self):
        """每个维度都应在 DESCRIPTIONS 中有对应的描述。"""
        for dim in ComparisonDimension.ALL:
            assert dim in ComparisonDimension.DESCRIPTIONS
            desc = ComparisonDimension.DESCRIPTIONS[dim]
            assert "unit" in desc

    def test_维度值为字符串(self):
        """每个维度常量应为字符串类型。"""
        assert isinstance(ComparisonDimension.GENERATION_SPEED, str)
        assert isinstance(ComparisonDimension.SELF_HEALING, str)
        assert isinstance(ComparisonDimension.CROSS_PLATFORM, str)


# ============================================================
# ExperimentConfig
# ============================================================


class TestExperimentConfig:
    """ExperimentConfig -- 实验配置数据模型"""

    def test_默认值(self):
        """ExperimentConfig 默认值应合理。"""
        config = ExperimentConfig()
        assert config.suite_dir == ""
        assert config.repetitions == 3
        assert len(config.dimensions) == 6

    def test_自定义维度(self):
        """应支持只选择部分维度进行对比。"""
        config = ExperimentConfig(
            suite_dir="/suite",
            dimensions=[
                ComparisonDimension.GENERATION_SPEED,
                ComparisonDimension.TOKEN_CONSUMPTION,
            ],
        )
        assert len(config.dimensions) == 2
        assert ComparisonDimension.GENERATION_SPEED in config.dimensions


# ============================================================
# ComparisonExperiment — 数据采集
# ============================================================


class TestDataCollection:
    """ComparisonExperiment -- 指标采集"""

    def test_collect_rodski_metrics_from_kpi(self):
        """直接传入 KPIMetrics 对象时应正确采集。"""
        exp = ComparisonExperiment()
        kpi = _sample_kpi()
        result = exp.collect_rodski_metrics(kpi=kpi)
        assert result["efficiency"]["t_design"] == 12.0
        assert result["quality"]["first_pass_rate"] == 80.0

    def test_collect_rodski_metrics_from_spans(self):
        """从 spans + token_records 计算 KPI 时应返回非空字典。"""
        sec = 1_000_000_000
        base = 1_000_000_000_000_000_000
        spans = [
            _make_span("design_case", base, base + 8 * sec),
            _make_span(
                "execute_case_1", base + 8 * sec, base + 11 * sec,
                attributes={"retry_count": 0},
            ),
        ]
        token_records = [
            {
                "purpose": "design",
                "total_tokens": 1000,
                "cost_usd": 0.01,
            },
        ]
        exp = ComparisonExperiment()
        result = exp.collect_rodski_metrics(
            spans=spans, token_records=token_records,
        )
        assert result["efficiency"]["t_design"] > 0

    def test_collect_generic_metrics(self):
        """collect_generic_metrics 应保存并返回手动录入数据。"""
        exp = ComparisonExperiment()
        metrics = _sample_generic_metrics()
        result = exp.collect_generic_metrics(metrics)
        assert result[ComparisonDimension.GENERATION_SPEED] == 45.0
        assert result[ComparisonDimension.SELF_HEALING] == 0.0

    def test_collect_generic_metrics_累加更新(self):
        """多次调用 collect_generic_metrics 应累加/覆盖值。"""
        exp = ComparisonExperiment()
        exp.collect_generic_metrics({ComparisonDimension.GENERATION_SPEED: 40.0})
        exp.collect_generic_metrics({ComparisonDimension.GENERATION_SPEED: 50.0})
        result = exp.collect_generic_metrics()
        assert result[ComparisonDimension.GENERATION_SPEED] == 50.0

    def test_collect_generic_metrics_无参数返回当前值(self):
        """不传参数时应返回已有的 metrics 而非报错。"""
        exp = ComparisonExperiment()
        result = exp.collect_generic_metrics()
        assert isinstance(result, dict)
        assert len(result) == 0


# ============================================================
# ComparisonExperiment — 报告生成
# ============================================================


class TestReportGeneration:
    """ComparisonExperiment -- 报告生成"""

    def _setup_experiment(self) -> ComparisonExperiment:
        """创建一个已采集双方数据的实验。"""
        exp = ComparisonExperiment(ExperimentConfig(suite_dir="/suite/demo"))
        exp.collect_rodski_metrics(kpi=_sample_kpi())
        exp.collect_generic_metrics(_sample_generic_metrics())
        return exp

    def test_generate_report_结构完整(self):
        """generate_report 应返回包含所有字段的 ComparisonResult。"""
        exp = self._setup_experiment()
        result = exp.generate_report()
        assert isinstance(result, ComparisonResult)
        assert result.experiment_id != ""
        assert result.timestamp != ""
        assert len(result.dimensions) > 0
        assert result.rodski_kpi is not None
        assert len(result.generic_metrics) > 0

    def test_generate_report_维度数量正确(self):
        """报告中的维度数量应等于配置中的维度数量。"""
        config = ExperimentConfig(
            dimensions=[
                ComparisonDimension.GENERATION_SPEED,
                ComparisonDimension.FIRST_SUCCESS_RATE,
            ],
        )
        exp = ComparisonExperiment(config)
        exp.collect_rodski_metrics(kpi=_sample_kpi())
        exp.collect_generic_metrics(_sample_generic_metrics())
        result = exp.generate_report()
        assert len(result.dimensions) == 2

    def test_generate_report_rodski胜出维度正确(self):
        """rodski-agent 在速度和自愈维度应胜出。"""
        exp = self._setup_experiment()
        result = exp.generate_report()

        # rodski t_design=12 < generic 45 => rodski better (lower is better)
        speed_dim = next(
            (d for d in result.dimensions
             if d.dimension == ComparisonDimension.GENERATION_SPEED),
            None,
        )
        assert speed_dim is not None
        assert speed_dim.rodski_better is True

        # rodski self_healing=70 > generic 0 => rodski better (higher is better)
        heal_dim = next(
            (d for d in result.dimensions
             if d.dimension == ComparisonDimension.SELF_HEALING),
            None,
        )
        assert heal_dim is not None
        assert heal_dim.rodski_better is True

    def test_generate_report_summary非空(self):
        """summary 应包含人类可读的对比总结。"""
        exp = self._setup_experiment()
        result = exp.generate_report()
        assert len(result.summary) > 0
        assert "dimensions" in result.summary.lower() or "compared" in result.summary.lower()

    def test_generate_report_to_dict可序列化(self):
        """ComparisonResult.to_dict() 输出应可被 json.dumps 序列化。"""
        exp = self._setup_experiment()
        result = exp.generate_report()
        d = result.to_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert len(text) > 0

    def test_generate_report_to_json格式(self):
        """ComparisonResult.to_json() 应输出格式化 JSON 字符串。"""
        exp = self._setup_experiment()
        result = exp.generate_report()
        text = result.to_json()
        parsed = json.loads(text)
        assert parsed["experiment_id"] == result.experiment_id


# ============================================================
# ComparisonExperiment — Markdown 报告
# ============================================================


class TestMarkdownReport:
    """ComparisonExperiment -- Markdown 报告生成"""

    def test_markdown_report_包含表格(self):
        """Markdown 报告应包含对比表格。"""
        exp = ComparisonExperiment(ExperimentConfig(suite_dir="/suite/demo"))
        exp.collect_rodski_metrics(kpi=_sample_kpi())
        exp.collect_generic_metrics(_sample_generic_metrics())
        md = exp.generate_markdown_report()
        assert "| Dimension |" in md
        assert "rodski-agent" in md
        assert "Generic" in md

    def test_markdown_report_包含标题(self):
        """Markdown 报告应包含标题和实验元信息。"""
        exp = ComparisonExperiment(ExperimentConfig(suite_dir="/suite/demo"))
        exp.collect_rodski_metrics(kpi=_sample_kpi())
        exp.collect_generic_metrics(_sample_generic_metrics())
        md = exp.generate_markdown_report()
        assert "# Agent Comparison Report" in md
        assert "Experiment ID" in md
        assert "Suite" in md

    def test_markdown_report_无数据不崩溃(self):
        """即使没有采集任何数据也应生成报告而非抛出异常。"""
        exp = ComparisonExperiment()
        md = exp.generate_markdown_report()
        assert isinstance(md, str)
        assert len(md) > 0


# ============================================================
# DimensionResult — 数据模型
# ============================================================


class TestDimensionResult:
    """DimensionResult -- 维度结果数据模型"""

    def test_默认值(self):
        """DimensionResult 默认值应全为零/空。"""
        dim = DimensionResult()
        assert dim.dimension == ""
        assert dim.rodski_value == 0.0
        assert dim.generic_value == 0.0
        assert dim.rodski_better is None

    def test_赋值后字段正确(self):
        """设置自定义值后各字段应正确。"""
        dim = DimensionResult(
            dimension=ComparisonDimension.GENERATION_SPEED,
            rodski_value=12.0,
            generic_value=45.0,
            unit="seconds",
            rodski_better=True,
            notes="rodski uses XML generation",
        )
        assert dim.dimension == "generation_speed"
        assert dim.rodski_value == 12.0
        assert dim.rodski_better is True


# ============================================================
# 边界与集成
# ============================================================


class TestEdgeCases:
    """边界条件与集成场景"""

    def test_双方值均为零时tie(self):
        """双方某维度值都为 0 时 rodski_better 应为 None。"""
        exp = ComparisonExperiment(
            ExperimentConfig(
                dimensions=[ComparisonDimension.CROSS_PLATFORM],
            ),
        )
        # rodski CROSS_PLATFORM 默认为 0.0（从 KPI 无法自动提取）
        exp.collect_rodski_metrics(kpi=KPIMetrics())
        exp.collect_generic_metrics({ComparisonDimension.CROSS_PLATFORM: 0.0})
        result = exp.generate_report()
        cross_dim = result.dimensions[0]
        assert cross_dim.rodski_better is None

    def test_重复调用generate_report不报错(self):
        """多次调用 generate_report 应每次返回独立的结果。"""
        exp = ComparisonExperiment()
        exp.collect_rodski_metrics(kpi=_sample_kpi())
        exp.collect_generic_metrics(_sample_generic_metrics())
        r1 = exp.generate_report()
        r2 = exp.generate_report()
        assert r1.experiment_id != r2.experiment_id
