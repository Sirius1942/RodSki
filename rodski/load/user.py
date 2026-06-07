"""RodskiLoadUser — Locust VU 基类。
LoadExecutor 动态子类化，注入 host / wait_time / case_registry / @task 方法。
每个并发 VU 是该类的一个独立 greenlet 实例。
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import SharedLoadContext

# 模块级导入，使 @patch 能拦截；try/except 兼容直接以 rodski/ 为 sys.path 的运行模式。
try:
    from ..drivers.load_driver import LoadDriver
    from ..core.keyword_engine import KeywordEngine
except ImportError:
    from drivers.load_driver import LoadDriver  # type: ignore[no-redef]
    from core.keyword_engine import KeywordEngine  # type: ignore[no-redef]


class RodskiLoadUser:
    """
    基类，由 LoadExecutor 动态子类化。abstract = True 防止 Locust 直接实例化。
    实际使用时，LoadExecutor 会用 type() 创建继承此类且继承 FastHttpUser 的子类。
    """
    abstract = True

    # 以下属性由 LoadExecutor 在子类中注入：
    # host: str
    # wait_time: callable
    # _shared_ctx: SharedLoadContext

    def on_start(self):
        """每个 VU greenlet 启动时调用，初始化独立的 LoadDriver + KeywordEngine。"""
        self._load_driver = LoadDriver(
            locust_client=self.client,
            host=getattr(self, 'host', ''),
        )

        ctx = getattr(self, '_shared_ctx', None)

        # KeywordEngine 使用 model_parser / data_manager / global_vars 属性
        # 在压测模式下，我们传入轻量代理对象以复用 context 中的注册表数据。
        model_parser = None
        data_manager = None
        global_vars: dict = {}

        if ctx is not None:
            model_parser = _ModelRegistryProxy(ctx.model_registry)
            data_manager = ctx.data_store
            global_vars = _flatten_global_values(ctx.global_values)

        self._keyword_engine = KeywordEngine(
            driver=self._load_driver,
            model_parser=model_parser,
            data_manager=data_manager,
            global_vars=global_vars,
        )
        self._returns = []  # 本次迭代的 Return 链（每次 @task 重置）

    def _execute_case(self, case_id: str):
        """执行一个 case 的 pre_process + test_case（跳过 post_process）。"""
        ctx = getattr(self, '_shared_ctx', None)
        if ctx is None:
            return
        case = ctx.case_registry.get(case_id)
        if case is None:
            raise ValueError(f"case_id '{case_id}' 不在 case_registry 中")

        self._returns = []  # 每次迭代重置 Return 链
        steps = list(case.get("pre_process", []) + case.get("test_case", []))
        for step in steps:
            result = self._execute_step(step)
            if result is not None:
                self._returns.append(result)

    def _execute_step(self, step: dict):
        """将 case step dict 映射到 keyword_engine.execute()，返回最新历史项（如有）。"""
        action = step.get("action", "")
        model = step.get("model", "")
        data = step.get("data", "")
        if not action:
            return None

        if action.lower() == "set":
            params = {"var_name": model, "value": data}
        else:
            params = {"model": model, "data": data}

        history_before = len(self._keyword_engine._context.history)
        self._keyword_engine.execute(action, params)
        history_after = self._keyword_engine._context.history
        if len(history_after) > history_before:
            return history_after[-1]
        return None


def _flatten_global_values(global_values: dict) -> dict:
    """将 {group: {var: value}} 格式展平为 {var: value}，供 KeywordEngine 使用。
    同时保留原始分组结构，以 group 名为 key 存入，以支持 Mobile.* 等嵌套访问。
    """
    flat: dict = {}
    for group_name, group_vars in (global_values or {}).items():
        flat[group_name] = group_vars
        if isinstance(group_vars, dict):
            flat.update(group_vars)
    return flat


class _ModelRegistryProxy:
    """将 model_registry dict 包装为 ModelParser 鸭子类型代理。
    仅实现 KeywordEngine._kw_send / _kw_verify 所需的接口。
    """

    def __init__(self, registry: dict):
        self._registry = registry
        # 兼容 KeywordEngine 对 model_parser.models 的直接访问
        self.models = registry

    def get_model(self, model_name: str):
        return self._registry.get(model_name)

    def get_model_type(self, model_name: str) -> str:
        model = self._registry.get(model_name)
        if not model:
            return "ui"
        return model.get("__model_type__", "ui")

    def get_model_driver_type(self, model_name: str) -> str:
        model = self._registry.get(model_name)
        if not model:
            return "web"
        driver_type = (model.get("__driver_type__") or "").strip()
        if driver_type:
            return driver_type
        model_type = model.get("__model_type__", "ui")
        if model_type == "interface":
            return "interface"
        return "web"

    def get_element(self, locator: str):
        if "." not in locator:
            return None
        model_name, element_name = locator.split(".", 1)
        model = self._registry.get(model_name)
        if not model:
            return None
        element = model.get(element_name)
        if not element:
            return None
        return {
            "locator_type": element.get("locator_type", ""),
            "locator_value": element.get("locator_value", ""),
            "model_type": element.get("model_type", self.get_model_type(model_name)),
            "element_type": element.get("element_type", ""),
            "locations": element.get("locations", []),
        }

    def get_auto_capture(self, model_name: str, trigger: str) -> list:
        model = self._registry.get(model_name, {})
        return model.get(f"__auto_capture_{trigger}__") or []
