"""执行队列 - 多层级执行队列管理器

支持功能：
- 记录所有层级的执行动作（Case/Phase/BusinessCall/Flow/Node/Step/DriverAction）
- 跟踪每个动作的状态（pending/running/success/failed/skipped）
- 支持断点设置和查询
- 支持执行上下文关联
"""
import logging
from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("rodski")


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionLevel(str, Enum):
    """执行层级枚举"""
    CASE = "case"
    PHASE = "phase"
    BUSINESS_CALL = "business_call"
    FLOW = "flow"
    NODE = "node"
    SCENARIO = "scenario"
    STEP = "step"
    DRIVER_ACTION = "driver_action"


@dataclass
class ExecutionAction:
    """执行动作记录"""
    seq: int  # 全局序列号
    level: ExecutionLevel
    name: str  # 动作名称（如 case_id, step_id, action_name）
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None

    # 上下文关联
    context: Dict[str, Any] = field(default_factory=dict)

    # 驱动动作特有字段
    action: Optional[str] = None  # find_element, click, fill 等
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志输出）"""
        data = {
            "seq": self.seq,
            "level": self.level.value,
            "name": self.name,
            "status": self.status.value,
        }
        if self.start_time:
            data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        if self.duration_ms is not None:
            data["duration_ms"] = self.duration_ms
        if self.error:
            data["error"] = self.error
        if self.context:
            data["context"] = self.context
        if self.action:
            data["action"] = self.action
        if self.params:
            data["params"] = self.params
        if self.result:
            data["result"] = str(self.result)
        return data


class ExecutionQueue:
    """执行队列管理器"""

    def __init__(self):
        self.actions: List[ExecutionAction] = []
        self._seq_counter = 0
        self._current_context: Dict[str, Any] = {}

    def add_action(
        self,
        level: ExecutionLevel,
        name: str,
        action: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionAction:
        """添加一个执行动作到队列"""
        self._seq_counter += 1
        exec_action = ExecutionAction(
            seq=self._seq_counter,
            level=level,
            name=name,
            action=action,
            params=params,
            context={**self._current_context, **(context or {})},
        )
        self.actions.append(exec_action)
        logger.debug(f"[ExecutionQueue] Add action #{self._seq_counter}: {level.value} {name}")
        return exec_action

    def start_action(self, seq: int) -> None:
        """标记动作开始执行"""
        action = self.get_action(seq)
        if action:
            action.status = ExecutionStatus.RUNNING
            action.start_time = datetime.now()
            logger.debug(f"[ExecutionQueue] Start action #{seq}: {action.level.value} {action.name}")

    def complete_action(self, seq: int, status: ExecutionStatus, error: Optional[str] = None, result: Optional[Any] = None) -> None:
        """标记动作完成"""
        action = self.get_action(seq)
        if action:
            action.status = status
            action.end_time = datetime.now()
            action.error = error
            action.result = result
            if action.start_time:
                delta = action.end_time - action.start_time
                action.duration_ms = int(delta.total_seconds() * 1000)
            status_icon = "✅" if status == ExecutionStatus.SUCCESS else "❌" if status == ExecutionStatus.FAILED else "⏹️"
            logger.debug(f"[ExecutionQueue] Complete action #{seq}: {action.level.value} {action.name} {status_icon} ({action.duration_ms}ms)")

    def skip_action(self, seq: int, reason: str = "") -> None:
        """标记动作跳过"""
        action = self.get_action(seq)
        if action:
            action.status = ExecutionStatus.SKIPPED
            action.error = reason or "Skipped"
            logger.debug(f"[ExecutionQueue] Skip action #{seq}: {action.level.value} {action.name}")

    def get_action(self, seq: int) -> Optional[ExecutionAction]:
        """根据序列号获取动作"""
        for action in self.actions:
            if action.seq == seq:
                return action
        return None

    def get_current_action(self) -> Optional[ExecutionAction]:
        """获取当前正在执行的动作（最后一个 RUNNING 状态）"""
        for action in reversed(self.actions):
            if action.status == ExecutionStatus.RUNNING:
                return action
        return None

    def get_actions_by_level(self, level: ExecutionLevel) -> List[ExecutionAction]:
        """获取指定层级的所有动作"""
        return [a for a in self.actions if a.level == level]

    def get_actions_by_status(self, status: ExecutionStatus) -> List[ExecutionAction]:
        """获取指定状态的所有动作"""
        return [a for a in self.actions if a.status == status]

    def update_context(self, **kwargs) -> None:
        """更新当前上下文（影响后续添加的所有动作）"""
        self._current_context.update(kwargs)

    def clear_context_key(self, key: str) -> None:
        """清除上下文中的某个键"""
        self._current_context.pop(key, None)

    def get_summary(self) -> Dict[str, Any]:
        """获取执行队列摘要"""
        total = len(self.actions)
        by_status = {
            "pending": len(self.get_actions_by_status(ExecutionStatus.PENDING)),
            "running": len(self.get_actions_by_status(ExecutionStatus.RUNNING)),
            "success": len(self.get_actions_by_status(ExecutionStatus.SUCCESS)),
            "failed": len(self.get_actions_by_status(ExecutionStatus.FAILED)),
            "skipped": len(self.get_actions_by_status(ExecutionStatus.SKIPPED)),
        }
        by_level = {}
        for level in ExecutionLevel:
            by_level[level.value] = len(self.get_actions_by_level(level))

        return {
            "total": total,
            "by_status": by_status,
            "by_level": by_level,
            "current_seq": self._seq_counter,
        }

    def to_text(self, max_lines: int = 50) -> str:
        """生成文本格式的队列内容（用于 CLI 显示）"""
        lines = ["Execution Queue:\n"]
        summary = self.get_summary()
        lines.append(f"Total Actions: {summary['total']}\n")
        lines.append(f"Status: ✅ {summary['by_status']['success']} | "
                    f"❌ {summary['by_status']['failed']} | "
                    f"⏳ {summary['by_status']['running']} | "
                    f"⏹️ {summary['by_status']['skipped']} | "
                    f"⏸️ {summary['by_status']['pending']}\n\n")

        # 显示最近的动作
        recent_actions = self.actions[-max_lines:] if len(self.actions) > max_lines else self.actions
        for action in recent_actions:
            status_icon = {
                ExecutionStatus.PENDING: "⏸️",
                ExecutionStatus.RUNNING: "⏳",
                ExecutionStatus.SUCCESS: "✅",
                ExecutionStatus.FAILED: "❌",
                ExecutionStatus.SKIPPED: "⏹️",
            }.get(action.status, "")

            duration = f" - {action.duration_ms}ms" if action.duration_ms else ""
            context_info = ""
            if action.context:
                if "step" in action.context:
                    context_info = f" (Step: {action.context['step']})"
                elif "node" in action.context:
                    context_info = f" (Node: {action.context['node']})"

            lines.append(f"  {status_icon} [{action.seq}] {action.level.value}: {action.name}{duration}{context_info}\n")

        if len(self.actions) > max_lines:
            lines.append(f"\n... ({len(self.actions) - max_lines} more actions)\n")

        return "".join(lines)
