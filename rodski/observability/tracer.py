"""轻量 trace 实现 + @trace_span 装饰器"""
import functools
import logging
import threading
from typing import Optional

from .span import Span

logger = logging.getLogger("rodski.trace")


class Tracer:
    """全局 Tracer 单例

    提供 span 的创建、嵌套和生命周期管理。
    使用栈结构维护当前活跃的 span 链，支持自动嵌套。

    线程安全：使用 threading.Lock 保护内部状态。
    """
    _instance: Optional["Tracer"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._root_span: Optional[Span] = None
        self._span_stack: list[Span] = []
        self._trace_id: Optional[str] = None
        self._state_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "Tracer":
        """获取或创建全局 Tracer 单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def _reset_instance(cls) -> None:
        """重置单例（仅用于测试）"""
        with cls._lock:
            cls._instance = None

    def start_span(self, name: str, **attributes) -> Span:
        """开始一个新的 span

        如果栈中有活跃 span，新 span 自动成为其子 span。
        如果栈为空，新 span 成为根 span 并生成新 trace_id。

        Args:
            name: span 名称
            **attributes: span 属性

        Returns:
            新创建的 Span 对象
        """
        with self._state_lock:
            parent = self._span_stack[-1] if self._span_stack else None

            if parent is None:
                # 根 span：生成新 trace_id
                self._trace_id = Span.generate_trace_id()

            span = Span(
                name=name,
                trace_id=self._trace_id,
                span_id=Span.generate_id(),
                parent_id=parent.span_id if parent else None,
                attributes=dict(attributes),
            )

            if parent is not None:
                parent.children.append(span)
            else:
                self._root_span = span

            self._span_stack.append(span)
            logger.debug(f"span 开始: {name} (id={span.span_id})")
            return span

    def end_span(self, status: str = "ok") -> None:
        """结束当前活跃的 span

        Args:
            status: span 状态，"ok" 或 "error"
        """
        import time
        with self._state_lock:
            if not self._span_stack:
                logger.warning("end_span 调用时栈为空，忽略")
                return

            span = self._span_stack.pop()
            span.end_time = time.time()
            span.status = status
            logger.debug(
                f"span 结束: {span.name} (status={status}, "
                f"duration={span.duration:.3f}s)"
            )

    def get_current_span(self) -> Optional[Span]:
        """获取当前活跃的 span

        Returns:
            当前栈顶 span，栈为空则返回 None
        """
        with self._state_lock:
            return self._span_stack[-1] if self._span_stack else None

    def get_root_span(self) -> Optional[Span]:
        """获取根 span

        Returns:
            根 Span 对象，未开始 trace 则返回 None
        """
        with self._state_lock:
            return self._root_span

    def reset(self) -> None:
        """重置 tracer 状态（每次 run 前调用）"""
        with self._state_lock:
            self._root_span = None
            self._span_stack.clear()
            self._trace_id = None
            logger.debug("tracer 已重置")


def get_tracer() -> Tracer:
    """获取全局 Tracer 单例

    Returns:
        全局 Tracer 实例
    """
    return Tracer.get_instance()


def trace_span(name: str):
    """装饰器：自动创建/结束 span

    用法:
        @trace_span("keyword.click")
        def click(self, locator):
            ...

    Args:
        name: span 名称
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span = tracer.start_span(name)
            try:
                result = func(*args, **kwargs)
                tracer.end_span("ok")
                return result
            except Exception as e:
                span.attributes["error"] = str(e)
                span.attributes["error_type"] = type(e).__name__
                tracer.end_span("error")
                raise
        return wrapper
    return decorator
