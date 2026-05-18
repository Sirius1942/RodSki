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
    import ast
    from importlib.metadata import PackageNotFoundError, version
    from pathlib import Path
    try:
        from ..core.keyword_engine import KeywordEngine
        from ..core.driver_factory import DriverFactory
        from ..core.model_parser import VALID_LOCATOR_TYPES
        from ..core.xml_schema_validator import SCHEMA_FILES
    except ImportError:
        from core.keyword_engine import KeywordEngine
        from core.driver_factory import DriverFactory
        from core.model_parser import VALID_LOCATOR_TYPES
        from core.xml_schema_validator import SCHEMA_FILES

    def _load_version_from_file(path: Path):
        try:
            module = ast.parse(path.read_text(encoding="utf-8"))
        except OSError:
            return None
        for node in module.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
                continue
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
        return None

    framework_version = _load_version_from_file(Path(__file__).resolve().parents[1] / "__init__.py")
    try:
        if not framework_version:
            from rodski import __version__ as framework_version
    except (ImportError, AttributeError):
        framework_version = None
    if not framework_version:
        try:
            framework_version = version("rodski")
        except PackageNotFoundError:
            framework_version = "dev"

    capabilities = {
        "version": framework_version,
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
