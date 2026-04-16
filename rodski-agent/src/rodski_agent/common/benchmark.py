"""Benchmark 测试运行器 — 运行基准测试套件并管理历史结果。

BenchmarkRunner 负责：
  1. 执行基准测试（实际执行由 rodski 完成，此处侧重 KPI 计算与结果管理）
  2. 将结果持久化为 JSON
  3. 对比两次运行的 KPI 差异

仅依赖 Python 标准库。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .kpi import KPICalculator, KPIDiff, KPIMetrics


# ============================================================
# 数据模型
# ============================================================


@dataclass
class BenchmarkConfig:
    """基准测试配置。

    Attributes
    ----------
    suite_dir : str
        测试套件目录路径。
    repetitions : int
        每条用例的重复运行次数。
    tags : list[str]
        自定义标签（如 "nightly"、"smoke"）。
    extra : dict
        额外配置参数。
    """

    suite_dir: str = ""
    repetitions: int = 1
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """单次基准测试运行结果。

    Attributes
    ----------
    run_id : str
        唯一运行标识。
    suite_name : str
        测试套件名称。
    timestamp : str
        运行时间（ISO 格式 UTC）。
    config : dict
        运行配置快照。
    kpi : KPIMetrics
        计算得到的 KPI 指标。
    metadata : dict
        额外元信息。
    """

    run_id: str = ""
    suite_name: str = ""
    timestamp: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    kpi: KPIMetrics = field(default_factory=KPIMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 化的字典。"""
        return {
            "run_id": self.run_id,
            "suite_name": self.suite_name,
            "timestamp": self.timestamp,
            "config": self.config,
            "kpi": self.kpi.to_dict(),
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BenchmarkResult:
        """从字典反序列化。"""
        from .kpi import EfficiencyMetrics, QualityMetrics, SelfHealingMetrics

        kpi_data = data.get("kpi", {})
        eff = kpi_data.get("efficiency", {})
        qual = kpi_data.get("quality", {})
        sh = kpi_data.get("self_healing", {})

        kpi = KPIMetrics(
            efficiency=EfficiencyMetrics(**{
                k: v for k, v in eff.items()
                if k in EfficiencyMetrics.__dataclass_fields__
            }),
            quality=QualityMetrics(**{
                k: v for k, v in qual.items()
                if k in QualityMetrics.__dataclass_fields__
            }),
            self_healing=SelfHealingMetrics(**{
                k: v for k, v in sh.items()
                if k in SelfHealingMetrics.__dataclass_fields__
            }),
        )

        return cls(
            run_id=data.get("run_id", ""),
            suite_name=data.get("suite_name", ""),
            timestamp=data.get("timestamp", ""),
            config=data.get("config", {}),
            kpi=kpi,
            metadata=data.get("metadata", {}),
        )


# ============================================================
# BenchmarkRunner
# ============================================================


class BenchmarkRunner:
    """基准测试运行器。

    Parameters
    ----------
    results_dir : Path | None
        结果存储目录。默认为当前目录下的 ``benchmark_results/``。
    """

    DEFAULT_RESULTS_DIR = Path("benchmark_results")

    def __init__(self, results_dir: Optional[Path] = None):
        self.results_dir = results_dir or self.DEFAULT_RESULTS_DIR

    # ------------------------------------------------------------------
    # 运行
    # ------------------------------------------------------------------

    def run_benchmark(
        self,
        suite_dir: str,
        config: Optional[BenchmarkConfig] = None,
        *,
        executor: Optional[Callable] = None,
    ) -> BenchmarkResult:
        """运行基准测试并返回结果。

        实际测试执行由外部 ``executor`` 回调完成。``executor`` 需返回
        ``(spans, token_records)`` 二元组。如果未提供 ``executor``，
        则使用空数据（适合单元测试和 dry-run 场景）。

        Parameters
        ----------
        suite_dir : str
            测试套件目录路径。
        config : BenchmarkConfig | None
            运行配置，为 ``None`` 时使用默认配置。
        executor : callable | None
            执行回调 ``() -> (list[dict], list[dict])``，
            返回 (spans, token_records)。

        Returns
        -------
        BenchmarkResult
        """
        if config is None:
            config = BenchmarkConfig(suite_dir=suite_dir)

        run_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).isoformat()
        suite_name = Path(suite_dir).name or suite_dir

        # 执行测试
        spans: List[Dict[str, Any]] = []
        token_records: List[Dict[str, Any]] = []
        if executor is not None:
            spans, token_records = executor()

        # 计算 KPI
        calculator = KPICalculator(spans=spans, token_records=token_records)
        kpi = calculator.calculate_from_run()

        result = BenchmarkResult(
            run_id=run_id,
            suite_name=suite_name,
            timestamp=timestamp,
            config=asdict(config),
            kpi=kpi,
            metadata={
                "span_count": len(spans),
                "token_record_count": len(token_records),
            },
        )

        # 持久化
        self._save_result(result)

        return result

    # ------------------------------------------------------------------
    # 对比
    # ------------------------------------------------------------------

    @staticmethod
    def compare(run_a: BenchmarkResult, run_b: BenchmarkResult) -> Dict[str, Any]:
        """对比两次运行的 KPI。

        Parameters
        ----------
        run_a : BenchmarkResult
            基线运行。
        run_b : BenchmarkResult
            当前运行。

        Returns
        -------
        dict
            包含 baseline/current run_id、KPIDiff 及 summary。
        """
        diff = KPICalculator.compare(run_a.kpi, run_b.kpi)
        return {
            "baseline_run_id": run_a.run_id,
            "current_run_id": run_b.run_id,
            "baseline_suite": run_a.suite_name,
            "current_suite": run_b.suite_name,
            "diff": diff.to_dict(),
        }

    # ------------------------------------------------------------------
    # 历史管理
    # ------------------------------------------------------------------

    def _save_result(self, result: BenchmarkResult) -> Path:
        """将运行结果保存为 JSON 文件。

        文件名格式：``{suite_name}_{run_id}.json``。

        Returns
        -------
        Path
            保存的文件路径。
        """
        self.results_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{result.suite_name}_{result.run_id}.json"
        filepath = self.results_dir / filename
        filepath.write_text(result.to_json(), encoding="utf-8")
        return filepath

    def load_result(self, run_id: str) -> Optional[BenchmarkResult]:
        """按 run_id 加载结果。

        Parameters
        ----------
        run_id : str
            运行标识。

        Returns
        -------
        BenchmarkResult | None
            找到则返回结果，否则返回 ``None``。
        """
        if not self.results_dir.exists():
            return None

        for filepath in self.results_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                if data.get("run_id") == run_id:
                    return BenchmarkResult.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return None

    def list_results(self, suite_name: Optional[str] = None) -> List[BenchmarkResult]:
        """列出所有保存的运行结果。

        Parameters
        ----------
        suite_name : str | None
            按套件名过滤。为 ``None`` 时返回全部。

        Returns
        -------
        list[BenchmarkResult]
            按 timestamp 降序排列的结果列表。
        """
        results: List[BenchmarkResult] = []
        if not self.results_dir.exists():
            return results

        for filepath in self.results_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                result = BenchmarkResult.from_dict(data)
                if suite_name is None or result.suite_name == suite_name:
                    results.append(result)
            except (json.JSONDecodeError, KeyError):
                continue

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results

    def delete_result(self, run_id: str) -> bool:
        """删除指定运行结果文件。

        Returns
        -------
        bool
            是否成功删除。
        """
        if not self.results_dir.exists():
            return False

        for filepath in self.results_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                if data.get("run_id") == run_id:
                    filepath.unlink()
                    return True
            except (json.JSONDecodeError, KeyError):
                continue
        return False
