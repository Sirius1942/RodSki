"""内置函数注册表

提供内置函数的注册和查找机制。
run 关键字优先查 BUILTIN_REGISTRY，命中则调用内置函数，
未命中则走原有 fun/ 脚本逻辑。

用法:
    register_builtin("mock_route", "builtin_ops.network_ops", "mock_route")
    fn = get_builtin("mock_route")
    if fn:
        result = fn(url_pattern="/api/users", status=200)
"""
import importlib
import logging
from typing import Callable, Optional

logger = logging.getLogger("rodski.builtins")

# 内置函数注册表
# 格式：函数名 -> (模块路径, 函数名)
BUILTIN_REGISTRY: dict[str, tuple[str, str]] = {}


def register_builtin(name: str, module: str, func_name: str) -> None:
    """注册内置函数

    Args:
        name: 注册名称（用户在 run 关键字中引用的名称）
        module: 模块路径（如 "builtins.network_ops"）
        func_name: 模块中的函数名
    """
    BUILTIN_REGISTRY[name] = (module, func_name)
    logger.debug(f"注册内置函数: {name} -> {module}.{func_name}")


def get_builtin(name: str) -> Optional[Callable]:
    """查找并返回内置函数

    延迟导入：只在实际调用时导入模块，避免启动时加载不必要的依赖。

    模块路径兼容两种运行模式：
    1. legacy 模式：`rodski/` 目录本身在 sys.path 上（如 `cd rodski && python3 ski_run.py`），
       此时 "builtin_ops.xxx" 是顶层绝对导入路径，可直接解析
    2. 标准安装模式：通过 pip / 可编辑安装的 `rodski` 包（真实 `rodski` CLI 命令走此路径），
       此时顶层包名为 `rodski`，"builtin_ops.xxx" 需要改写为 "rodski.builtin_ops.xxx" 才能解析

    先尝试原始路径（兼容 legacy），失败后再尝试加 "rodski." 前缀。

    Args:
        name: 函数名称

    Returns:
        可调用函数对象，未找到返回 None
    """
    if name not in BUILTIN_REGISTRY:
        return None

    module_path, func_name = BUILTIN_REGISTRY[name]
    module = None
    last_error: Optional[Exception] = None

    for candidate in (module_path, f"rodski.{module_path}"):
        try:
            module = importlib.import_module(candidate)
            break
        except ImportError as e:
            last_error = e
            continue

    if module is None:
        logger.warning(f"内置函数模块导入失败: {module_path} - {last_error}")
        return None

    func = getattr(module, func_name, None)
    if func is None:
        logger.warning(f"内置函数模块 {module.__name__} 中未找到 {func_name}")
        return None
    return func


def list_builtins() -> list[str]:
    """列出所有已注册的内置函数名

    Returns:
        已注册的函数名列表
    """
    return list(BUILTIN_REGISTRY.keys())


# ── 自动注册 network_ops 中的函数 ─────────────────────────────
register_builtin("mock_route", "builtin_ops.network_ops", "mock_route")
register_builtin("wait_for_response", "builtin_ops.network_ops", "wait_for_response")
register_builtin("clear_routes", "builtin_ops.network_ops", "clear_routes")

# ── 自动注册 coverage_ops 中的函数 ─────────────────────────────
register_builtin("start_js_coverage", "builtin_ops.coverage_ops", "start_js_coverage")
register_builtin("stop_js_coverage", "builtin_ops.coverage_ops", "stop_js_coverage")
