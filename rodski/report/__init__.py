"""报告模块 - 结构化报告数据模型、收集器、HTML 生成器、历史与趋势分析"""

from .data_model import (
    EnvironmentInfo,
    RunSummary,
    StepReport,
    PhaseReport,
    CaseReport,
    ReportData,
)
from .collector import ReportCollector
from .generator import ReportGenerator
from .history import HistoryManager
from .trend import TrendCalculator

__all__ = [
    "EnvironmentInfo",
    "RunSummary",
    "StepReport",
    "PhaseReport",
    "CaseReport",
    "ReportData",
    "ReportCollector",
    "ReportGenerator",
    "HistoryManager",
    "TrendCalculator",
]
