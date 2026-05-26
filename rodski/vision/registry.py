"""PerceptionRegistry — perception backend 的运行时发现与选择。

通过 Python ``importlib.metadata.entry_points`` 机制发现所有已安装
的 perception backend。rodski 核心不硬编码任何 backend 实现路径，
只要 backend 项目在 ``pyproject.toml`` 中正确注册 entry_point：

.. code-block:: toml

    # rodski-perception/pyproject.toml
    [project.entry-points."rodski.perception_backends"]
    local = "rodski_perception.backend:LocalPerceptionBackend"

rodski 即可在不修改源码的前提下发现并使用该 backend。

设计参考：``.pb/specs/v7.1.0-perception-design.md`` §4.3、
         ``rodski/docs/CORE_DESIGN_CONSTRAINTS.md`` §2.6.3 / §2.6.4
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Type

from .perception_interface import (
    PerceptionBackend,
    PerceptionUnavailableError,
)

logger = logging.getLogger(__name__)

#: entry_points group 名称。第三方 backend 项目必须使用此 group。
ENTRY_POINT_GROUP: str = "rodski.perception_backends"

#: 当用户未指定 backend 时的自动 fallback 顺序。
DEFAULT_FALLBACK_ORDER: tuple = ("local", "remote")


class PerceptionRegistry:
    """perception backend 的发现与实例化中心。

    主要 API：

    - :py:meth:`discover` — 扫描所有 entry_points，返回 ``{name: class}``
      字典；首次调用后结果会缓存在类属性 ``_cache``。
    - :py:meth:`get_backend` — 根据配置（``perception_backend`` /
      环境变量 ``RODSKI_PERCEPTION_BACKEND``）实例化一个可用 backend；
      未发现任何 backend 时抛 :py:class:`PerceptionUnavailableError`。
    - :py:meth:`reset` — 清空缓存，仅用于测试。
    - :py:meth:`register` — 测试用 hook，直接往缓存中注入 backend 类。
    """

    #: 缓存：``{backend_name: backend_class}``。``None`` 表示尚未 discover。
    _cache: Optional[Dict[str, Type[PerceptionBackend]]] = None

    # ------------------------------------------------------------------
    # 发现
    # ------------------------------------------------------------------

    @classmethod
    def discover(cls) -> Dict[str, Type[PerceptionBackend]]:
        """扫描 entry_points，返回所有注册的 backend 类。

        单个 entry_point 加载失败（导入异常、依赖缺失等）会被记录为
        warning，但不会影响其他 backend 的发现。

        多次调用返回缓存结果；测试中调用 :py:meth:`reset` 后会重新扫描。
        """
        if cls._cache is not None:
            return cls._cache

        backends: Dict[str, Type[PerceptionBackend]] = {}

        try:
            from importlib.metadata import entry_points
        except ImportError:  # pragma: no cover - python < 3.8
            logger.warning(
                "importlib.metadata.entry_points 不可用 (Python < 3.8)，"
                "无法发现 perception backend"
            )
            cls._cache = backends
            return backends

        try:
            # Python 3.10+: entry_points(group=...) 返回 EntryPoints
            # Python 3.8/3.9: entry_points() 返回 {group: tuple(...)}
            try:
                eps = entry_points(group=ENTRY_POINT_GROUP)
            except TypeError:
                all_eps = entry_points()
                eps = all_eps.get(ENTRY_POINT_GROUP, ())
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "扫描 entry_points group=%r 失败：%s",
                ENTRY_POINT_GROUP, exc,
            )
            cls._cache = backends
            return backends

        for ep in eps:
            try:
                backend_cls = ep.load()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "perception backend %r 加载失败（已跳过）：%s",
                    ep.name, exc,
                )
                continue

            if not isinstance(backend_cls, type) or not issubclass(
                backend_cls, PerceptionBackend
            ):
                logger.warning(
                    "entry_point %r 指向的对象 %r 不是 PerceptionBackend "
                    "的子类，已跳过",
                    ep.name, backend_cls,
                )
                continue

            backends[ep.name] = backend_cls
            logger.debug(
                "发现 perception backend：%s -> %s.%s",
                ep.name, backend_cls.__module__, backend_cls.__name__,
            )

        cls._cache = backends
        return backends

    # ------------------------------------------------------------------
    # 选择 & 实例化
    # ------------------------------------------------------------------

    @classmethod
    def get_backend(
        cls,
        config: Optional[Dict[str, Any]] = None,
    ) -> PerceptionBackend:
        """根据配置实例化一个可用的 backend。

        Parameters
        ----------
        config:
            合并了 globalvalue.xml / 用例 ``set`` 注入的配置字典。
            读取的键：

            - ``perception_backend``: 显式指定 backend 名（``"local"`` /
              ``"remote"``）。若指定的 backend 不存在则抛
              :py:class:`PerceptionUnavailableError`。
            - 其他键作为 ``**kwargs`` 透传给 backend ``__init__``。

            ``None`` 视为空字典。

            优先级（从高到低）：
                1. ``config["perception_backend"]``
                2. 环境变量 ``RODSKI_PERCEPTION_BACKEND``
                3. ``DEFAULT_FALLBACK_ORDER``（local → remote）

        Returns
        -------
        实例化好的 backend，已通过 ``is_available()`` 检查。

        Raises
        ------
        PerceptionUnavailableError:
            未发现任何 backend；或指定的 backend 不存在；
            或所有可用 backend 的 ``is_available()`` 全部返回 ``False``。
        """
        config = dict(config or {})
        backends = cls.discover()

        # 1. 用户显式指定
        preferred = config.pop("perception_backend", None) or os.getenv(
            "RODSKI_PERCEPTION_BACKEND"
        )

        if not backends:
            raise PerceptionUnavailableError()

        if preferred:
            if preferred not in backends:
                available = sorted(backends.keys())
                raise PerceptionUnavailableError(
                    f"指定的 perception backend '{preferred}' 未安装。\n"
                    f"  当前可用：{available}\n"
                    f"  {PerceptionUnavailableError.DEFAULT_HINT}"
                )
            instance = cls._instantiate(backends[preferred], config)
            if not instance.is_available():
                raise PerceptionUnavailableError(
                    f"perception backend '{preferred}' 已安装但当前不可用"
                    f"（is_available() 返回 False）。\n"
                    f"  {PerceptionUnavailableError.DEFAULT_HINT}"
                )
            return instance

        # 2. 自动 fallback
        last_unavailable: Optional[str] = None
        for name in DEFAULT_FALLBACK_ORDER:
            if name in backends:
                instance = cls._instantiate(backends[name], config)
                if instance.is_available():
                    return instance
                last_unavailable = name

        # 2.5 fallback 顺序外但已注册的 backend 也尝试一下
        for name, cls_ in backends.items():
            if name in DEFAULT_FALLBACK_ORDER:
                continue
            instance = cls._instantiate(cls_, config)
            if instance.is_available():
                return instance
            last_unavailable = name

        # 3. 全军覆没
        msg_lines = ["发现已安装的 perception backend，但全部不可用："]
        for name in backends:
            msg_lines.append(f"    - {name}: is_available() == False")
        if last_unavailable:
            msg_lines.append(
                "  常见原因：ollama 未启动 / 模型未下载 / 远程服务不可达。"
            )
        msg_lines.append(PerceptionUnavailableError.DEFAULT_HINT)
        raise PerceptionUnavailableError("\n".join(msg_lines))

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @classmethod
    def list_backends(cls) -> List[str]:
        """返回所有已发现的 backend 名称（仅用于诊断 / CLI）。"""
        return sorted(cls.discover().keys())

    @classmethod
    def reset(cls) -> None:
        """清空发现缓存，强制下次 ``discover()`` 重新扫描。

        **仅用于测试**——生产代码不应调用。
        """
        cls._cache = None

    @classmethod
    def register(
        cls,
        name: str,
        backend_cls: Type[PerceptionBackend],
    ) -> None:
        """**测试专用**：直接往缓存中注入 backend 类，跳过 entry_points 扫描。

        允许单元测试在不真正安装包的前提下验证 Registry 行为。生产代码
        请通过 ``pyproject.toml`` 的 entry_points 机制注册。
        """
        if not isinstance(backend_cls, type) or not issubclass(
            backend_cls, PerceptionBackend
        ):
            raise TypeError(
                f"{backend_cls!r} 不是 PerceptionBackend 的子类"
            )
        if cls._cache is None:
            cls._cache = {}
        cls._cache[name] = backend_cls

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @staticmethod
    def _instantiate(
        backend_cls: Type[PerceptionBackend],
        config: Dict[str, Any],
    ) -> PerceptionBackend:
        """根据 backend 的 ``__init__`` 签名筛选 kwargs 后实例化。"""
        import inspect
        try:
            sig = inspect.signature(backend_cls.__init__)
            accepted = set()
            has_var_kwarg = False
            for name, param in sig.parameters.items():
                if name == "self":
                    continue
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    has_var_kwarg = True
                else:
                    accepted.add(name)
            if has_var_kwarg:
                kwargs = config
            else:
                kwargs = {k: v for k, v in config.items() if k in accepted}
        except (TypeError, ValueError):
            kwargs = {}
        return backend_cls(**kwargs)


__all__ = ["PerceptionRegistry", "ENTRY_POINT_GROUP", "DEFAULT_FALLBACK_ORDER"]
