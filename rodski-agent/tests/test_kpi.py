"""KPI 计算框架单元测试。

测试 src/rodski_agent/common/kpi.py 中的所有公开类与方法。
覆盖：KPIMetrics 序列化、KPICalculator 效率/质量/自愈指标计算、KPI 对比。
"""
from __future__ import annotations

import json

import pytest

from rodski_agent.common.kpi import (
    EfficiencyMetrics,
    KPICalculator,
    KPIDiff,
    KPIDiffEntry,
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
    """快速构建一个 span 字典（模拟 Span.to_dict() 输出）。"""
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
    """快速构建一个 token 记录字典。"""
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


@pytest.fixture
def sample_spans() -> list[dict]:
    """包含 design、execute、fix 阶段的 span 列表。"""
    sec = 1_000_000_000  # 1 秒 = 1e9 纳秒
    base = 1_000_000_000_000_000_000  # 某个起始时间

    return [
        # design 阶段 — 10 秒
        _make_span("design_case", base, base + 10 * sec),
        # execute 阶段 — 3 条用例，各 2/3/5 秒
        _make_span(
            "execute_case_1", base + 10 * sec, base + 12 * sec,
            attributes={"retry_count": 0, "total_assertions": 5, "valid_assertions": 5},
        ),
        _make_span(
            "execute_case_2", base + 12 * sec, base + 15 * sec,
            status="error",
            attributes={"retry_count": 1, "total_assertions": 3, "valid_assertions": 2},
        ),
        _make_span(
            "execute_case_3", base + 15 * sec, base + 20 * sec,
            attributes={"retry_count": 0, "total_assertions": 4, "valid_assertions": 4,
                        "xml_valid": True},
        ),
        # fix 阶段 — 2 次修复
        _make_span(
            "fix_locator", base + 20 * sec, base + 25 * sec,
            attributes={"fix_success": True, "fix_strategy": "update_locator"},
        ),
        _make_span(
            "fix_wait", base + 25 * sec, base + 30 * sec,
            attributes={"fix_success": False, "fix_strategy": "add_wait"},
        ),
    ]


@pytest.fixture
def sample_token_records() -> list[dict]:
    """示例 token 记录。"""
    return [
        _make_token_record("design", 2000, 0.02),
        _make_token_record("design", 1500, 0.015),
        _make_token_record("fix", 800, 0.008),
        _make_token_record("diagnosis", 500, 0.005),
    ]


# ============================================================
# KPIMetrics 数据模型
# ============================================================


class TestKPIMetrics:
    """KPIMetrics — 数据模型与序列化"""

    def test_默认值全为零(self):
        """KPIMetrics 默认初始化后所有数值字段应为 0。"""
        kpi = KPIMetrics()
        d = kpi.to_dict()
        assert d["efficiency"]["t_design"] == 0.0
        assert d["quality"]["first_pass_rate"] == 0.0
        assert d["self_healing"]["fix_success_pct"] == 0.0

    def test_to_dict_结构正确(self):
        """to_dict 应包含 efficiency/quality/self_healing 三个顶级键。"""
        kpi = KPIMetrics()
        d = kpi.to_dict()
        assert "efficiency" in d
        assert "quality" in d
        assert "self_healing" in d

    def test_to_json_可解析(self):
        """to_json 输出应为合法 JSON 字符串。"""
        kpi = KPIMetrics(
            efficiency=EfficiencyMetrics(t_design=5.0, cost_per_case=0.05),
        )
        text = kpi.to_json()
        parsed = json.loads(text)
        assert parsed["efficiency"]["t_design"] == 5.0
        assert parsed["efficiency"]["cost_per_case"] == 0.05

    def test_自定义值序列化(self):
        """设置自定义值后 to_dict 应正确反映。"""
        kpi = KPIMetrics(
            efficiency=EfficiencyMetrics(t_execute=3.5),
            quality=QualityMetrics(first_pass_rate=85.0),
            self_healing=SelfHealingMetrics(
                fix_success_pct=60.0,
                fix_by_strategy={"update_locator": 80.0, "add_wait": 40.0},
            ),
        )
        d = kpi.to_dict()
        assert d["efficiency"]["t_execute"] == 3.5
        assert d["quality"]["first_pass_rate"] == 85.0
        assert d["self_healing"]["fix_by_strategy"]["update_locator"] == 80.0


# ============================================================
# KPICalculator — 效率指标
# ============================================================


class TestEfficiencyCalculation:
    """KPICalculator — 效率指标计算"""

    def test_t_design_从design_span提取(self, sample_spans, sample_token_records):
        """t_design 应从名称包含 'design' 的 span 中提取持续时间。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        assert kpi.efficiency.t_design == pytest.approx(10.0, abs=0.1)

    def test_t_execute_计算平均值(self, sample_spans, sample_token_records):
        """t_execute 应为所有 execute span 的平均持续时间。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        # 3 条用例：2s + 3s + 5s = 10s, 平均 ≈ 3.33s
        expected_avg = (2.0 + 3.0 + 5.0) / 3
        assert kpi.efficiency.t_execute == pytest.approx(expected_avg, abs=0.1)

    def test_t_fix_从fix_span提取(self, sample_spans, sample_token_records):
        """t_fix 应从 fix 阶段 span 中提取总持续时间。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        # fix_locator(5s) + fix_wait(5s) = 10s
        assert kpi.efficiency.t_fix == pytest.approx(10.0, abs=0.1)

    def test_token_per_case(self, sample_spans, sample_token_records):
        """token_per_case 应为总 token / 用例数。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        total_tokens = 2000 + 1500 + 800 + 500
        case_count = 3
        assert kpi.efficiency.token_per_case == pytest.approx(
            total_tokens / case_count, abs=1.0
        )

    def test_cost_per_case(self, sample_spans, sample_token_records):
        """cost_per_case 应为总费用 / 用例数。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        total_cost = 0.02 + 0.015 + 0.008 + 0.005
        case_count = 3
        assert kpi.efficiency.cost_per_case == pytest.approx(
            total_cost / case_count, abs=0.001
        )

    def test_空数据返回零(self):
        """无 span 和 token 数据时所有效率指标应为 0。"""
        calc = KPICalculator([], [])
        kpi = calc.calculate_from_run()
        assert kpi.efficiency.t_design == 0.0
        assert kpi.efficiency.t_execute == 0.0
        assert kpi.efficiency.cost_per_case == 0.0


# ============================================================
# KPICalculator — 质量指标
# ============================================================


class TestQualityCalculation:
    """KPICalculator — 质量指标计算"""

    def test_first_pass_rate(self, sample_spans, sample_token_records):
        """first_pass_rate 应为首次通过（status=ok, retry=0）的比例。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        # 3 条用例：case_1 通过(ok,retry=0), case_2 失败(error), case_3 通过(ok,retry=0)
        assert kpi.quality.first_pass_rate == pytest.approx(2 / 3 * 100, abs=0.1)

    def test_valid_assertion_pct(self, sample_spans, sample_token_records):
        """valid_assertion_pct 应为有效断言 / 总断言。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        # total: 5+3+4=12, valid: 5+2+4=11
        assert kpi.quality.valid_assertion_pct == pytest.approx(11 / 12 * 100, abs=0.1)

    def test_xml_validity_rate(self, sample_spans, sample_token_records):
        """xml_validity_rate 应统计含 xml_valid 属性的 span。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        # 只有 case_3 有 xml_valid=True，共 1 个，全部为 True
        assert kpi.quality.xml_validity_rate == pytest.approx(100.0, abs=0.1)

    def test_flakiness_rate_默认值(self, sample_spans, sample_token_records):
        """未设置 flakiness_rate 属性时应返回 0。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        assert kpi.quality.flakiness_rate == 0.0

    def test_flakiness_rate_从属性读取(self):
        """span attributes 中有 flakiness_rate 时应正确读取。"""
        spans = [
            _make_span("summary", 0, 1000000000, attributes={"flakiness_rate": 12.5}),
        ]
        calc = KPICalculator(spans, [])
        kpi = calc.calculate_from_run()
        assert kpi.quality.flakiness_rate == 12.5


# ============================================================
# KPICalculator — 自愈指标
# ============================================================


class TestSelfHealingCalculation:
    """KPICalculator — 自愈指标计算"""

    def test_fix_success_pct(self, sample_spans, sample_token_records):
        """fix_success_pct 应为成功修复 / 总修复尝试。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        # 2 次修复：1 成功 1 失败 → 50%
        assert kpi.self_healing.fix_success_pct == pytest.approx(50.0, abs=0.1)

    def test_mttr_auto(self, sample_spans, sample_token_records):
        """mttr_auto 应为成功修复的平均耗时。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        # 只有 fix_locator 成功（5 秒）
        assert kpi.self_healing.mttr_auto == pytest.approx(5.0, abs=0.1)

    def test_fix_by_strategy(self, sample_spans, sample_token_records):
        """fix_by_strategy 应按策略分组统计成功率。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        assert "update_locator" in kpi.self_healing.fix_by_strategy
        assert kpi.self_healing.fix_by_strategy["update_locator"] == pytest.approx(
            100.0, abs=0.1
        )
        assert kpi.self_healing.fix_by_strategy["add_wait"] == pytest.approx(
            0.0, abs=0.1
        )

    def test_无fix数据时自愈指标为零(self):
        """无 fix span 时所有自愈指标应为 0。"""
        spans = [
            _make_span("execute_case_1", 0, 1000000000, attributes={"retry_count": 0}),
        ]
        calc = KPICalculator(spans, [])
        kpi = calc.calculate_from_run()
        assert kpi.self_healing.fix_success_pct == 0.0
        assert kpi.self_healing.mttr_auto == 0.0
        assert kpi.self_healing.fix_by_strategy == {}


# ============================================================
# KPICalculator — calculate_from_run 参数覆盖
# ============================================================


class TestCalculateFromRun:
    """KPICalculator.calculate_from_run — 参数覆盖行为"""

    def test_构造时传参(self, sample_spans, sample_token_records):
        """构造时传入数据，calculate_from_run 无参调用也能计算。"""
        calc = KPICalculator(sample_spans, sample_token_records)
        kpi = calc.calculate_from_run()
        assert kpi.efficiency.t_design > 0

    def test_calculate时覆盖参数(self, sample_spans, sample_token_records):
        """calculate_from_run 传入的参数应覆盖构造时的数据。"""
        calc = KPICalculator([], [])  # 构造时无数据
        kpi = calc.calculate_from_run(
            spans=sample_spans,
            token_records=sample_token_records,
        )
        assert kpi.efficiency.t_design > 0


# ============================================================
# KPICalculator.compare — KPI 对比
# ============================================================


class TestKPICompare:
    """KPICalculator.compare — KPI 差异对比"""

    def test_全部改善(self):
        """所有指标都改善时，summary 中 improved 数量应正确。"""
        baseline = KPIMetrics(
            efficiency=EfficiencyMetrics(t_design=20.0, t_execute=5.0, cost_per_case=0.1),
            quality=QualityMetrics(first_pass_rate=50.0),
            self_healing=SelfHealingMetrics(fix_success_pct=30.0),
        )
        current = KPIMetrics(
            efficiency=EfficiencyMetrics(t_design=10.0, t_execute=3.0, cost_per_case=0.05),
            quality=QualityMetrics(first_pass_rate=80.0),
            self_healing=SelfHealingMetrics(fix_success_pct=70.0),
        )
        diff = KPICalculator.compare(baseline, current)
        assert diff.summary["improved"] >= 5
        assert diff.summary["regressed"] == 0

    def test_全部退步(self):
        """所有指标都退步时，summary 中 regressed 数量应正确。"""
        baseline = KPIMetrics(
            efficiency=EfficiencyMetrics(t_design=10.0, t_execute=3.0),
            quality=QualityMetrics(first_pass_rate=90.0),
        )
        current = KPIMetrics(
            efficiency=EfficiencyMetrics(t_design=20.0, t_execute=6.0),
            quality=QualityMetrics(first_pass_rate=50.0),
        )
        diff = KPICalculator.compare(baseline, current)
        assert diff.summary["regressed"] >= 3

    def test_完全相同(self):
        """两次运行指标完全相同时应全部为 unchanged。"""
        kpi = KPIMetrics(
            efficiency=EfficiencyMetrics(t_design=10.0),
            quality=QualityMetrics(first_pass_rate=80.0),
        )
        diff = KPICalculator.compare(kpi, kpi)
        # 所有条目的 delta 应为 0
        for entry in diff.entries:
            assert entry.delta == pytest.approx(0.0, abs=1e-9)
        assert diff.summary["improved"] == 0
        assert diff.summary["regressed"] == 0

    def test_diff_entry_内容正确(self):
        """KPIDiffEntry 应包含正确的 metric/baseline/current/delta/improved。"""
        baseline = KPIMetrics(
            efficiency=EfficiencyMetrics(t_design=20.0),
        )
        current = KPIMetrics(
            efficiency=EfficiencyMetrics(t_design=15.0),
        )
        diff = KPICalculator.compare(baseline, current)
        t_design_entry = next(
            (e for e in diff.entries if e.metric == "efficiency.t_design"), None
        )
        assert t_design_entry is not None
        assert t_design_entry.baseline == 20.0
        assert t_design_entry.current == 15.0
        assert t_design_entry.delta == pytest.approx(-5.0)
        assert t_design_entry.improved is True  # 越低越好

    def test_diff_to_dict_可序列化(self):
        """KPIDiff.to_dict() 输出应为可 JSON 序列化的字典。"""
        diff = KPICalculator.compare(KPIMetrics(), KPIMetrics())
        d = diff.to_dict()
        assert "entries" in d
        assert "summary" in d
        # 确保可以 JSON 序列化
        text = json.dumps(d)
        assert len(text) > 0
