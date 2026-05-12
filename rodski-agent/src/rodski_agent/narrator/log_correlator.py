"""LogCorrelator — 解析 RodSki 执行日志，提取步骤级运行时信息。

日志格式示例：
    2026-05-07 15:37:12,488 [INFO] 执行用例 1/3: TC020 - SQLite查询订单
    2026-05-07 15:37:12,488 [INFO] 执行关键字: DB(model=QuerySQL, data=Q001)
    2026-05-07 15:37:12,488 [INFO] DB query: SELECT ...
    2026-05-07 15:37:12,489 [INFO] [STEP] action=DB model=QuerySQL status=OK
    2026-05-07 15:37:14,029 [INFO]   PASS (1.542s)

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ============================================================
# 数据结构
# ============================================================

@dataclass
class StepLogEntry:
    action: str = ""
    model_name: str = ""
    data_id: str = ""
    status: str = ""        # OK | FAIL
    sql: str = ""           # DB query/execute 语句
    return_value: str = ""  # history[N] 的原始字符串（截断）
    keyword_line: str = ""  # 执行关键字原始行


@dataclass
class CaseLogInfo:
    case_id: str
    title: str
    status: str = ""        # PASS | FAIL
    duration_s: float = 0.0
    steps: list[StepLogEntry] = field(default_factory=list)


# ============================================================
# 正则
# ============================================================

_RE_CASE_START = re.compile(
    r"执行用例\s+\d+/\d+:\s+(\S+)\s+-\s+(.*)"
)
_RE_KEYWORD = re.compile(
    r"执行关键字:\s+(\w+)\((?:model=(\w*),\s*data=(\S*))?\)"
)
_RE_STEP = re.compile(
    r"\[STEP\]\s+action=(\S+)\s+model=(\S*)\s+status=(\S+)"
)
_RE_SQL_QUERY = re.compile(r"DB query:\s+(.*)")
_RE_SQL_EXEC = re.compile(r"DB execute:\s+(.*)")
_RE_HISTORY = re.compile(r"history\[\d+\]=(.{0,200})")
_RE_PASS = re.compile(r"\s+PASS\s+\((\d+\.\d+)s\)")
_RE_FAIL = re.compile(r"\s+FAIL\s+\((\d+\.\d+)s\)")


# ============================================================
# LogCorrelator
# ============================================================

class LogCorrelator:
    """解析执行日志，返回按 case_id 索引的步骤信息。"""

    def __init__(self, log_path: str) -> None:
        self.log_path = Path(log_path)

    def correlate(self) -> dict[str, CaseLogInfo]:
        """解析日志，返回 {case_id: CaseLogInfo}。"""
        if not self.log_path.exists():
            return {}

        lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        result: dict[str, CaseLogInfo] = {}
        current: CaseLogInfo | None = None
        current_step: StepLogEntry | None = None

        for line in lines:
            # 去掉时间戳和日志级别前缀，只保留消息部分
            msg = _strip_prefix(line)

            # 用例开始
            m = _RE_CASE_START.search(msg)
            if m:
                if current is not None:
                    result[current.case_id] = current
                current = CaseLogInfo(case_id=m.group(1), title=m.group(2).strip())
                current_step = None
                continue

            if current is None:
                continue

            # 关键字执行行 → 开始新步骤
            m = _RE_KEYWORD.search(msg)
            if m:
                current_step = StepLogEntry(
                    action=m.group(1),
                    model_name=m.group(2) or "",
                    data_id=m.group(3) or "",
                    keyword_line=msg.strip(),
                )
                current.steps.append(current_step)
                continue

            if current_step is None:
                # 还没遇到关键字行，跳过
                pass
            else:
                # SQL 语句
                m = _RE_SQL_QUERY.search(msg)
                if m:
                    current_step.sql = m.group(1).strip()
                    continue
                m = _RE_SQL_EXEC.search(msg)
                if m:
                    current_step.sql = m.group(1).strip()
                    continue

                # 步骤状态
                m = _RE_STEP.search(msg)
                if m:
                    current_step.action = m.group(1)
                    current_step.status = m.group(3)
                    continue

                # 返回值（history）
                m = _RE_HISTORY.search(msg)
                if m and not current_step.return_value:
                    current_step.return_value = m.group(1).strip()
                    continue

            # 用例结果
            m = _RE_PASS.search(msg)
            if m:
                current.status = "PASS"
                current.duration_s = float(m.group(1))
                continue
            m = _RE_FAIL.search(msg)
            if m:
                current.status = "FAIL"
                current.duration_s = float(m.group(1))
                continue

        # 保存最后一个 case
        if current is not None:
            result[current.case_id] = current

        return result

    @staticmethod
    def to_dict(info: CaseLogInfo) -> dict[str, Any]:
        return {
            "case_id": info.case_id,
            "title": info.title,
            "status": info.status,
            "duration_s": info.duration_s,
            "steps": [
                {
                    "action": s.action,
                    "model_name": s.model_name,
                    "data_id": s.data_id,
                    "status": s.status,
                    "sql": s.sql,
                    "return_value": s.return_value,
                    "keyword_line": s.keyword_line,
                }
                for s in info.steps
            ],
        }


# ============================================================
# 工具函数
# ============================================================

def _strip_prefix(line: str) -> str:
    """去掉 '2026-05-07 15:37:12,488 [INFO] ' 前缀，返回消息部分。"""
    # 格式：YYYY-MM-DD HH:MM:SS,mmm [LEVEL] message
    idx = line.find("] ")
    if idx != -1:
        return line[idx + 2:]
    return line
