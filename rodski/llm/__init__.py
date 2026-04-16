"""RodSki LLM 统一模块 — lazy imports to avoid requiring optional dependencies."""

__all__ = ['LLMClient']


def __getattr__(name):
    if name == 'LLMClient':
        from .client import LLMClient
        return LLMClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
