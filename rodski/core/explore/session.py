"""探索会话管理模块

提供探索测试的会话状态管理、预算控制和去重功能。

核心类：
- ExploreSession: 会话状态数据结构
- ExploreSessionStore: 会话持久化（原子写入）
- BudgetGuard: 预算控制和去重检查
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple
import tempfile
import os


def _compute_action_hash(command: Dict[str, Any]) -> str:
    """计算命令指纹（用于去重）

    Args:
        command: 命令字典 {action, model, data}

    Returns:
        SHA256 哈希值（前 16 位）
    """
    identity = {
        "action": command.get("action", ""),
        "model": command.get("model", ""),
        "data": command.get("data", ""),
    }
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class ExploreSession:
    """探索会话状态

    Attributes:
        session_id: 会话唯一标识
        module_dir: 模块目录路径
        started_at: 会话开始时间（Unix 时间戳）
        budget: 预算配置 {steps, duration, tokens, cost_usd}
        history: 执行历史 [{command, result, timestamp}, ...]
        seen_action_hashes: 已执行的动作哈希集合（去重）
        budget_spent: 已消耗的预算 {steps, duration, tokens, cost_usd}
        status: 会话状态（running/stopped）
        stopped_reason: 停止原因（budget_steps/budget_duration/manual）
    """

    session_id: str
    module_dir: Path
    started_at: float
    budget: Dict[str, Any]
    history: List[Dict[str, Any]] = field(default_factory=list)
    seen_action_hashes: Set[str] = field(default_factory=set)
    budget_spent: Dict[str, float] = field(default_factory=lambda: {
        "steps": 0,
        "duration": 0.0,
        "tokens": 0,
        "cost_usd": 0.0,
    })
    status: str = "running"
    stopped_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于 JSON 持久化）"""
        return {
            "session_id": self.session_id,
            "module_dir": str(self.module_dir),
            "started_at": self.started_at,
            "budget": self.budget,
            "history": self.history,
            "seen_action_hashes": list(self.seen_action_hashes),
            "budget_spent": self.budget_spent,
            "status": self.status,
            "stopped_reason": self.stopped_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExploreSession:
        """从字典反序列化"""
        return cls(
            session_id=data["session_id"],
            module_dir=Path(data["module_dir"]),
            started_at=data["started_at"],
            budget=data["budget"],
            history=data.get("history", []),
            seen_action_hashes=set(data.get("seen_action_hashes", [])),
            budget_spent=data.get("budget_spent", {
                "steps": 0,
                "duration": 0.0,
                "tokens": 0,
                "cost_usd": 0.0,
            }),
            status=data.get("status", "running"),
            stopped_reason=data.get("stopped_reason", ""),
        )


class ExploreSessionStore:
    """探索会话持久化

    职责：
    - 会话状态保存到 JSON 文件
    - 原子写入（临时文件 + rename）
    - 会话列表、删除
    """

    def __init__(self, module_dir: Path):
        """初始化

        Args:
            module_dir: 测试模块目录
        """
        self.module_dir = Path(module_dir)
        self.session_dir = self.module_dir / "result" / "explore"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.session_dir / f"session_{session_id}.json"

    def save(self, session: ExploreSession) -> None:
        """保存会话（原子写入）

        Args:
            session: 会话对象
        """
        session_path = self._session_path(session.session_id)

        # 原子写入：临时文件 + rename
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=self.session_dir,
            prefix=f".session_{session.session_id}_",
            suffix=".tmp",
            delete=False,
            encoding='utf-8',
        ) as f:
            temp_path = Path(f.name)
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

        # 原子替换
        temp_path.replace(session_path)

    def load(self, session_id: str) -> Optional[ExploreSession]:
        """加载会话

        Args:
            session_id: 会话 ID

        Returns:
            会话对象，不存在返回 None
        """
        session_path = self._session_path(session_id)
        if not session_path.exists():
            return None

        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ExploreSession.from_dict(data)
        except Exception:
            return None

    def list_sessions(self) -> List[str]:
        """列出所有会话 ID

        Returns:
            会话 ID 列表
        """
        session_ids = []
        for path in self.session_dir.glob("session_*.json"):
            session_id = path.stem.replace("session_", "")
            session_ids.append(session_id)
        return sorted(session_ids)

    def delete(self, session_id: str) -> None:
        """删除会话及关联证据

        Args:
            session_id: 会话 ID
        """
        # 删除会话文件
        session_path = self._session_path(session_id)
        if session_path.exists():
            session_path.unlink()

        # 删除关联证据（截图）
        for screenshot in self.session_dir.glob(f"session_{session_id}_*.png"):
            screenshot.unlink()


class BudgetGuard:
    """预算控制和去重检查

    职责：
    - 检查预算是否耗尽（步数/时长/token/成本）
    - 检查命令是否重复
    - 记录已执行的动作
    """

    def __init__(self, session: ExploreSession):
        """初始化

        Args:
            session: 会话对象
        """
        self.session = session

    def check_budget(self) -> Tuple[bool, str]:
        """检查预算是否耗尽

        Returns:
            (stopped, reason):
                - (False, "") 表示预算充足
                - (True, "budget_steps") 表示步数耗尽
                - (True, "budget_duration") 表示时长耗尽
        """
        budget = self.session.budget
        spent = self.session.budget_spent

        # 检查步数
        max_steps = budget.get("steps")
        if max_steps is not None and spent["steps"] >= max_steps:
            return True, "budget_steps"

        # 检查时长
        max_duration = budget.get("duration")
        if max_duration is not None:
            current_duration = time.time() - self.session.started_at
            if current_duration >= max_duration:
                return True, "budget_duration"

        # 检查 token（由调用方在外部累积）
        max_tokens = budget.get("tokens")
        if max_tokens is not None and spent["tokens"] >= max_tokens:
            return True, "budget_tokens"

        # 检查成本（由调用方在外部累积）
        max_cost = budget.get("cost_usd")
        if max_cost is not None and spent["cost_usd"] >= max_cost:
            return True, "budget_cost"

        return False, ""

    def is_duplicate(self, command: Dict[str, Any]) -> bool:
        """检查命令是否重复

        Args:
            command: 命令字典 {action, model, data}

        Returns:
            True 表示重复
        """
        action_hash = _compute_action_hash(command)
        return action_hash in self.session.seen_action_hashes

    def record_action(self, command: Dict[str, Any]) -> None:
        """记录已执行的动作

        Args:
            command: 命令字典 {action, model, data}
        """
        action_hash = _compute_action_hash(command)
        self.session.seen_action_hashes.add(action_hash)
        self.session.budget_spent["steps"] += 1
        self.session.budget_spent["duration"] = time.time() - self.session.started_at

    def get_budget_status(self) -> Dict[str, Any]:
        """获取预算状态（用于 CLI 输出）

        Returns:
            预算状态字典
        """
        budget = self.session.budget
        spent = self.session.budget_spent
        stopped, reason = self.check_budget()

        return {
            "steps": {
                "used": int(spent["steps"]),
                "limit": budget.get("steps"),
                "remaining": max(0, budget.get("steps", 0) - spent["steps"]) if budget.get("steps") else None,
            },
            "duration": {
                "used": round(spent["duration"], 2),
                "limit": budget.get("duration"),
                "remaining": round(max(0, budget.get("duration", 0) - spent["duration"]), 2) if budget.get("duration") else None,
            },
            "tokens": {
                "used": int(spent["tokens"]),
                "limit": budget.get("tokens"),
                "remaining": max(0, budget.get("tokens", 0) - spent["tokens"]) if budget.get("tokens") else None,
            },
            "cost_usd": {
                "used": round(spent["cost_usd"], 4),
                "limit": budget.get("cost_usd"),
                "remaining": round(max(0, budget.get("cost_usd", 0) - spent["cost_usd"]), 4) if budget.get("cost_usd") else None,
            },
            "stopped": stopped,
            "stopped_reason": reason,
        }
