"""MemoryStore 单元测试。

测试 src/rodski_agent/common/memory_store.py 中 MemoryStore 的所有公开方法。
覆盖：fix_patterns CRUD、app_models CRUD、淘汰策略、统计信息。
所有文件系统操作通过 pytest tmp_path 隔离。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from rodski_agent.common.memory_store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    """创建一个使用临时目录的 MemoryStore 实例。"""
    db_path = tmp_path / "test_memory.db"
    s = MemoryStore(db_path=db_path)
    yield s
    s.close()


# ============================================================
# 初始化
# ============================================================


class TestInit:
    """MemoryStore -- 初始化与 Schema"""

    def test_初始化创建数据库文件(self, tmp_path: Path):
        """MemoryStore 初始化时应创建 SQLite 数据库文件。"""
        db_path = tmp_path / "sub" / "memory.db"
        s = MemoryStore(db_path=db_path)
        assert db_path.exists()
        s.close()

    def test_初始化创建表结构(self, store: MemoryStore):
        """MemoryStore 初始化后应包含 fix_patterns 和 app_models 两张表。"""
        cursor = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        assert "fix_patterns" in tables
        assert "app_models" in tables

    def test_重复初始化幂等(self, tmp_path: Path):
        """对同一个数据库文件多次创建 MemoryStore 不应报错。"""
        db_path = tmp_path / "memory.db"
        s1 = MemoryStore(db_path=db_path)
        s1.record_fix("err", "fix", True)
        s1.close()

        s2 = MemoryStore(db_path=db_path)
        results = s2.find_fix("err", min_confidence=0.0)
        assert len(results) == 1
        s2.close()


# ============================================================
# fix_patterns CRUD
# ============================================================


class TestRecordFix:
    """MemoryStore.record_fix -- 记录修复结果"""

    def test_记录成功修复(self, store: MemoryStore):
        """record_fix(success=True) 应创建新行且 success_count=1。"""
        store.record_fix("element_not_found", "update_locator", success=True)
        rows = store.find_fix("element_not_found", min_confidence=0.0)
        assert len(rows) == 1
        assert rows[0]["success_count"] == 1
        assert rows[0]["fail_count"] == 0
        assert rows[0]["confidence"] == 1.0

    def test_记录失败修复(self, store: MemoryStore):
        """record_fix(success=False) 应创建新行且 fail_count=1。"""
        store.record_fix("timeout", "add_wait", success=False)
        rows = store.find_fix("timeout", min_confidence=0.0)
        assert len(rows) == 1
        assert rows[0]["success_count"] == 0
        assert rows[0]["fail_count"] == 1
        assert rows[0]["confidence"] == 0.0

    def test_同pattern同strategy更新计数(self, store: MemoryStore):
        """对相同 pattern+strategy 组合多次 record_fix 应累加计数而非创建新行。"""
        store.record_fix("element_not_found", "update_locator", success=True)
        store.record_fix("element_not_found", "update_locator", success=True)
        store.record_fix("element_not_found", "update_locator", success=False)

        rows = store.find_fix("element_not_found", min_confidence=0.0)
        assert len(rows) == 1
        assert rows[0]["success_count"] == 2
        assert rows[0]["fail_count"] == 1
        assert abs(rows[0]["confidence"] - 2 / 3) < 1e-9

    def test_不同strategy创建独立行(self, store: MemoryStore):
        """相同 pattern 不同 strategy 应创建独立行。"""
        store.record_fix("element_not_found", "update_locator", success=True)
        store.record_fix("element_not_found", "add_wait", success=True)

        rows = store.find_fix("element_not_found", min_confidence=0.0)
        assert len(rows) == 2


class TestFindFix:
    """MemoryStore.find_fix -- 查找修复策略"""

    def test_模糊匹配(self, store: MemoryStore):
        """find_fix 应通过 LIKE 模糊匹配 failure_pattern。"""
        store.record_fix("element_not_found: #loginBtn", "update_locator", success=True)
        results = store.find_fix("element_not_found")
        assert len(results) == 1

    def test_置信度过滤(self, store: MemoryStore):
        """find_fix 应过滤掉低于 min_confidence 的结果。"""
        store.record_fix("timeout", "add_wait", success=False)
        # confidence = 0.0，默认 min_confidence = 0.3
        results = store.find_fix("timeout")
        assert len(results) == 0

        results = store.find_fix("timeout", min_confidence=0.0)
        assert len(results) == 1

    def test_按置信度降序排列(self, store: MemoryStore):
        """find_fix 返回结果应按 confidence DESC 排序。"""
        store.record_fix("error", "strategy_a", success=True)
        # strategy_a: confidence = 1.0

        store.record_fix("error", "strategy_b", success=True)
        store.record_fix("error", "strategy_b", success=False)
        # strategy_b: confidence = 0.5

        results = store.find_fix("error", min_confidence=0.0)
        assert len(results) == 2
        assert results[0]["confidence"] > results[1]["confidence"]

    def test_无匹配返回空列表(self, store: MemoryStore):
        """find_fix 无匹配时应返回空列表。"""
        results = store.find_fix("nonexistent_pattern")
        assert results == []


class TestUpdateConfidence:
    """MemoryStore.update_confidence -- 置信度重算"""

    def test_重算置信度(self, store: MemoryStore):
        """update_confidence 应根据 success/fail 计数重算。"""
        store.record_fix("err", "fix", success=True)
        rows = store.find_fix("err", min_confidence=0.0)
        pid = rows[0]["id"]

        # 手动修改计数来验证 update_confidence 独立计算
        store._conn.execute(
            "UPDATE fix_patterns SET success_count = 3, fail_count = 7 WHERE id = ?",
            (pid,),
        )
        store._conn.commit()
        store.update_confidence(pid)

        rows = store.find_fix("err", min_confidence=0.0)
        assert abs(rows[0]["confidence"] - 0.3) < 1e-9

    def test_不存在的id无异常(self, store: MemoryStore):
        """update_confidence 传入不存在的 id 不应抛出异常。"""
        store.update_confidence(99999)  # 不应抛出异常


# ============================================================
# app_models CRUD
# ============================================================


class TestAppModels:
    """MemoryStore -- app_models CRUD"""

    def test_保存并获取模型(self, store: MemoryStore):
        """save_app_model + get_app_model 应正确保存和读取。"""
        xml = "<models><model name='Login'/></models>"
        store.save_app_model("LoginPage", xml, window_title="Login - Demo")

        model = store.get_app_model("LoginPage")
        assert model is not None
        assert model["app_name"] == "LoginPage"
        assert model["model_xml"] == xml
        assert model["window_title"] == "Login - Demo"
        assert model["reliability"] == 1.0

    def test_更新覆盖已有模型(self, store: MemoryStore):
        """对同一 app_name 再次 save_app_model 应更新而非新增。"""
        store.save_app_model("LoginPage", "<v1/>")
        store.save_app_model("LoginPage", "<v2/>", window_title="Updated")

        model = store.get_app_model("LoginPage")
        assert model["model_xml"] == "<v2/>"
        assert model["window_title"] == "Updated"
        assert model["reliability"] == 1.0

        # 验证只有一行
        count = store._conn.execute(
            "SELECT COUNT(*) as cnt FROM app_models WHERE app_name = 'LoginPage'"
        ).fetchone()["cnt"]
        assert count == 1

    def test_获取不存在的模型返回None(self, store: MemoryStore):
        """get_app_model 查不到时应返回 None。"""
        assert store.get_app_model("nonexistent") is None

    def test_标记模型为stale(self, store: MemoryStore):
        """mark_stale 应将 reliability 设为 0。"""
        store.save_app_model("LoginPage", "<xml/>")
        store.mark_stale("LoginPage")

        model = store.get_app_model("LoginPage")
        assert model["reliability"] == 0.0

    def test_更新stale模型恢复reliability(self, store: MemoryStore):
        """对 stale 模型重新 save_app_model 应恢复 reliability 为 1.0。"""
        store.save_app_model("LoginPage", "<v1/>")
        store.mark_stale("LoginPage")
        store.save_app_model("LoginPage", "<v2/>")

        model = store.get_app_model("LoginPage")
        assert model["reliability"] == 1.0


# ============================================================
# 淘汰
# ============================================================


class TestCleanup:
    """MemoryStore -- 淘汰策略"""

    def test_cleanup_删除低置信度旧记录(self, store: MemoryStore):
        """cleanup 应删除 confidence < 阈值且 last_used 超过 max_age_days 的记录。"""
        store.record_fix("old_error", "bad_fix", success=False)
        # 手动将 last_used 设为 60 天前
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        store._conn.execute(
            "UPDATE fix_patterns SET last_used = ?", (old_time,)
        )
        store._conn.commit()

        deleted = store.cleanup(max_age_days=30, min_confidence=0.3)
        assert deleted == 1

    def test_cleanup_保留高置信度记录(self, store: MemoryStore):
        """cleanup 不应删除高置信度记录，即使时间很久。"""
        store.record_fix("error", "good_fix", success=True)
        # confidence = 1.0
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        store._conn.execute(
            "UPDATE fix_patterns SET last_used = ?", (old_time,)
        )
        store._conn.commit()

        deleted = store.cleanup(max_age_days=30, min_confidence=0.3)
        assert deleted == 0

    def test_cleanup_保留近期低置信度记录(self, store: MemoryStore):
        """cleanup 不应删除近期的低置信度记录（last_used < max_age_days）。"""
        store.record_fix("error", "bad_fix", success=False)
        # confidence = 0.0, last_used = 刚才（今天）
        deleted = store.cleanup(max_age_days=30, min_confidence=0.3)
        assert deleted == 0

    def test_cleanup_stale_models_删除过期stale模型(self, store: MemoryStore):
        """cleanup_stale_models 应删除 reliability=0 且超时的模型。"""
        store.save_app_model("OldPage", "<xml/>")
        store.mark_stale("OldPage")
        # 将 last_verified 设为 14 天前
        old_time = (datetime.now(timezone.utc) - timedelta(days=14)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        store._conn.execute(
            "UPDATE app_models SET last_verified = ?", (old_time,)
        )
        store._conn.commit()

        deleted = store.cleanup_stale_models(max_age_days=7)
        assert deleted == 1

    def test_cleanup_stale_models_保留正常模型(self, store: MemoryStore):
        """cleanup_stale_models 不应删除 reliability > 0 的模型。"""
        store.save_app_model("GoodPage", "<xml/>")
        deleted = store.cleanup_stale_models(max_age_days=7)
        assert deleted == 0


# ============================================================
# 统计
# ============================================================


class TestGetStats:
    """MemoryStore.get_stats -- 统计信息"""

    def test_空库统计(self, store: MemoryStore):
        """空库的统计信息应全为 0。"""
        stats = store.get_stats()
        assert stats["fix_patterns"]["total"] == 0
        assert stats["fix_patterns"]["high_confidence"] == 0
        assert stats["app_models"]["total"] == 0
        assert stats["app_models"]["stale"] == 0

    def test_有数据时统计正确(self, store: MemoryStore):
        """插入数据后统计应准确反映各项指标。"""
        store.record_fix("err1", "fix1", success=True)   # confidence = 1.0 (高)
        store.record_fix("err2", "fix2", success=False)   # confidence = 0.0 (低)

        store.save_app_model("Page1", "<xml/>")
        store.save_app_model("Page2", "<xml/>")
        store.mark_stale("Page2")

        stats = store.get_stats()
        assert stats["fix_patterns"]["total"] == 2
        assert stats["fix_patterns"]["high_confidence"] == 1
        assert stats["app_models"]["total"] == 2
        assert stats["app_models"]["stale"] == 1


# ============================================================
# 生命周期
# ============================================================


class TestLifecycle:
    """MemoryStore -- 生命周期管理"""

    def test_close_关闭连接(self, tmp_path: Path):
        """close 后操作数据库应抛出异常。"""
        db_path = tmp_path / "memory.db"
        s = MemoryStore(db_path=db_path)
        s.close()
        with pytest.raises(Exception):
            s.record_fix("err", "fix", True)
