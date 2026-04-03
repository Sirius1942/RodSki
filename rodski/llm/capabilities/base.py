"""Capability 抽象基类"""
from abc import ABC, abstractmethod


class BaseCapability(ABC):
    """LLM 能力抽象基类"""

    def __init__(self, client):
        self.client = client

    @abstractmethod
    def execute(self, *args, **kwargs):
        """执行能力"""
        pass
