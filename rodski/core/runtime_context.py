"""统一运行时上下文 — 管理单个测试用例的执行状态"""
from typing import Any


class RuntimeContext:
    def __init__(self):
        self.history: list = []   # Return[-N] 访问
        self.named: dict = {}     # set/get 命名访问
        self.objects: dict = {}   # 预留，首版不实现

    def append_history(self, value: Any) -> None:
        self.history.append(value)

    def get_history(self, n: int) -> Any:
        if not self.history:
            return None
        try:
            return self.history[n]
        except IndexError:
            return None
