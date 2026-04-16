"""Agent 历史记忆存储 -- 基于 SQLite 的修复模式学习与应用模型缓存。

提供两类持久化数据：
  - fix_patterns: 失败模式 → 修复策略的映射，带置信度与使用计数
  - app_models: 应用页面模型缓存，供 Agent 复用已探索的 UI 结构

仅依赖 Python 标准库（sqlite3）。
所有时间操作使用 UTC。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


class MemoryStore:
    """Agent 历史记忆存储（SQLite）。

    Parameters
    ----------
    db_path : Path | None
        SQLite 数据库文件路径。为 ``None`` 时使用默认路径
        ``~/.rodski-agent/memory.db``。
    """

    DEFAULT_DB_PATH = Path.home() / ".rodski-agent" / "memory.db"

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        """创建表结构（幂等）。"""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS fix_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                failure_pattern TEXT NOT NULL,
                fix_strategy TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.0,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS app_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT DEFAULT '',
                model_xml TEXT NOT NULL,
                screenshot_path TEXT DEFAULT '',
                last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reliability REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_fix_pattern
                ON fix_patterns(failure_pattern);
            CREATE INDEX IF NOT EXISTS idx_app_name
                ON app_models(app_name);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # fix_patterns CRUD
    # ------------------------------------------------------------------

    def record_fix(self, failure_pattern: str, fix_strategy: str, success: bool) -> None:
        """记录一次修复结果。

        如果 ``failure_pattern`` + ``fix_strategy`` 组合已存在，更新对应计数；
        否则插入新行。置信度在每次记录后自动重算。
        """
        now = _utcnow_str()
        row = self._conn.execute(
            "SELECT id FROM fix_patterns WHERE failure_pattern = ? AND fix_strategy = ?",
            (failure_pattern, fix_strategy),
        ).fetchone()

        if row:
            col = "success_count" if success else "fail_count"
            self._conn.execute(
                f"UPDATE fix_patterns SET {col} = {col} + 1, last_used = ? WHERE id = ?",
                (now, row["id"]),
            )
            self.update_confidence(row["id"])
        else:
            s_count = 1 if success else 0
            f_count = 0 if success else 1
            total = s_count + f_count
            confidence = s_count / total if total > 0 else 0.0
            self._conn.execute(
                """INSERT INTO fix_patterns
                   (failure_pattern, fix_strategy, success_count, fail_count,
                    confidence, last_used, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (failure_pattern, fix_strategy, s_count, f_count,
                 confidence, now, now),
            )
        self._conn.commit()

    def find_fix(self, failure_pattern: str, min_confidence: float = 0.3) -> list[dict]:
        """查找匹配的修复策略，按置信度降序排列。

        使用 LIKE 进行模糊匹配（``%pattern%``）。
        """
        rows = self._conn.execute(
            """SELECT id, failure_pattern, fix_strategy, success_count,
                      fail_count, confidence, last_used, created_at
               FROM fix_patterns
               WHERE failure_pattern LIKE ? AND confidence >= ?
               ORDER BY confidence DESC""",
            (f"%{failure_pattern}%", min_confidence),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_confidence(self, pattern_id: int) -> None:
        """重新计算置信度：``success / (success + fail)``。"""
        row = self._conn.execute(
            "SELECT success_count, fail_count FROM fix_patterns WHERE id = ?",
            (pattern_id,),
        ).fetchone()
        if row is None:
            return
        total = row["success_count"] + row["fail_count"]
        confidence = row["success_count"] / total if total > 0 else 0.0
        self._conn.execute(
            "UPDATE fix_patterns SET confidence = ? WHERE id = ?",
            (confidence, pattern_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # app_models CRUD
    # ------------------------------------------------------------------

    def save_app_model(
        self,
        app_name: str,
        model_xml: str,
        window_title: str = "",
        screenshot_path: str = "",
    ) -> None:
        """保存或更新应用模型。

        如果 ``app_name`` 已存在，覆盖更新；否则插入新行。
        """
        now = _utcnow_str()
        row = self._conn.execute(
            "SELECT id FROM app_models WHERE app_name = ?",
            (app_name,),
        ).fetchone()

        if row:
            self._conn.execute(
                """UPDATE app_models
                   SET model_xml = ?, window_title = ?, screenshot_path = ?,
                       last_verified = ?, reliability = 1.0
                   WHERE id = ?""",
                (model_xml, window_title, screenshot_path, now, row["id"]),
            )
        else:
            self._conn.execute(
                """INSERT INTO app_models
                   (app_name, window_title, model_xml, screenshot_path,
                    last_verified, reliability, created_at)
                   VALUES (?, ?, ?, ?, ?, 1.0, ?)""",
                (app_name, window_title, model_xml, screenshot_path, now, now),
            )
        self._conn.commit()

    def get_app_model(self, app_name: str) -> Optional[dict]:
        """按 ``app_name`` 获取最新的应用模型。

        Returns
        -------
        dict | None
            找到时返回行字典，否则返回 ``None``。
        """
        row = self._conn.execute(
            """SELECT id, app_name, window_title, model_xml, screenshot_path,
                      last_verified, reliability, created_at
               FROM app_models
               WHERE app_name = ?
               ORDER BY last_verified DESC
               LIMIT 1""",
            (app_name,),
        ).fetchone()
        return dict(row) if row else None

    def mark_stale(self, app_name: str) -> None:
        """标记应用模型为 stale（reliability 设为 0）。"""
        self._conn.execute(
            "UPDATE app_models SET reliability = 0.0 WHERE app_name = ?",
            (app_name,),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # 淘汰
    # ------------------------------------------------------------------

    def cleanup(self, max_age_days: int = 30, min_confidence: float = 0.3) -> int:
        """清理低置信度且长时间未使用的 fix_patterns。

        删除条件：``confidence < min_confidence AND last_used < now - max_age_days``。

        Returns
        -------
        int
            删除的记录数。
        """
        cutoff = _utcnow() - timedelta(days=max_age_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(
            "DELETE FROM fix_patterns WHERE confidence < ? AND last_used < ?",
            (min_confidence, cutoff_str),
        )
        self._conn.commit()
        return cursor.rowcount

    def cleanup_stale_models(self, max_age_days: int = 7) -> int:
        """清理过期的 app_models（reliability == 0 且超过 max_age_days 未验证）。

        Returns
        -------
        int
            删除的记录数。
        """
        cutoff = _utcnow() - timedelta(days=max_age_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        cursor = self._conn.execute(
            "DELETE FROM app_models WHERE reliability = 0.0 AND last_verified < ?",
            (cutoff_str,),
        )
        self._conn.commit()
        return cursor.rowcount

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """返回记忆库统计信息。

        Returns
        -------
        dict
            包含 fix_patterns 和 app_models 的统计数据。
        """
        fix_total = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM fix_patterns"
        ).fetchone()["cnt"]
        fix_high_confidence = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM fix_patterns WHERE confidence >= 0.7"
        ).fetchone()["cnt"]
        model_total = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM app_models"
        ).fetchone()["cnt"]
        model_stale = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM app_models WHERE reliability = 0.0"
        ).fetchone()["cnt"]

        return {
            "fix_patterns": {
                "total": fix_total,
                "high_confidence": fix_high_confidence,
            },
            "app_models": {
                "total": model_total,
                "stale": model_stale,
            },
        }

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self) -> None:
        """关闭数据库连接。"""
        self._conn.close()


# ======================================================================
# 内部工具
# ======================================================================


def _utcnow() -> datetime:
    """返回当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def _utcnow_str() -> str:
    """返回当前 UTC 时间的字符串表示（``YYYY-MM-DD HH:MM:SS``）。"""
    return _utcnow().strftime("%Y-%m-%d %H:%M:%S")
