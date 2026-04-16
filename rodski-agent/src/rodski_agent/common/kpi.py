"""Agent KPI 评估框架 — 从 trace 和 token 数据计算效率/质量/自愈指标。

从 rodski observability Span 和 LLM TokenTracker 记录中提取关键绩效指标，
用于量化评估 Agent 的执行效率、生成质量与自愈能力。

仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================
# KPI 数据模型
# ============================================================


@dataclass
class EfficiencyMetrics:
    """效率指标。

    Attributes
    ----------
    t_design : float
        从需求到可执行用例的时间（秒）。
    t_execute : float
        平均每条用例的执行时间（秒）。
    t_fix : float
        从失败到自动修复成功的时间（秒）。
    token_per_case : float
        每条用例的总 token 消耗。
    token_per_fix : float
        每次修复的 token 消耗。
    cost_per_case : float
        每条用例的 LLM 费用（USD）。
    """

    t_design: float = 0.0
    t_execute: float = 0.0
    t_fix: float = 0.0
    token_per_case: float = 0.0
    token_per_fix: float = 0.0
    cost_per_case: float = 0.0


@dataclass
class QualityMetrics:
    """质量指标。

    Attributes
    ----------
    first_pass_rate : float
        首次通过率（百分比，0-100）。
    valid_assertion_pct : float
        有效断言占比（百分比，0-100）。
    xml_validity_rate : float
        生成的 XML 首次通过 XSD 校验的比率（百分比，0-100）。
    flakiness_rate : float
        多次运行的不一致率（百分比，0-100）。
    """

    first_pass_rate: float = 0.0
    valid_assertion_pct: float = 0.0
    xml_validity_rate: float = 0.0
    flakiness_rate: float = 0.0


@dataclass
class SelfHealingMetrics:
    """自愈指标。

    Attributes
    ----------
    mttr_auto : float
        自动修复平均恢复时间（秒）。
    fix_success_pct : float
        自动修复成功率（百分比，0-100）。
    fix_by_strategy : dict
        按修复策略分组的成功率 ``{strategy_name: success_pct}``。
    """

    mttr_auto: float = 0.0
    fix_success_pct: float = 0.0
    fix_by_strategy: Dict[str, float] = field(default_factory=dict)


@dataclass
class KPIMetrics:
    """完整的 KPI 指标集合。

    聚合效率、质量和自愈三类指标。
    """

    efficiency: EfficiencyMetrics = field(default_factory=EfficiencyMetrics)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    self_healing: SelfHealingMetrics = field(default_factory=SelfHealingMetrics)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可被 ``json.dumps`` 处理的字典。"""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ============================================================
# KPI Diff — 两次运行的差异
# ============================================================


@dataclass
class KPIDiffEntry:
    """单个指标的基线 vs 当前 对比。"""

    metric: str
    baseline: float
    current: float
    delta: float
    improved: bool


@dataclass
class KPIDiff:
    """两次 KPI 指标对比结果。

    Attributes
    ----------
    entries : list[KPIDiffEntry]
        逐个指标的对比条目。
    summary : dict
        汇总信息（改善数、退步数、持平数）。
    """

    entries: List[KPIDiffEntry] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entries": [asdict(e) for e in self.entries],
            "summary": self.summary,
        }


# ============================================================
# 指标改善方向定义
# ============================================================

# True = 越低越好（如时间、token、费用、flakiness）
# False = 越高越好（如通过率、有效断言率）
_LOWER_IS_BETTER: Dict[str, bool] = {
    "efficiency.t_design": True,
    "efficiency.t_execute": True,
    "efficiency.t_fix": True,
    "efficiency.token_per_case": True,
    "efficiency.token_per_fix": True,
    "efficiency.cost_per_case": True,
    "quality.first_pass_rate": False,
    "quality.valid_assertion_pct": False,
    "quality.xml_validity_rate": False,
    "quality.flakiness_rate": True,
    "self_healing.mttr_auto": True,
    "self_healing.fix_success_pct": False,
}


# ============================================================
# KPICalculator
# ============================================================


class KPICalculator:
    """从 trace span 和 token 记录计算 KPI 指标。

    Parameters
    ----------
    spans : list[dict]
        Span.to_dict() 输出的列表（或等价的字典列表）。
    token_records : list[dict]
        LLMCallRecord.to_dict() 输出的列表（或等价的字典列表）。
    """

    def __init__(
        self,
        spans: Optional[List[Dict[str, Any]]] = None,
        token_records: Optional[List[Dict[str, Any]]] = None,
    ):
        self._spans = spans or []
        self._token_records = token_records or []

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def calculate_from_run(
        self,
        spans: Optional[List[Dict[str, Any]]] = None,
        token_records: Optional[List[Dict[str, Any]]] = None,
    ) -> KPIMetrics:
        """从单次运行数据计算完整 KPI。

        Parameters
        ----------
        spans : list[dict] | None
            若提供则覆盖构造时传入的 spans。
        token_records : list[dict] | None
            若提供则覆盖构造时传入的 token_records。

        Returns
        -------
        KPIMetrics
        """
        if spans is not None:
            self._spans = spans
        if token_records is not None:
            self._token_records = token_records

        efficiency = self._calc_efficiency()
        quality = self._calc_quality()
        self_healing = self._calc_self_healing()

        return KPIMetrics(
            efficiency=efficiency,
            quality=quality,
            self_healing=self_healing,
        )

    # ------------------------------------------------------------------
    # 效率指标
    # ------------------------------------------------------------------

    def _calc_efficiency(self) -> EfficiencyMetrics:
        t_design = self._extract_phase_duration("design")
        t_execute = self._calc_avg_execution_time()
        t_fix = self._extract_phase_duration("fix")

        case_count = self._count_cases()
        fix_count = self._count_by_purpose("fix") or self._count_fix_spans()

        total_tokens = sum(r.get("total_tokens", 0) for r in self._token_records)
        total_cost = sum(r.get("cost_usd", 0.0) for r in self._token_records)

        fix_tokens = sum(
            r.get("total_tokens", 0)
            for r in self._token_records
            if r.get("purpose", "") in ("fix", "repair", "diagnosis")
        )

        token_per_case = total_tokens / case_count if case_count > 0 else 0.0
        token_per_fix = fix_tokens / fix_count if fix_count > 0 else 0.0
        cost_per_case = total_cost / case_count if case_count > 0 else 0.0

        return EfficiencyMetrics(
            t_design=t_design,
            t_execute=t_execute,
            t_fix=t_fix,
            token_per_case=token_per_case,
            token_per_fix=token_per_fix,
            cost_per_case=cost_per_case,
        )

    def _extract_phase_duration(self, phase_name: str) -> float:
        """从 spans 中提取某阶段的总耗时。"""
        total = 0.0
        for span in self._spans:
            name = span.get("name", "")
            if phase_name in name.lower():
                start = span.get("startTimeUnixNano", 0)
                end = span.get("endTimeUnixNano")
                if start and end:
                    total += (end - start) / 1e9
        return total

    def _calc_avg_execution_time(self) -> float:
        """计算平均用例执行时间。"""
        durations: List[float] = []
        for span in self._spans:
            name = span.get("name", "")
            if "execute" in name.lower() or "run_case" in name.lower():
                start = span.get("startTimeUnixNano", 0)
                end = span.get("endTimeUnixNano")
                if start and end:
                    durations.append((end - start) / 1e9)
        return sum(durations) / len(durations) if durations else 0.0

    def _count_cases(self) -> int:
        """统计用例数量（execute/run_case spans 数）。"""
        count = 0
        for span in self._spans:
            name = span.get("name", "")
            if "execute" in name.lower() or "run_case" in name.lower():
                count += 1
        return max(count, 1)  # 至少 1 避免除零

    def _count_by_purpose(self, purpose: str) -> int:
        """按 purpose 统计 token 记录数。"""
        return sum(
            1
            for r in self._token_records
            if r.get("purpose", "") == purpose
        )

    def _count_fix_spans(self) -> int:
        """统计 fix 相关 spans 数。"""
        count = 0
        for span in self._spans:
            name = span.get("name", "")
            if "fix" in name.lower() or "repair" in name.lower():
                count += 1
        return count

    # ------------------------------------------------------------------
    # 质量指标
    # ------------------------------------------------------------------

    def _calc_quality(self) -> QualityMetrics:
        first_pass_rate = self._calc_first_pass_rate()
        valid_assertion_pct = self._calc_valid_assertion_pct()
        xml_validity_rate = self._calc_xml_validity_rate()
        flakiness_rate = self._calc_flakiness_rate()

        return QualityMetrics(
            first_pass_rate=first_pass_rate,
            valid_assertion_pct=valid_assertion_pct,
            xml_validity_rate=xml_validity_rate,
            flakiness_rate=flakiness_rate,
        )

    def _calc_first_pass_rate(self) -> float:
        """首次通过率。从 span attributes 中读取。"""
        total = 0
        passed = 0
        for span in self._spans:
            name = span.get("name", "")
            if "execute" in name.lower() or "run_case" in name.lower():
                total += 1
                attrs = span.get("attributes", {})
                status = span.get("status", "")
                retry = attrs.get("retry_count", 0)
                if status == "ok" and retry == 0:
                    passed += 1
        return (passed / total * 100) if total > 0 else 0.0

    def _calc_valid_assertion_pct(self) -> float:
        """有效断言比例。从 span attributes 中读取。"""
        total = 0
        valid = 0
        for span in self._spans:
            attrs = span.get("attributes", {})
            t_assertions = attrs.get("total_assertions", 0)
            v_assertions = attrs.get("valid_assertions", 0)
            total += t_assertions
            valid += v_assertions
        return (valid / total * 100) if total > 0 else 0.0

    def _calc_xml_validity_rate(self) -> float:
        """XML 首次校验通过率。"""
        total = 0
        valid = 0
        for span in self._spans:
            attrs = span.get("attributes", {})
            if "xml_valid" in attrs:
                total += 1
                if attrs["xml_valid"]:
                    valid += 1
        return (valid / total * 100) if total > 0 else 0.0

    def _calc_flakiness_rate(self) -> float:
        """多次运行不一致率。"""
        for span in self._spans:
            attrs = span.get("attributes", {})
            if "flakiness_rate" in attrs:
                return float(attrs["flakiness_rate"])
        return 0.0

    # ------------------------------------------------------------------
    # 自愈指标
    # ------------------------------------------------------------------

    def _calc_self_healing(self) -> SelfHealingMetrics:
        mttr_auto = self._calc_mttr_auto()
        fix_success_pct = self._calc_fix_success_pct()
        fix_by_strategy = self._calc_fix_by_strategy()

        return SelfHealingMetrics(
            mttr_auto=mttr_auto,
            fix_success_pct=fix_success_pct,
            fix_by_strategy=fix_by_strategy,
        )

    def _calc_mttr_auto(self) -> float:
        """自动修复平均恢复时间。"""
        durations: List[float] = []
        for span in self._spans:
            name = span.get("name", "")
            if "fix" in name.lower() or "repair" in name.lower():
                start = span.get("startTimeUnixNano", 0)
                end = span.get("endTimeUnixNano")
                attrs = span.get("attributes", {})
                if start and end and attrs.get("fix_success", False):
                    durations.append((end - start) / 1e9)
        return sum(durations) / len(durations) if durations else 0.0

    def _calc_fix_success_pct(self) -> float:
        """自动修复成功率。"""
        total = 0
        success = 0
        for span in self._spans:
            name = span.get("name", "")
            if "fix" in name.lower() or "repair" in name.lower():
                total += 1
                attrs = span.get("attributes", {})
                if attrs.get("fix_success", False):
                    success += 1
        return (success / total * 100) if total > 0 else 0.0

    def _calc_fix_by_strategy(self) -> Dict[str, float]:
        """按策略分组的修复成功率。"""
        strategy_stats: Dict[str, Dict[str, int]] = {}
        for span in self._spans:
            name = span.get("name", "")
            if "fix" in name.lower() or "repair" in name.lower():
                attrs = span.get("attributes", {})
                strategy = attrs.get("fix_strategy", "unknown")
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {"total": 0, "success": 0}
                strategy_stats[strategy]["total"] += 1
                if attrs.get("fix_success", False):
                    strategy_stats[strategy]["success"] += 1

        result: Dict[str, float] = {}
        for strategy, stats in strategy_stats.items():
            total = stats["total"]
            result[strategy] = (stats["success"] / total * 100) if total > 0 else 0.0
        return result

    # ------------------------------------------------------------------
    # 对比
    # ------------------------------------------------------------------

    @staticmethod
    def compare(baseline: KPIMetrics, current: KPIMetrics) -> KPIDiff:
        """对比两次 KPI 结果，返回差异。

        Parameters
        ----------
        baseline : KPIMetrics
            基线指标。
        current : KPIMetrics
            当前指标。

        Returns
        -------
        KPIDiff
            包含每个指标的 delta 与改善/退步判断。
        """
        baseline_dict = baseline.to_dict()
        current_dict = current.to_dict()

        entries: List[KPIDiffEntry] = []
        improved_count = 0
        regressed_count = 0
        unchanged_count = 0

        for category in ("efficiency", "quality", "self_healing"):
            b_cat = baseline_dict.get(category, {})
            c_cat = current_dict.get(category, {})
            for key, b_val in b_cat.items():
                if key == "fix_by_strategy":
                    continue  # 跳过字典类型的指标
                c_val = c_cat.get(key, 0.0)
                if not isinstance(b_val, (int, float)) or not isinstance(c_val, (int, float)):
                    continue

                delta = c_val - b_val
                metric_key = f"{category}.{key}"
                lower_is_better = _LOWER_IS_BETTER.get(metric_key, True)

                if abs(delta) < 1e-9:
                    is_improved = False
                    unchanged_count += 1
                elif lower_is_better:
                    is_improved = delta < 0
                    if is_improved:
                        improved_count += 1
                    else:
                        regressed_count += 1
                else:
                    is_improved = delta > 0
                    if is_improved:
                        improved_count += 1
                    else:
                        regressed_count += 1

                entries.append(KPIDiffEntry(
                    metric=metric_key,
                    baseline=float(b_val),
                    current=float(c_val),
                    delta=float(delta),
                    improved=is_improved,
                ))

        return KPIDiff(
            entries=entries,
            summary={
                "improved": improved_count,
                "regressed": regressed_count,
                "unchanged": unchanged_count,
            },
        )
