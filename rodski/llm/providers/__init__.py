"""LLM Providers — lazy imports to avoid requiring optional dependencies."""

__all__ = ['BaseProvider', 'ClaudeProvider', 'OpenAIProvider']

_LAZY_IMPORTS = {
    'BaseProvider': '.base',
    'ClaudeProvider': '.claude',
    'OpenAIProvider': '.openai',
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib
        mod = importlib.import_module(_LAZY_IMPORTS[name], __name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
