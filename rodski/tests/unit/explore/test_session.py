"""探索会话管理模块单元测试"""

import pytest
import json
import time
from pathlib import Path
from rodski.core.explore.session import (
    ExploreSession,
    ExploreSessionStore,
    BudgetGuard,
    _compute_action_hash,
)


class TestActionHash:
    """测试命令指纹计算"""

    def test_same_command_same_hash(self):
        """相同命令生成相同哈希"""
        cmd1 = {"action": "type", "model": "LoginPage", "data": "username"}
        cmd2 = {"action": "type", "model": "LoginPage", "data": "username"}
        assert _compute_action_hash(cmd1) == _compute_action_hash(cmd2)

    def test_different_command_different_hash(self):
        """不同命令生成不同哈希"""
        cmd1 = {"action": "type", "model": "LoginPage", "data": "username"}
        cmd2 = {"action": "type", "model": "LoginPage", "data": "password"}
        assert _compute_action_hash(cmd1) != _compute_action_hash(cmd2)

    def test_order_independent(self):
        """键顺序不影响哈希（已排序）"""
        cmd1 = {"action": "type", "model": "LoginPage", "data": "test"}
        cmd2 = {"data": "test", "action": "type", "model": "LoginPage"}
        assert _compute_action_hash(cmd1) == _compute_action_hash(cmd2)


class TestExploreSession:
    """测试会话状态数据结构"""

    def test_create_session(self):
        """测试创建会话"""
        session = ExploreSession(
            session_id="test_001",
            module_dir=Path("/tmp/test"),
            started_at=time.time(),
            budget={"steps": 10, "duration": 60.0},
        )
        assert session.session_id == "test_001"
        assert session.status == "running"
        assert session.budget_spent["steps"] == 0

    def test_serialize_deserialize(self):
        """测试序列化和反序列化"""
        session = ExploreSession(
            session_id="test_002",
            module_dir=Path("/tmp/test"),
            started_at=1234567890.0,
            budget={"steps": 20},
            history=[{"command": {"action": "navigate"}, "result": {"success": True}}],
            seen_action_hashes={"abc123", "def456"},
        )

        # 序列化
        data = session.to_dict()
        assert data["session_id"] == "test_002"
        assert data["budget"]["steps"] == 20
        assert len(data["seen_action_hashes"]) == 2

        # 反序列化
        restored = ExploreSession.from_dict(data)
        assert restored.session_id == "test_002"
        assert restored.budget["steps"] == 20
        assert len(restored.seen_action_hashes) == 2


class TestExploreSessionStore:
    """测试会话持久化"""

    @pytest.fixture
    def temp_module(self, tmp_path):
        """临时模块目录"""
        return tmp_path / "test_module"

    @pytest.fixture
    def store(self, temp_module):
        """会话存储实例"""
        return ExploreSessionStore(temp_module)

    def test_save_and_load(self, store, temp_module):
        """测试保存和加载"""
        session = ExploreSession(
            session_id="save_load_001",
            module_dir=temp_module,
            started_at=time.time(),
            budget={"steps": 15},
        )

        # 保存
        store.save(session)

        # 检查文件存在
        session_file = store.session_dir / "session_save_load_001.json"
        assert session_file.exists()

        # 加载
        loaded = store.load("save_load_001")
        assert loaded is not None
        assert loaded.session_id == "save_load_001"
        assert loaded.budget["steps"] == 15

    def test_load_nonexistent(self, store):
        """测试加载不存在的会话"""
        result = store.load("nonexistent_999")
        assert result is None

    def test_list_sessions(self, store, temp_module):
        """测试列出所有会话"""
        # 创建多个会话
        for i in range(3):
            session = ExploreSession(
                session_id=f"list_test_{i:03d}",
                module_dir=temp_module,
                started_at=time.time(),
                budget={},
            )
            store.save(session)

        # 列出
        session_ids = store.list_sessions()
        assert len(session_ids) == 3
        assert "list_test_000" in session_ids
        assert "list_test_002" in session_ids

    def test_delete(self, store, temp_module):
        """测试删除会话"""
        session = ExploreSession(
            session_id="delete_test",
            module_dir=temp_module,
            started_at=time.time(),
            budget={},
        )
        store.save(session)

        # 确认存在
        assert store.load("delete_test") is not None

        # 删除
        store.delete("delete_test")

        # 确认删除
        assert store.load("delete_test") is None

    def test_atomic_write(self, store, temp_module):
        """测试原子写入（多次保存）"""
        session = ExploreSession(
            session_id="atomic_test",
            module_dir=temp_module,
            started_at=time.time(),
            budget={"steps": 10},
        )

        # 第一次保存
        store.save(session)
        loaded1 = store.load("atomic_test")
        assert loaded1.budget_spent["steps"] == 0

        # 修改并再次保存
        session.budget_spent["steps"] = 5
        store.save(session)
        loaded2 = store.load("atomic_test")
        assert loaded2.budget_spent["steps"] == 5


class TestBudgetGuard:
    """测试预算控制"""

    def test_check_budget_sufficient(self):
        """测试预算充足"""
        session = ExploreSession(
            session_id="budget_001",
            module_dir=Path("/tmp"),
            started_at=time.time(),
            budget={"steps": 10, "duration": 60.0},
        )
        guard = BudgetGuard(session)

        stopped, reason = guard.check_budget()
        assert not stopped
        assert reason == ""

    def test_check_budget_steps_exceeded(self):
        """测试步数耗尽"""
        session = ExploreSession(
            session_id="budget_002",
            module_dir=Path("/tmp"),
            started_at=time.time(),
            budget={"steps": 5},
        )
        session.budget_spent["steps"] = 5
        guard = BudgetGuard(session)

        stopped, reason = guard.check_budget()
        assert stopped
        assert reason == "budget_steps"

    def test_check_budget_duration_exceeded(self):
        """测试时长耗尽"""
        session = ExploreSession(
            session_id="budget_003",
            module_dir=Path("/tmp"),
            started_at=time.time() - 70,  # 70 秒前开始
            budget={"duration": 60.0},
        )
        guard = BudgetGuard(session)

        stopped, reason = guard.check_budget()
        assert stopped
        assert reason == "budget_duration"

    def test_is_duplicate(self):
        """测试去重检查"""
        session = ExploreSession(
            session_id="dup_001",
            module_dir=Path("/tmp"),
            started_at=time.time(),
            budget={},
        )
        guard = BudgetGuard(session)

        cmd = {"action": "type", "model": "LoginPage", "data": "test"}

        # 第一次：不重复
        assert not guard.is_duplicate(cmd)

        # 记录
        guard.record_action(cmd)

        # 第二次：重复
        assert guard.is_duplicate(cmd)

    def test_record_action(self):
        """测试记录动作"""
        session = ExploreSession(
            session_id="record_001",
            module_dir=Path("/tmp"),
            started_at=time.time(),
            budget={},
        )
        guard = BudgetGuard(session)

        cmd = {"action": "navigate", "model": "", "data": "http://test.com"}
        guard.record_action(cmd)

        # 检查步数增加
        assert session.budget_spent["steps"] == 1

        # 检查哈希已记录
        assert guard.is_duplicate(cmd)

    def test_get_budget_status(self):
        """测试获取预算状态"""
        session = ExploreSession(
            session_id="status_001",
            module_dir=Path("/tmp"),
            started_at=time.time(),
            budget={"steps": 10, "duration": 60.0},
        )
        session.budget_spent["steps"] = 3
        guard = BudgetGuard(session)

        status = guard.get_budget_status()
        assert status["steps"]["used"] == 3
        assert status["steps"]["remaining"] == 7
        assert not status["stopped"]
