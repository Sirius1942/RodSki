"""Reviewers — lazy imports to avoid requiring optional dependencies."""

__all__ = ['LLMReviewer']


def __getattr__(name):
    if name == 'LLMReviewer':
        from .llm_reviewer import LLMReviewer
        return LLMReviewer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
