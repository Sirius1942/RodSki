"""Core package — lazy imports to avoid heavy optional dependencies at import time"""

__all__ = [
    'KeywordEngine',
    'TaskExecutor',
    'ConfigManager',
    'Logger',
    'RodskiXmlValidator',
    'XmlSchemaValidationError',
    'DriverFactory',
]


def __getattr__(name):
    if name == 'KeywordEngine':
        from .keyword_engine import KeywordEngine
        return KeywordEngine
    if name == 'TaskExecutor':
        from .task_executor import TaskExecutor
        return TaskExecutor
    if name == 'ConfigManager':
        from .config_manager import ConfigManager
        return ConfigManager
    if name == 'Logger':
        from .logger import Logger
        return Logger
    if name == 'RodskiXmlValidator':
        from .xml_schema_validator import RodskiXmlValidator
        return RodskiXmlValidator
    if name == 'XmlSchemaValidationError':
        from .exceptions import XmlSchemaValidationError
        return XmlSchemaValidationError
    if name == 'DriverFactory':
        from .driver_factory import DriverFactory
        return DriverFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
