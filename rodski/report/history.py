"""历史数据管理 — 管理多次运行的历史索引 (history.json)

存储格式见任务描述：每次运行只保存 case_id -> {status, duration, error} 的摘要，
以及可选的诊断信息摘要。零外部依赖。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .data_model import ReportData

logger = logging.getLogger("rodski")

# history.json 最多保留的运行记录数
_MAX_HISTORY_RUNS = 100


class HistoryManager:
    """管理多次运行的历史数据

    数据存储在 result_dir/history.json，格式：
    {
      "runs": [
        {
          "run_id": "run_20260416_1430",
          "timestamp": "2026-04-16T14:30:00",
          "total": 22, "passed": 20, "failed": 1, "skipped": 1,
          "pass_rate": 90.9, "duration": 45.3,
          "cases": {
            "TC001": {"status": "PASS", "duration": 2.1},
            "TC002": {"status": "FAIL", "duration": 3.4,
                      "error": "Element not found: #submit"}
          }
        }
      ]
    }
    """

    def __init__(self, result_dir: str) -> None:
        self.result_dir = Path(result_dir)
        self.history_file = self.result_dir / "history.json"

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def add_run(self, report_data: ReportData) -> None:
        """将一次运行的摘要添加到历史索引"""
        history = self._load_raw()
        runs: List[Dict[str, Any]] = history.get("runs", [])

        run_entry = self._build_run_entry(report_data)
        runs.append(run_entry)

        # 超过上限则裁剪最旧的记录
        if len(runs) > _MAX_HISTORY_RUNS:
            runs = runs[-_MAX_HISTORY_RUNS:]

        history["runs"] = runs
        self._save_raw(history)
        logger.info(
            f"[HistoryManager] 已添加 run_id={run_entry['run_id']}，"
            f"历史记录数={len(runs)}"
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_history(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """获取最近 N 次运行摘要"""
        runs = self._load_raw().get("runs", [])
        return runs[-last_n:] if last_n > 0 else runs

    def get_case_history(
        self, case_id: str, last_n: int = 10
    ) -> List[Dict[str, Any]]:
        """获取特定用例的历史记录

        返回格式: [{run_id, timestamp, status, duration, error?}, ...]
        """
        runs = self._load_raw().get("runs", [])
        records: List[Dict[str, Any]] = []

        for run in runs:
            case_info = run.get("cases", {}).get(case_id)
            if case_info is not None:
                record: Dict[str, Any] = {
                    "run_id": run.get("run_id", ""),
                    "timestamp": run.get("timestamp", ""),
                    "status": case_info.get("status", ""),
                    "duration": case_info.get("duration", 0),
                }
                if case_info.get("error"):
                    record["error"] = case_info["error"]
                records.append(record)

        return records[-last_n:] if last_n > 0 else records

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """按 run_id 获取单次运行"""
        for run in self._load_raw().get("runs", []):
            if run.get("run_id") == run_id:
                return run
        return None

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _build_run_entry(report_data: ReportData) -> Dict[str, Any]:
        """从 ReportData 构建精简的历史条目"""
        cases: Dict[str, Dict[str, Any]] = {}
        for c in report_data.cases:
            entry: Dict[str, Any] = {
                "status": c.status,
                "duration": round(c.duration, 3),
            }
            # 从 steps 中提取第一个 error 信息
            error_msg = _extract_first_error(c)
            if error_msg:
                entry["error"] = error_msg

            # 保存诊断摘要（WI-44）
            diagnosis_list = _extract_diagnosis_summary(c)
            if diagnosis_list:
                entry["diagnosis"] = diagnosis_list

            cases[c.case_id] = entry

        # 从 summary 中获取汇总数据（兼容 Wave 1 ReportData 结构）
        summary = report_data.summary
        total = summary.total if summary else 0
        passed = summary.passed if summary else 0
        failed = summary.failed if summary else 0
        skipped = summary.skipped if summary else 0
        pass_rate = summary.pass_rate if summary else 0.0

        timestamp = ""
        if report_data.start_time:
            timestamp = report_data.start_time.isoformat()

        return {
            "run_id": report_data.run_id,
            "timestamp": timestamp,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": round(pass_rate, 1),
            "duration": round(report_data.duration, 3),
            "cases": cases,
        }

    def _load_raw(self) -> Dict[str, Any]:
        """加载 history.json，文件不存在则返回空结构"""
        if not self.history_file.exists():
            return {"runs": []}
        try:
            text = self.history_file.read_text(encoding="utf-8")
            data = json.loads(text)
            if not isinstance(data, dict) or "runs" not in data:
                return {"runs": []}
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"[HistoryManager] 加载 history.json 失败: {exc}")
            return {"runs": []}

    def _save_raw(self, data: Dict[str, Any]) -> None:
        """写入 history.json"""
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.history_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _iter_all_steps(case_report):
    """遍历 CaseReport 所有阶段的所有步骤"""
    for phase in (case_report.pre_process, case_report.test_case, case_report.post_process):
        if phase and hasattr(phase, "steps"):
            yield from (phase.steps or [])


def _extract_first_error(case_report) -> Optional[str]:
    """从 CaseReport 的步骤中提取第一个错误信息"""
    for step in _iter_all_steps(case_report):
        if hasattr(step, "error") and step.error:
            return step.error
    return None


def _extract_diagnosis_summary(case_report) -> List[Dict[str, Any]]:
    """从 CaseReport 的步骤中提取诊断摘要

    只保留 category + strategy + fixed 三个关键字段，避免历史膨胀。
    """
    summaries: List[Dict[str, Any]] = []
    for step in _iter_all_steps(case_report):
        if hasattr(step, "diagnosis") and step.diagnosis:
            summary: Dict[str, Any] = {}
            # 兼容不同的 diagnosis 格式
            diag = step.diagnosis
            if isinstance(diag, dict):
                if diag.get("failure_reason"):
                    summary["category"] = diag.get("failure_reason", "")
                if diag.get("recovery_action"):
                    action = diag["recovery_action"]
                    if isinstance(action, dict):
                        summary["strategy"] = action.get("action", "")
            if summary:
                summaries.append(summary)

        # 从重试历史中提取修复结果
        if hasattr(step, "retry_history"):
            for retry in step.retry_history:
                if isinstance(retry, dict) and retry.get("strategy"):
                    summaries.append({
                        "strategy": retry.get("strategy", ""),
                        "fixed": retry.get("fixed", False),
                    })
    return summaries
