"""Agent vs Generic Agent 对比实验框架。

提供标准化的实验结构，用于量化对比 rodski-agent 与通用 Agent（如直接使用
Claude 编写 Playwright 代码）在多个维度上的表现差异。

通用 Agent 的指标需手动录入（无法自动化运行通用 Agent）。
rodski-agent 的指标通过 KPICalculator 自动采集。

仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# 使用相对导入从 rodski-agent 的 common 模块获取 KPI 能力
# 由于 benchmark/ 不在 src/ 包内，使用绝对路径导入
try:
    from rodski_agent.common.kpi import KPICalculator, KPIMetrics
except ImportError:
    # 允许直接运行或测试时的 fallback
    KPICalculator = None  # type: ignore[assignment, misc]
    KPIMetrics = None  # type: ignore[assignment, misc]


# ============================================================
# 对比维度
# ============================================================


class ComparisonDimension:
    """对比维度常量。

    每个维度定义了 rodski-agent 和 generic agent 各自的测量方式。
    """

    GENERATION_SPEED = "generation_speed"
    FIRST_SUCCESS_RATE = "first_success_rate"
    MAINTENANCE_COST = "maintenance_cost"
    TOKEN_CONSUMPTION = "token_consumption"
    SELF_HEALING = "self_healing"
    CROSS_PLATFORM = "cross_platform"

    ALL = [
        GENERATION_SPEED,
        FIRST_SUCCESS_RATE,
        MAINTENANCE_COST,
        TOKEN_CONSUMPTION,
        SELF_HEALING,
        CROSS_PLATFORM,
    ]

    # 维度说明表
    DESCRIPTIONS: Dict[str, Dict[str, str]] = {
        GENERATION_SPEED: {
            "rodski_agent": "T_design (requirements -> XML)",
            "generic_agent": "T_codegen (requirements -> code)",
            "unit": "seconds",
        },
        FIRST_SUCCESS_RATE: {
            "rodski_agent": "XML valid + execution pass",
            "generic_agent": "Code compiles + runs",
            "unit": "percent",
        },
        MAINTENANCE_COST: {
            "rodski_agent": "Lines changed after UI change",
            "generic_agent": "Lines changed after UI change",
            "unit": "lines",
        },
        TOKEN_CONSUMPTION: {
            "rodski_agent": "Token tracker total",
            "generic_agent": "Token tracker total",
            "unit": "tokens",
        },
        SELF_HEALING: {
            "rodski_agent": "Fix_success_pct",
            "generic_agent": "None (manual)",
            "unit": "percent",
        },
        CROSS_PLATFORM: {
            "rodski_agent": "Lines to switch driver_type",
            "generic_agent": "Lines to rewrite code",
            "unit": "lines",
        },
    }


# ============================================================
# 数据模型
# ============================================================


@dataclass
class ExperimentConfig:
    """实验配置。

    Attributes
    ----------
    suite_dir : str
        测试套件目录路径。
    models : list[str]
        参与对比的 LLM 模型列表。
    repetitions : int
        每个场景的重复次数。
    dimensions : list[str]
        要评估的维度列表。默认全部。
    extra : dict
        额外配置。
    """

    suite_dir: str = ""
    models: List[str] = field(default_factory=lambda: ["claude-sonnet-4-20250514"])
    repetitions: int = 3
    dimensions: List[str] = field(
        default_factory=lambda: list(ComparisonDimension.ALL)
    )
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DimensionResult:
    """单个维度的对比结果。

    Attributes
    ----------
    dimension : str
        维度名称。
    rodski_value : float
        rodski-agent 的测量值。
    generic_value : float
        generic agent 的测量值。
    unit : str
        单位。
    rodski_better : bool | None
        rodski-agent 是否更优。None 表示无法判断。
    notes : str
        备注。
    """

    dimension: str = ""
    rodski_value: float = 0.0
    generic_value: float = 0.0
    unit: str = ""
    rodski_better: Optional[bool] = None
    notes: str = ""


@dataclass
class ComparisonResult:
    """完整的对比实验结果。

    Attributes
    ----------
    experiment_id : str
        实验唯一标识。
    timestamp : str
        实验时间（ISO 格式 UTC）。
    config : dict
        实验配置快照。
    dimensions : list[DimensionResult]
        各维度对比结果。
    rodski_kpi : dict | None
        rodski-agent 的完整 KPI 数据。
    generic_metrics : dict
        generic agent 的手动录入数据。
    summary : str
        人类可读的总结。
    """

    experiment_id: str = ""
    timestamp: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    dimensions: List[DimensionResult] = field(default_factory=list)
    rodski_kpi: Optional[Dict[str, Any]] = None
    generic_metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 化的字典。"""
        return {
            "experiment_id": self.experiment_id,
            "timestamp": self.timestamp,
            "config": self.config,
            "dimensions": [asdict(d) for d in self.dimensions],
            "rodski_kpi": self.rodski_kpi,
            "generic_metrics": self.generic_metrics,
            "summary": self.summary,
        }

    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ============================================================
# 维度比较逻辑
# ============================================================

# True = 越低越好
_LOWER_IS_BETTER_DIMS: Dict[str, bool] = {
    ComparisonDimension.GENERATION_SPEED: True,
    ComparisonDimension.FIRST_SUCCESS_RATE: False,
    ComparisonDimension.MAINTENANCE_COST: True,
    ComparisonDimension.TOKEN_CONSUMPTION: True,
    ComparisonDimension.SELF_HEALING: False,
    ComparisonDimension.CROSS_PLATFORM: True,
}


# ============================================================
# ComparisonExperiment
# ============================================================


class ComparisonExperiment:
    """Agent 对比实验。

    Parameters
    ----------
    config : ExperimentConfig
        实验配置。
    """

    def __init__(self, config: Optional[ExperimentConfig] = None):
        self.config = config or ExperimentConfig()
        self._rodski_kpi: Optional[KPIMetrics] = None
        self._generic_metrics: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # 数据采集
    # ------------------------------------------------------------------

    def collect_rodski_metrics(
        self,
        spans: Optional[List[Dict[str, Any]]] = None,
        token_records: Optional[List[Dict[str, Any]]] = None,
        *,
        kpi: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """从 trace/token 数据采集 rodski-agent 指标。

        可直接传入已计算好的 KPIMetrics（通过 ``kpi`` 参数），
        或传入 spans + token_records 由内部计算。

        Parameters
        ----------
        spans : list[dict] | None
            Span 数据。
        token_records : list[dict] | None
            Token 记录数据。
        kpi : KPIMetrics | None
            直接传入已计算的 KPI。

        Returns
        -------
        dict
            rodski-agent KPI 字典。
        """
        if kpi is not None:
            self._rodski_kpi = kpi
        elif KPICalculator is not None:
            calculator = KPICalculator(
                spans=spans or [],
                token_records=token_records or [],
            )
            self._rodski_kpi = calculator.calculate_from_run()
        else:
            # KPI 模块不可用时返回空
            return {}

        return self._rodski_kpi.to_dict()

    def collect_generic_metrics(
        self,
        metrics: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """录入 generic agent 的手动测量数据。

        Generic agent 的指标需人工采集，此方法接受手动录入值。

        Parameters
        ----------
        metrics : dict | None
            维度名 → 测量值的映射。键应使用 ComparisonDimension 常量。
            示例::

                {
                    "generation_speed": 45.0,
                    "first_success_rate": 60.0,
                    "maintenance_cost": 120,
                    "token_consumption": 15000,
                    "self_healing": 0.0,
                    "cross_platform": 500,
                }

        Returns
        -------
        dict
            当前的 generic metrics。
        """
        if metrics is not None:
            self._generic_metrics.update(metrics)
        return dict(self._generic_metrics)

    # ------------------------------------------------------------------
    # 生成报告
    # ------------------------------------------------------------------

    def generate_report(self) -> ComparisonResult:
        """基于采集的数据生成对比结果。

        Returns
        -------
        ComparisonResult
        """
        import uuid

        rodski_kpi_dict = self._rodski_kpi.to_dict() if self._rodski_kpi else {}
        dimension_results = self._build_dimension_results(rodski_kpi_dict)
        summary = self._build_summary(dimension_results)

        return ComparisonResult(
            experiment_id=uuid.uuid4().hex[:12],
            timestamp=datetime.now(timezone.utc).isoformat(),
            config=asdict(self.config),
            dimensions=dimension_results,
            rodski_kpi=rodski_kpi_dict,
            generic_metrics=dict(self._generic_metrics),
            summary=summary,
        )

    def generate_markdown_report(self) -> str:
        """生成 Markdown 格式的对比报告。

        Returns
        -------
        str
            Markdown 文本。
        """
        result = self.generate_report()
        lines: List[str] = []

        lines.append("# Agent Comparison Report")
        lines.append("")
        lines.append(f"**Experiment ID:** {result.experiment_id}")
        lines.append(f"**Timestamp:** {result.timestamp}")
        lines.append(f"**Suite:** {self.config.suite_dir}")
        lines.append(f"**Repetitions:** {self.config.repetitions}")
        lines.append("")

        # 对比表格
        lines.append("## Comparison Table")
        lines.append("")
        lines.append(
            "| Dimension | rodski-agent | Generic Agent | Unit | Winner |"
        )
        lines.append(
            "|-----------|-------------|---------------|------|--------|"
        )

        for dim in result.dimensions:
            winner = "rodski-agent" if dim.rodski_better else "Generic"
            if dim.rodski_better is None:
                winner = "N/A"
            lines.append(
                f"| {dim.dimension} | {dim.rodski_value:.2f} | "
                f"{dim.generic_value:.2f} | {dim.unit} | {winner} |"
            )

        lines.append("")

        # 总结
        lines.append("## Summary")
        lines.append("")
        lines.append(result.summary)
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _build_dimension_results(
        self, rodski_kpi_dict: Dict[str, Any]
    ) -> List[DimensionResult]:
        """根据采集数据构建各维度对比结果。"""
        results: List[DimensionResult] = []

        # 从 KPI 数据提取对应维度值
        rodski_values = self._extract_rodski_dimension_values(rodski_kpi_dict)

        for dim in self.config.dimensions:
            desc = ComparisonDimension.DESCRIPTIONS.get(dim, {})
            unit = desc.get("unit", "")

            r_val = rodski_values.get(dim, 0.0)
            g_val = self._generic_metrics.get(dim, 0.0)

            lower = _LOWER_IS_BETTER_DIMS.get(dim, True)
            if abs(r_val) < 1e-9 and abs(g_val) < 1e-9:
                better = None
            elif lower:
                better = r_val < g_val
            else:
                better = r_val > g_val

            results.append(DimensionResult(
                dimension=dim,
                rodski_value=r_val,
                generic_value=g_val,
                unit=unit,
                rodski_better=better,
            ))

        return results

    @staticmethod
    def _extract_rodski_dimension_values(
        kpi_dict: Dict[str, Any],
    ) -> Dict[str, float]:
        """从 KPI 字典中提取各对比维度的值。"""
        eff = kpi_dict.get("efficiency", {})
        qual = kpi_dict.get("quality", {})
        sh = kpi_dict.get("self_healing", {})

        return {
            ComparisonDimension.GENERATION_SPEED: float(
                eff.get("t_design", 0.0)
            ),
            ComparisonDimension.FIRST_SUCCESS_RATE: float(
                qual.get("first_pass_rate", 0.0)
            ),
            ComparisonDimension.MAINTENANCE_COST: 0.0,  # 需外部提供
            ComparisonDimension.TOKEN_CONSUMPTION: float(
                eff.get("token_per_case", 0.0)
            ),
            ComparisonDimension.SELF_HEALING: float(
                sh.get("fix_success_pct", 0.0)
            ),
            ComparisonDimension.CROSS_PLATFORM: 0.0,  # 需外部提供
        }

    @staticmethod
    def _build_summary(dimensions: List[DimensionResult]) -> str:
        """从维度结果构建人类可读的总结文本。"""
        rodski_wins = sum(
            1 for d in dimensions if d.rodski_better is True
        )
        generic_wins = sum(
            1 for d in dimensions if d.rodski_better is False
        )
        ties = sum(
            1 for d in dimensions if d.rodski_better is None
        )
        total = len(dimensions)

        parts: List[str] = []
        parts.append(
            f"Compared {total} dimensions: "
            f"rodski-agent wins {rodski_wins}, "
            f"generic wins {generic_wins}, "
            f"tie/N/A {ties}."
        )

        if rodski_wins > generic_wins:
            parts.append("Overall: rodski-agent demonstrates clear advantages.")
        elif generic_wins > rodski_wins:
            parts.append("Overall: generic agent performs better in more dimensions.")
        else:
            parts.append("Overall: results are mixed, no clear winner.")

        return " ".join(parts)
