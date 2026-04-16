"""RodSki 驱动模块 — lazy imports to avoid requiring optional dependencies at import time

提供统一的驱动接口和多种平台实现：
- BaseDriver: 驱动基类接口
- PlaywrightDriver: Web 自动化驱动
- PywinautoDriver: Windows 桌面自动化驱动
- DesktopDriver: 跨平台桌面自动化驱动 (Windows/macOS)
- AppiumDriver: 移动端自动化驱动
- AndroidDriver: Android 平台驱动
- IOSDriver: iOS 平台驱动
"""
from .base_driver import BaseDriver

__all__ = [
    'BaseDriver',
    'PlaywrightDriver',
    'PywinautoDriver',
    'DesktopDriver',
    'AppiumDriver',
    'AndroidDriver',
    'IOSDriver',
]

_LAZY_IMPORTS = {
    'PlaywrightDriver': '.playwright_driver',
    'PywinautoDriver': '.pywinauto_driver',
    'DesktopDriver': '.desktop_driver',
    'AppiumDriver': '.appium_driver',
    'AndroidDriver': '.android_driver',
    'IOSDriver': '.ios_driver',
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib
        module = importlib.import_module(_LAZY_IMPORTS[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")