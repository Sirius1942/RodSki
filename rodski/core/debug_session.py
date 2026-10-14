"""调试会话管理器 - 整合执行队列、断点管理、对象池和交互控制

这是 REQ-012 调试功能的核心控制器，管理：
- 执行队列（多层级动作记录）
- 断点管理（触发检测和暂停控制）
- 对象池（运行时对象生命周期）
- 交互循环（暂停时的用户交互）
- 上下文查看（Return 栈、GlobalValue、当前行）
"""
import logging
import sys
from typing import Any, Dict, Optional, Literal, Callable
from pathlib import Path

from .execution_queue import ExecutionQueue, ExecutionLevel, ExecutionStatus
from .breakpoint_manager import BreakpointManager, Breakpoint
from .object_pool import ObjectPool

logger = logging.getLogger("rodski")


class DebugSession:
    """调试会话管理器（单例）"""

    _instance: Optional["DebugSession"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 核心组件
        self.execution_queue = ExecutionQueue()
        self.breakpoint_manager = BreakpointManager()
        self.object_pool = ObjectPool()

        # 调试状态
        self.enabled = False  # 是否启用调试模式
        self.paused = False  # 是否暂停中
        self.step_mode = False  # 是否单步模式
        self.should_quit = False  # 是否应该退出

        # 部分执行控制
        self.start_from: Optional[int] = None  # 从第 N 步开始
        self.stop_at: Optional[int] = None  # 在第 N 步停止

        # 上下文（用于 debug context 命令）
        self.runtime_context: Optional[Any] = None  # RuntimeContext 实例
        self.current_case_id: Optional[str] = None
        self.current_step_num: Optional[int] = None
        self.current_scenario_id: Optional[str] = None
        self.current_flow_id: Optional[str] = None
        self.current_node_name: Optional[str] = None
        self.current_data_row: Optional[Dict[str, Any]] = None

        # 步骤快照（用于调试时查看步骤状态）
        self.step_snapshots: Dict[int, Dict[str, Any]] = {}

        # 日志输出
        self.log_file: Optional[Path] = None

    @classmethod
    def get_instance(cls) -> "DebugSession":
        """获取调试会话单例"""
        return cls()

    def enable(
        self,
        breakpoints: Optional[list] = None,
        start_from: Optional[int] = None,
        stop_at: Optional[int] = None,
        step_mode: bool = False,
    ) -> None:
        """启用调试模式"""
        self.enabled = True
        self.step_mode = step_mode
        self.start_from = start_from
        self.stop_at = stop_at

        if breakpoints:
            for bp_str in breakpoints:
                self.breakpoint_manager.add_from_string(bp_str)

        logger.info(f"[DebugSession] Enabled (breakpoints: {len(self.breakpoint_manager.breakpoints)}, "
                   f"start_from: {start_from}, stop_at: {stop_at}, step_mode: {step_mode})")

    def should_skip_step(self, step_num: int) -> bool:
        """判断是否应该跳过某个步骤（基于 start_from）"""
        if self.start_from is not None and step_num < self.start_from:
            return True
        return False

    def should_stop_step(self, step_num: int) -> bool:
        """判断是否应该在某个步骤停止（基于 stop_at）"""
        if self.stop_at is not None and step_num > self.stop_at:
            return True
        return False

    def save_step_snapshot(self, step_num: int, snapshot: Dict[str, Any]) -> None:
        """保存步骤快照（用于调试时查看）

        Args:
            step_num: 步骤编号
            snapshot: 快照数据（包含 action, model, data, 返回值等）
        """
        self.step_snapshots[step_num] = snapshot
        logger.debug(f"[DebugSession] Saved snapshot for step {step_num}")

    def get_step_snapshot(self, step_num: int) -> Optional[Dict[str, Any]]:
        """获取步骤快照

        Args:
            step_num: 步骤编号

        Returns:
            快照数据，如果不存在则返回 None
        """
        return self.step_snapshots.get(step_num)

    def clear_snapshots(self) -> None:
        """清空所有步骤快照"""
        self.step_snapshots.clear()
        logger.debug("[DebugSession] Cleared all step snapshots")

    def check_breakpoint(self, **kwargs) -> bool:
        """检查是否命中断点

        Returns:
            True 如果命中断点且需要暂停
        """
        if not self.enabled:
            return False

        # 检查 stop_at
        if "step_num" in kwargs and self.should_stop_step(kwargs["step_num"]):
            logger.info(f"[DebugSession] Reached stop_at: step {kwargs['step_num']}")
            self.paused = True
            return True

        # 检查断点
        hit_bp = self.breakpoint_manager.check_hit(**kwargs)
        if hit_bp:
            self.paused = True
            return True

        # 单步模式
        if self.step_mode:
            self.paused = True
            return True

        return False

    def pause(self, reason: str = "Breakpoint") -> None:
        """暂停执行并进入交互循环"""
        self.paused = True
        current = self.execution_queue.get_current_action()

        print(f"\n{'='*60}")
        print(f"🔴 PAUSED: {reason}")
        if current:
            print(f"Level: {current.level.value}")
            print(f"Name: {current.name}")
            if current.context:
                if "case" in current.context:
                    print(f"Case: {current.context['case']}")
                if "step" in current.context:
                    print(f"Step: {current.context['step']}")
                if "node" in current.context:
                    print(f"Node: {current.context['node']}")
        print(f"{'='*60}")
        print("Commands: (c)ontinue | (s)kip | (q)uit | (h)elp")
        print("Debug commands: queue | objects | context | status")
        print(f"{'='*60}\n")

    def interact(self) -> Literal["continue", "skip", "quit"]:
        """交互循环（暂停时）

        Returns:
            用户命令：continue | skip | quit
        """
        while self.paused:
            try:
                command = input("> ").strip().lower()

                if command in ["c", "continue"]:
                    self.paused = False
                    return "continue"

                elif command in ["s", "skip"]:
                    self.paused = False
                    return "skip"

                elif command in ["q", "quit"]:
                    self.paused = False
                    self.should_quit = True
                    return "quit"

                elif command == "queue":
                    print(self.execution_queue.to_text())

                elif command == "objects":
                    print(self.object_pool.to_text())

                elif command == "context":
                    print(self.format_context())

                elif command == "status":
                    print(self.format_status())

                elif command in ["h", "help"]:
                    print("""
Debug Commands:
  c, continue    - Continue execution
  s, skip        - Skip current step
  q, quit        - Quit execution
  queue          - Show execution queue
  objects        - Show runtime objects
  context        - Show execution context (Return, GlobalValue, ROW)
  status         - Show current status
  h, help        - Show this help
""")
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'h' for help")

            except (EOFError, KeyboardInterrupt):
                print("\nInterrupted, continuing...")
                self.paused = False
                return "continue"

        return "continue"

    def format_context(self) -> str:
        """格式化上下文信息"""
        lines = ["Execution Context:\n"]

        if self.current_case_id:
            lines.append(f"  Case: {self.current_case_id}\n")

        if self.current_step_num:
            lines.append(f"  Step: {self.current_step_num}\n")

        if self.current_scenario_id:
            lines.append(f"  Scenario: {self.current_scenario_id}\n")

        if self.current_flow_id:
            lines.append(f"  Flow: {self.current_flow_id}\n")

        if self.current_node_name:
            lines.append(f"  Node: {self.current_node_name}\n")

        # Return 栈
        if self.runtime_context and hasattr(self.runtime_context, "history"):
            lines.append("\nReturn Stack:\n")
            history = self.runtime_context.history
            if history:
                for i in range(min(5, len(history))):
                    idx = -(i + 1)
                    value = history[idx]
                    lines.append(f"  ${{Return[{idx}]}} = {repr(value)}\n")
            else:
                lines.append("  (empty)\n")

        # 当前行数据
        if self.current_data_row:
            lines.append("\nRow Variables:\n")
            for key, value in self.current_data_row.items():
                lines.append(f"  ${{ROW.{key}}} = {repr(value)}\n")

        return "".join(lines)

    def format_status(self) -> str:
        """格式化当前状态"""
        lines = ["Debug Session Status:\n"]
        lines.append(f"  Enabled: {self.enabled}\n")
        lines.append(f"  Paused: {self.paused}\n")
        lines.append(f"  Step Mode: {self.step_mode}\n")

        if self.start_from:
            lines.append(f"  Start From: step {self.start_from}\n")
        if self.stop_at:
            lines.append(f"  Stop At: step {self.stop_at}\n")

        # 断点
        bps = self.breakpoint_manager.list_breakpoints()
        lines.append(f"\nBreakpoints: {len(bps)}\n")
        for bp in bps:
            lines.append(f"  - {bp}\n")

        # 执行队列摘要
        summary = self.execution_queue.get_summary()
        lines.append(f"\nExecution Queue:\n")
        lines.append(f"  Total: {summary['total']}\n")
        lines.append(f"  Success: {summary['by_status']['success']}\n")
        lines.append(f"  Failed: {summary['by_status']['failed']}\n")
        lines.append(f"  Running: {summary['by_status']['running']}\n")

        # 对象池摘要
        obj_summary = self.object_pool.get_summary()
        lines.append(f"\nRuntime Objects:\n")
        lines.append(f"  Total: {obj_summary['total']}\n")
        lines.append(f"  Alive: {obj_summary['alive']}\n")

        return "".join(lines)

    def cleanup(self) -> None:
        """清理调试会话"""
        # 关闭所有对象
        closed = self.object_pool.close_all()
        if closed > 0:
            logger.info(f"[DebugSession] Closed {closed} objects")

        # 重置状态（保留队列和日志用于事后分析）
        self.paused = False
        self.should_quit = False


# 全局快捷访问函数
def get_debug_session() -> DebugSession:
    """获取全局调试会话"""
    return DebugSession.get_instance()
