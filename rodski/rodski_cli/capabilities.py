"""rodski capabilities 子命令 — 输出 JSON 格式的框架能力清单。

供 rodski-agent 等外部工具在运行时动态获取 rodski 支持的关键字、
定位器类型、驱动类型等约束信息，实现版本协商和动态约束校验。
"""
import json
import sys


def setup_parser(subparsers):
    parser = subparsers.add_parser(
        "capabilities",
        help="输出 rodski 框架能力清单（JSON 格式）",
    )
    parser.set_defaults(func=handle)


def handle(args):
    """输出 JSON 格式的 rodski 能力清单。"""
    from rodski import __version__
    from rodski.core.keyword_engine import KeywordEngine
    from rodski.core.driver_factory import DriverFactory
    from rodski.core.model_parser import VALID_LOCATOR_TYPES
    from rodski.core.xml_schema_validator import SCHEMA_FILES

    capabilities = {
        "version": __version__,
        "supported_keywords": list(KeywordEngine.SUPPORTED),
        "compat_keywords": ["check"],
        "locator_types": list(VALID_LOCATOR_TYPES),
        "driver_types": list(DriverFactory.SUPPORTED_DRIVER_TYPES),
        "case_phases": ["pre_process", "test_case", "post_process"],
        "schema_types": list(SCHEMA_FILES.keys()),
        "special_values": ["BLANK", "NULL", "NONE"],
        "required_dirs": ["case", "model", "data"],
        "optional_dirs": ["fun", "result"],
        "component_types": ["界面", "接口", "数据库"],
        "execute_values": ["是", "否"],
    }

    print(json.dumps(capabilities, ensure_ascii=False, indent=2))
    return 0
