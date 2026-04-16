"""执行数据收集器 - 将 SKIExecutor 执行流程中的数据收集为结构化报告

ReportCollector 作为可选组件注入 SKIExecutor。
当 SKIExecutor 没有收集器时，行为完全不变。
"""

import logging
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from .data_model import (
    CaseReport,
    EnvironmentInfo,
    PhaseReport,
    ReportData,
    RunSummary,
    StepReport,
)

logger = logging.getLogger("rodski")


def _collect_environment() -> EnvironmentInfo:
    """采集当前运行环境信息"""
    try:
        from __init__ import __version__ as rodski_version
    except Exception:
        rodski_version = "unknown"

    return EnvironmentInfo(
        os_name=platform.system(),
        os_version=platform.version(),
        python_version=platform.python_version(),
        rodski_version=rodski_version,
    )


class ReportCollector:
    """执行数据收集器

    生命周期方法与 SKIExecutor 执行流程一一对应：

        start_run()
            start_case(case_info)
                start_phase(phase_name)
                    record_step(step_info)
                end_phase()
            end_case(status)
        end_run()
    """

    def __init__(self, output_dir: Optional[str] = None):
        """初始化收集器

        Args:
            output_dir: 报告输出目录（可选）。为 None 时 end_run 不会自动写入文件。
        """
        self._output_dir = output_dir
        self._report: Optional[ReportData] = None
        self._current_case: Optional[CaseReport] = None
        self._current_phase: Optional[PhaseReport] = None
        self._phase_start: float = 0.0
        self._case_start: float = 0.0

    @property
    def report(self) -> Optional[ReportData]:
        """获取当前报告数据"""
        return self._report

    # ------------------------------------------------------------------
    # Run 级别
    # ------------------------------------------------------------------

    def start_run(self, run_id: Optional[str] = None) -> ReportData:
        """开始新的执行，创建 ReportData 并记录开始时间和环境信息"""
        self._report = ReportData(
            run_id=run_id or uuid4().hex[:12],
            start_time=datetime.now(),
            environment=_collect_environment(),
        )
        logger.debug(f"[ReportCollector] 开始执行: run_id={self._report.run_id}")
        return self._report

    def end_run(self) -> Optional[ReportData]:
        """结束执行，计算汇总并可选地写入 report_data.json"""
        if self._report is None:
            return None

        self._report.end_time = datetime.now()
        self._report.duration = (
            self._report.end_time - self._report.start_time
        ).total_seconds()

        # 计算汇总
        self._report.summary = self._compute_summary()

        # 如果指定了输出目录，自动写入
        if self._output_dir:
            out_path = str(Path(self._output_dir) / "report_data.json")
            self._report.to_json(out_path)
            logger.info(f"[ReportCollector] 报告已写入: {out_path}")

        logger.debug(
            f"[ReportCollector] 执行结束: "
            f"total={self._report.summary.total}, "
            f"passed={self._report.summary.passed}, "
            f"failed={self._report.summary.failed}, "
            f"pass_rate={self._report.summary.pass_rate:.1f}%"
        )
        return self._report

    # ------------------------------------------------------------------
    # Case 级别
    # ------------------------------------------------------------------

    def start_case(self, case_info: Dict[str, Any]) -> CaseReport:
        """开始收集一个用例的数据

        Args:
            case_info: case_parser 解析出的 case dict，包含 case_id, title 等
        """
        self._case_start = time.time()
        self._current_case = CaseReport(
            case_id=case_info.get("case_id", ""),
            title=case_info.get("title", ""),
            description=case_info.get("description", ""),
            component_type=case_info.get("component_type", "界面"),
            tags=case_info.get("tags", []),
            priority=case_info.get("priority", ""),
        )
        logger.debug(f"[ReportCollector] 开始用例: {self._current_case.case_id}")
        return self._current_case

    def end_case(self, status: str) -> Optional[CaseReport]:
        """结束当前用例，记录最终状态和耗时"""
        if self._current_case is None:
            return None

        self._current_case.status = status
        self._current_case.duration = round(time.time() - self._case_start, 3)

        if self._report is not None:
            self._report.cases.append(self._current_case)

        logger.debug(
            f"[ReportCollector] 用例结束: {self._current_case.case_id} "
            f"status={status} duration={self._current_case.duration}s"
        )

        case = self._current_case
        self._current_case = None
        return case

    # ------------------------------------------------------------------
    # Phase 级别
    # ------------------------------------------------------------------

    def start_phase(self, phase_name: str) -> PhaseReport:
        """开始收集一个阶段的数据

        Args:
            phase_name: 阶段名称（pre_process / test_case / post_process）
        """
        self._phase_start = time.time()
        self._current_phase = PhaseReport(name=phase_name)
        logger.debug(f"[ReportCollector] 开始阶段: {phase_name}")
        return self._current_phase

    def end_phase(self, status: str = "ok") -> Optional[PhaseReport]:
        """结束当前阶段，记录状态和耗时"""
        if self._current_phase is None:
            return None

        self._current_phase.status = status
        self._current_phase.duration = round(time.time() - self._phase_start, 3)

        # 挂载到当前 case
        if self._current_case is not None:
            phase_name = self._current_phase.name
            if phase_name == "pre_process":
                self._current_case.pre_process = self._current_phase
            elif phase_name == "test_case":
                self._current_case.test_case = self._current_phase
            elif phase_name == "post_process":
                self._current_case.post_process = self._current_phase

        logger.debug(
            f"[ReportCollector] 阶段结束: {self._current_phase.name} "
            f"status={status} duration={self._current_phase.duration}s"
        )

        phase = self._current_phase
        self._current_phase = None
        return phase

    # ------------------------------------------------------------------
    # Step 级别
    # ------------------------------------------------------------------

    def record_step(self, step_info: Dict[str, Any]) -> StepReport:
        """记录一个步骤的执行结果

        Args:
            step_info: 步骤信息字典，支持的字段：
                - index: 步骤序号
                - action: 关键字
                - model: 模型标识
                - data: 数据
                - status: ok / fail / skip
                - duration: 耗时
                - screenshot: 截图路径
                - log: 日志文本
                - return_value: 返回值
                - error: 错误信息
                - diagnosis: Agent 诊断信息
                - retry_history: 重试历史
        """
        step = StepReport(
            index=step_info.get("index", 0),
            action=step_info.get("action", ""),
            model=step_info.get("model", ""),
            data=step_info.get("data", ""),
            status=step_info.get("status", "ok"),
            duration=step_info.get("duration", 0.0),
            screenshot=step_info.get("screenshot"),
            log=step_info.get("log", ""),
            return_value=step_info.get("return_value"),
            error=step_info.get("error"),
            diagnosis=step_info.get("diagnosis"),
            retry_history=step_info.get("retry_history", []),
        )

        if self._current_phase is not None:
            self._current_phase.steps.append(step)

        return step

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _compute_summary(self) -> RunSummary:
        """根据已收集的 case 结果计算汇总"""
        if self._report is None:
            return RunSummary()

        total = len(self._report.cases)
        passed = sum(1 for c in self._report.cases if c.status == "PASS")
        failed = sum(1 for c in self._report.cases if c.status == "FAIL")
        skipped = sum(1 for c in self._report.cases if c.status == "SKIP")
        error = sum(1 for c in self._report.cases if c.status == "ERROR")
        duration = self._report.duration
        pass_rate = (passed / total * 100) if total > 0 else 0.0

        return RunSummary(
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            error=error,
            pass_rate=round(pass_rate, 2),
            duration=round(duration, 3),
        )
