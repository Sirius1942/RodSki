"""运行时控制命令队列 — 暂停 / 插入 / 终止（步骤边界生效）

设计见 docs/核心设计约束.md §8.6–8.7。一般命令在当前 test_step 执行结束后于边界处理；
强制终止可立即抛出 ForceRunTermination。
"""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Optional

if TYPE_CHECKING:
    from core.ski_executor import SKIExecutor


class ControlCommandKind(Enum):
    PAUSE = "pause"
    RESUME = "resume"
    INSERT = "insert"
    TERMINATE = "terminate"
    FORCE_TERMINATE = "force_terminate"


@dataclass
class ControlCommand:
    kind: ControlCommandKind
    steps: Optional[List[Dict[str, str]]] = None
    temp_models: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None
    temp_tables: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None


class GracefulRunTermination(Exception):
    """在步骤边界收到正常终止命令，结束当前阶段循环。"""


class ForceRunTermination(Exception):
    """收到强制终止命令（可不等待当前步自然结束，由调用方在边界抛出）。"""


class BaseRuntimeControl:
    """无远程控制时的空实现。"""

    def wait_unpaused(self, timeout: Optional[float] = None) -> bool:
        return True

    def drain_at_boundary(self, executor: "SKIExecutor", dq: Deque[Dict[str, str]]) -> None:
        return


class RuntimeCommandQueue(BaseRuntimeControl):
    """线程安全队列；在步骤边界 drain。暂停时阻塞直至 resume。"""

    def __init__(self) -> None:
        self._q = queue.Queue()  # Queue[ControlCommand]
        self._unpaused = threading.Event()
        self._unpaused.set()

    def enqueue(self, cmd: ControlCommand) -> None:
        self._q.put(cmd)

    def pause(self) -> None:
        self.enqueue(ControlCommand(ControlCommandKind.PAUSE))

    def resume(self) -> None:
        self.enqueue(ControlCommand(ControlCommandKind.RESUME))

    def insert(
        self,
        steps: List[Dict[str, str]],
        *,
        temp_models: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None,
        temp_tables: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
    ) -> None:
        self.enqueue(
            ControlCommand(
                ControlCommandKind.INSERT,
                steps=steps,
                temp_models=temp_models,
                temp_tables=temp_tables,
            )
        )

    def terminate(self, *, force: bool = False) -> None:
        kind = ControlCommandKind.FORCE_TERMINATE if force else ControlCommandKind.TERMINATE
        self.enqueue(ControlCommand(kind))

    def wait_unpaused(self, timeout: Optional[float] = None) -> bool:
        return self._unpaused.wait(timeout=timeout)

    def _apply_pause_resume(self, cmd: ControlCommand) -> None:
        if cmd.kind == ControlCommandKind.PAUSE:
            self._unpaused.clear()
        elif cmd.kind == ControlCommandKind.RESUME:
            self._unpaused.set()

    def drain_at_boundary(self, executor: "SKIExecutor", dq: Deque[Dict[str, str]]) -> None:
        while True:
            try:
                cmd = self._q.get_nowait()
            except queue.Empty:
                break
            if cmd.kind == ControlCommandKind.PAUSE:
                self._apply_pause_resume(cmd)
            elif cmd.kind == ControlCommandKind.RESUME:
                self._apply_pause_resume(cmd)
            elif cmd.kind == ControlCommandKind.INSERT:
                if cmd.steps:
                    executor.apply_insert_resources(cmd.temp_models, cmd.temp_tables)
                    dq.extendleft(reversed(cmd.steps))
            elif cmd.kind == ControlCommandKind.TERMINATE:
                raise GracefulRunTermination()
            elif cmd.kind == ControlCommandKind.FORCE_TERMINATE:
                raise ForceRunTermination("runtime force_terminate")
