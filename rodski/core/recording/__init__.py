"""录屏模块 — lazy imports to avoid requiring playwright at import time."""

__all__ = ["Recorder", "recorder"]


def __getattr__(name):
    if name in ('Recorder', 'recorder'):
        from .recorder import Recorder, recorder
        if name == 'Recorder':
            return Recorder
        return recorder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
