"""趋势计算 — 基于历史数据计算通过率趋势、耗时趋势、不稳定用例、缺陷聚合等

零外部依赖；缺陷 fingerprint 去除动态部分后取哈希。
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any, Dict, List, Set


class TrendCalculator:
    """基于历史数据计算趋势

    Args:
        history: HistoryManager.get_history() 返回的运行摘要列表
    """

    def __init__(self, history: List[Dict[str, Any]]) -> None:
        self.history = history

    # ------------------------------------------------------------------
    # 通过率 / 耗时
    # ------------------------------------------------------------------

    def pass_rate_trend(self) -> List[Dict[str, Any]]:
        """通过率趋势

        Returns:
            [{run_id, timestamp, pass_rate}, ...]
        """
        return [
            {
                "run_id": run.get("run_id", ""),
                "timestamp": run.get("timestamp", ""),
                "pass_rate": run.get("pass_rate", 0),
            }
            for run in self.history
        ]

    def duration_trend(self) -> List[Dict[str, Any]]:
        """耗时趋势

        Returns:
            [{run_id, timestamp, duration}, ...]
        """
        return [
            {
                "run_id": run.get("run_id", ""),
                "timestamp": run.get("timestamp", ""),
                "duration": run.get("duration", 0),
            }
            for run in self.history
        ]

    # ------------------------------------------------------------------
    # 不稳定用例
    # ------------------------------------------------------------------

    def flaky_cases(self) -> List[Dict[str, Any]]:
        """不稳定用例检测

        不稳定定义：同一 case 在最近 N 次运行中状态不一致
        （既有 PASS 又有 FAIL）。

        Returns:
            [{case_id, flaky_rate, runs_checked}, ...]
            flaky_rate: 状态翻转次数 / (runs_checked - 1)
        """
        # 收集每个 case 的状态序列
        case_statuses: Dict[str, List[str]] = defaultdict(list)
        for run in self.history:
            for case_id, info in run.get("cases", {}).items():
                case_statuses[case_id].append(info.get("status", ""))

        result: List[Dict[str, Any]] = []
        for case_id, statuses in case_statuses.items():
            if len(statuses) < 2:
                continue
            # 只关注 PASS / FAIL（SKIP 不算翻转）
            relevant = [s for s in statuses if s in ("PASS", "FAIL")]
            if len(relevant) < 2:
                continue
            unique = set(relevant)
            if len(unique) <= 1:
                continue
            # 计算翻转次数
            flips = sum(
                1 for i in range(1, len(relevant)) if relevant[i] != relevant[i - 1]
            )
            flaky_rate = round(flips / (len(relevant) - 1), 3)
            result.append(
                {
                    "case_id": case_id,
                    "flaky_rate": flaky_rate,
                    "runs_checked": len(relevant),
                }
            )
        # 按 flaky_rate 降序
        result.sort(key=lambda x: x["flaky_rate"], reverse=True)
        return result

    # ------------------------------------------------------------------
    # 缺陷聚合
    # ------------------------------------------------------------------

    def defect_clusters(self) -> List[Dict[str, Any]]:
        """缺陷聚合 — 按错误消息 fingerprint 分组

        fingerprint 通过去除动态部分（时间戳、UUID、数字序列）后取 MD5 前12位。

        Returns:
            [{error_fingerprint, sample_error, count, case_ids,
              first_seen, last_seen}, ...]
        """
        clusters: Dict[str, Dict[str, Any]] = {}

        for run in self.history:
            ts = run.get("timestamp", "")
            for case_id, info in run.get("cases", {}).items():
                error = info.get("error", "")
                if not error:
                    continue
                fp = _error_fingerprint(error)
                if fp not in clusters:
                    clusters[fp] = {
                        "error_fingerprint": fp,
                        "sample_error": error,
                        "count": 0,
                        "case_ids": set(),
                        "first_seen": ts,
                        "last_seen": ts,
                    }
                clusters[fp]["count"] += 1
                clusters[fp]["case_ids"].add(case_id)
                clusters[fp]["last_seen"] = ts

        # set -> list 并按 count 降序
        result: List[Dict[str, Any]] = []
        for c in clusters.values():
            c["case_ids"] = sorted(c["case_ids"])
            result.append(c)
        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    # ------------------------------------------------------------------
    # 新增失败 / 修复成功
    # ------------------------------------------------------------------

    def new_failures(self) -> List[str]:
        """新增失败：上次通过但本次失败的 case_id

        需要至少两次运行才有意义。
        """
        if len(self.history) < 2:
            return []
        prev_cases = self.history[-2].get("cases", {})
        curr_cases = self.history[-1].get("cases", {})

        result: List[str] = []
        for case_id, curr in curr_cases.items():
            if curr.get("status") == "FAIL":
                prev = prev_cases.get(case_id)
                if prev and prev.get("status") == "PASS":
                    result.append(case_id)
        return sorted(result)

    def fixed_cases(self) -> List[str]:
        """修复成功：上次失败但本次通过的 case_id"""
        if len(self.history) < 2:
            return []
        prev_cases = self.history[-2].get("cases", {})
        curr_cases = self.history[-1].get("cases", {})

        result: List[str] = []
        for case_id, curr in curr_cases.items():
            if curr.get("status") == "PASS":
                prev = prev_cases.get(case_id)
                if prev and prev.get("status") == "FAIL":
                    result.append(case_id)
        return sorted(result)

    # ------------------------------------------------------------------
    # WI-44: Agent 诊断统计
    # ------------------------------------------------------------------

    def diagnosis_summary(self) -> Dict[str, int]:
        """Agent 诊断统计

        从历史记录中的 step diagnosis 字段统计各诊断类别出现次数。

        Returns:
            {category: count}  例如 {"Element not found": 5, "Timeout": 2}
        """
        counts: Dict[str, int] = defaultdict(int)
        for run in self.history:
            for _case_id, info in run.get("cases", {}).items():
                for diag in info.get("diagnosis", []):
                    cat = diag.get("category", "")
                    if cat:
                        counts[cat] += 1
        return dict(counts)

    def fix_success_rate(self) -> Dict[str, Dict[str, Any]]:
        """修复成功率

        从历史记录中的 diagnosis 条目统计各修复策略的成功率。

        Returns:
            {strategy: {total: int, success: int, rate: float}}
        """
        stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total": 0, "success": 0}
        )
        for run in self.history:
            for _case_id, info in run.get("cases", {}).items():
                for diag in info.get("diagnosis", []):
                    strategy = diag.get("strategy", "")
                    if not strategy:
                        continue
                    stats[strategy]["total"] += 1
                    if diag.get("fixed"):
                        stats[strategy]["success"] += 1

        result: Dict[str, Dict[str, Any]] = {}
        for strategy, s in stats.items():
            total = s["total"]
            success = s["success"]
            result[strategy] = {
                "total": total,
                "success": success,
                "rate": round(success / total, 3) if total > 0 else 0,
            }
        return result


# ======================================================================
# 工具函数
# ======================================================================

# 用于去除错误消息中动态部分的模式
_DYNAMIC_PATTERNS = [
    # ISO 时间戳: 2026-04-16T14:30:00 或 2026-04-16 14:30:00.123
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?"),
    # 日期: 2026-04-16, 2026/04/16
    re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}"),
    # UUID: 550e8400-e29b-41d4-a716-446655440000
    re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"),
    # 长十六进制序列 (>= 8 位): 0x7f3a2b1c, session_abc123def456
    re.compile(r"0x[0-9a-fA-F]{4,}"),
    re.compile(r"[0-9a-fA-F]{8,}"),
    # 纯数字序列 (>= 4 位): port 8080, id 12345
    re.compile(r"\b\d{4,}\b"),
]


def _error_fingerprint(error_msg: str) -> str:
    """将错误消息标准化后取 MD5 前12位作为 fingerprint

    去除时间戳、UUID、长数字等动态部分，使同类错误聚合到同一 fingerprint。
    """
    normalized = error_msg
    for pattern in _DYNAMIC_PATTERNS:
        normalized = pattern.sub("<DYN>", normalized)
    # 合并连续空白
    normalized = re.sub(r"\s+", " ", normalized).strip()
    md5 = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return md5[:12]
