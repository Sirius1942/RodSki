"""LocalPerceptionBackend — rodski 通过 entry_points 发现的本地 backend。

注册位置（``pyproject.toml``）::

    [project.entry-points."rodski.perception_backends"]
    local = "rodski_perception.backend:LocalPerceptionBackend"

rodski 侧 :class:`rodski.vision.registry.PerceptionRegistry` 在 ``discover``
时自动加载本类；构造时 rodski 通过 ``inspect`` 过滤可接受的 kwargs，
本类接受任意 ``**kwargs`` 兼容多版本配置键。

约束
----

- ``__init__`` 不联网，不实例化 ``VLMAgent`` —— 首次 ``locate``/``locate_many``
  调用时才创建（保证 ``import`` 链路廉价）
- ``is_available()`` 只做 ollama health check + 模型是否安装；不抛异常
- ``locate_fused`` 保留父类默认实现 —— 真正的融合裁决留给 54d
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)


# rodski 侧的接口契约：如果 rodski 未安装（仅作为独立工具使用）则
# 退化为本地 stub，让本模块在 ``rodski-perception`` 单包发布时也能 import。
try:
    from rodski.vision.perception_interface import (  # type: ignore[import-not-found]
        PerceptionBackend,
        PerceptionResult,
    )
except ImportError:  # pragma: no cover - rodski 未安装的单包场景
    from dataclasses import dataclass, field
    from typing import Tuple

    @dataclass
    class PerceptionResult:  # type: ignore[no-redef]
        bbox: Tuple[int, int, int, int]
        coordinates: Tuple[int, int]
        target_description: str
        confidence: Optional[float] = None
        consensus_count: int = 0
        latency_ms: int = 0
        hint_results: dict = field(default_factory=dict)

    class PerceptionBackend:  # type: ignore[no-redef]
        name: str = "abstract"
        capabilities: set = set()

        def is_available(self) -> bool:  # pragma: no cover
            raise NotImplementedError

        def locate(self, image_path, description, element_type=None):  # pragma: no cover
            raise NotImplementedError

        def locate_many(self, image_path, descriptions, element_types=None):  # pragma: no cover
            types = element_types or [None] * len(descriptions)
            return [
                self.locate(image_path, d, element_type=t)
                for d, t in zip(descriptions, types)
            ]

        def locate_fused(self, image_path, hints, element_type=None):  # pragma: no cover
            for h in hints:
                if getattr(h, "type", "") == "vision":
                    return self.locate(
                        image_path, h.value, element_type=element_type
                    )
            return None


from .agent import DEFAULT_MODEL, LocateResult, VLMAgent
from .errors import OllamaUnreachableError
from .ollama_client import DEFAULT_OLLAMA_HOST, OllamaClient


class LocalPerceptionBackend(PerceptionBackend):  # type: ignore[misc, valid-type]
    """rodski 的本地 perception backend，基于 ollama + Qwen3-VL。

    支持的配置键（构造 kwargs，rodski Registry 会从 globalvalue.xml 透传）：

    - ``model`` / ``perception_model`` — VLM 模型名，默认 ``qwen3-vl:2b``
    - ``ollama_host`` — ollama 服务地址，默认读环境变量 ``OLLAMA_HOST``
      或 ``http://localhost:11434``

    其它未识别的 kwargs 被静默忽略，保证向前兼容。
    """

    name: str = "local"
    capabilities = {"locate", "locate_many", "parse"}

    def __init__(
        self,
        model: Optional[str] = None,
        ollama_host: Optional[str] = None,
        # 兼容 rodski globalvalue.xml 用的命名
        perception_model: Optional[str] = None,
        perception_server: Optional[str] = None,
        **kwargs,
    ) -> None:
        self._model = (
            model
            or perception_model
            or os.getenv("RODSKI_PERCEPTION_MODEL")
            or DEFAULT_MODEL
        )
        self._ollama_host = (
            ollama_host
            or perception_server
            or os.getenv("OLLAMA_HOST")
            or DEFAULT_OLLAMA_HOST
        )
        # backward compat: 一些 rodski 旧代码可能传 perception_backend 进来
        kwargs.pop("perception_backend", None)
        if kwargs:
            logger.debug(
                "LocalPerceptionBackend ignoring unknown kwargs: %s",
                sorted(kwargs.keys()),
            )

        # 延迟构造 — is_available / locate 都按需创建
        self._agent: Optional[VLMAgent] = None
        self._probe_client: Optional[OllamaClient] = None

    # ------------------------------------------------------------------
    # 必须实现
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """ollama 可达 **且** 指定模型已安装 → ``True``。"""
        client = self._get_probe_client()
        if not client.is_reachable():
            logger.debug("ollama %s 不可达", self._ollama_host)
            return False
        try:
            installed = set(client.list_models())
        except OllamaUnreachableError:
            return False
        # 模型名匹配：完全相等，或忽略 ``:tag`` 后缀
        if self._model in installed:
            return True
        bare = self._model.split(":")[0]
        return any(m == self._model or m.split(":")[0] == bare for m in installed)

    def locate(
        self,
        image_path: str,
        description: str,
        element_type: Optional[str] = None,
    ):
        """单目标定位，委托 :class:`VLMAgent`。"""
        agent = self._get_agent()
        result = agent.locate(
            prompt=description, image=image_path, element_type=element_type
        )
        if result is None:
            return None
        return _to_perception_result(result)

    def locate_many(
        self,
        image_path: str,
        descriptions: List[str],
        element_types: Optional[List[Optional[str]]] = None,
    ):
        """批量定位 — 单次 ollama 推理拿 N 个 bbox。

        ``element_types`` 长度若与 ``descriptions`` 不一致直接抛 ValueError
        （与基类契约一致）。本实现把所有 element_type 合并为一个 hint —— 因为
        单次推理只能注入一次 hint —— 取第一个非 None 的 type 作为代表。
        若需要每个目标用不同 type，调用方应改回 N 次 ``locate``。
        """
        if element_types is None:
            element_types = [None] * len(descriptions)
        if len(element_types) != len(descriptions):
            raise ValueError(
                "element_types length must match descriptions length"
            )

        agent = self._get_agent()
        merged_type = next((t for t in element_types if t), None)
        results = agent.locate_many(
            prompts=list(descriptions),
            image=image_path,
            element_type=merged_type,
        )
        return [
            _to_perception_result(r) if r is not None else None
            for r in results
        ]

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _get_probe_client(self) -> OllamaClient:
        if self._probe_client is None:
            self._probe_client = OllamaClient(host=self._ollama_host, timeout=3)
        return self._probe_client

    def _get_agent(self) -> VLMAgent:
        if self._agent is None:
            self._agent = VLMAgent(
                model=self._model,
                ollama_host=self._ollama_host,
            )
        return self._agent


# ----------------------------------------------------------------------
# 转换
# ----------------------------------------------------------------------


def _to_perception_result(result: LocateResult):
    """把 rodski-perception 的 :class:`LocateResult` 转成 rodski 的
    :class:`PerceptionResult`。"""
    return PerceptionResult(
        bbox=result.bbox,
        coordinates=result.coordinates,
        target_description=result.target_description,
        confidence=result.confidence,
        consensus_count=0,
        latency_ms=result.latency_ms,
        hint_results={},
    )


__all__ = ["LocalPerceptionBackend"]
