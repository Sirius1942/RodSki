"""PerceptionBackend 抽象接口 — v7.1.0 perception 插件契约。

本模块定义 rodski 与 perception 实现（rodski-perception、未来的远程 backend
或任何第三方 backend）之间的稳定契约。**rodski 核心不依赖任何具体 backend
实现**——所有 backend 通过 Python ``entry_points`` 机制注册，并在运行时由
``rodski.vision.registry.PerceptionRegistry`` 动态发现。

契约稳定性承诺
--------------
- ``PerceptionResult`` / ``PerceptionBackend`` 的字段与方法签名在 v7.x
  内保持向后兼容；新增字段为可选并提供默认值。
- 抽象方法 ``locate`` 必须实现；``locate_many`` / ``locate_fused``
  提供默认回退实现，第三方 backend 可选择重载以提供单次推理优化。

参考：``.pb/specs/v7.1.0-perception-design.md`` §4.2、§4.4
       ``rodski/docs/CORE_DESIGN_CONSTRAINTS.md`` §2.6
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# 数据载体
# ---------------------------------------------------------------------------


@dataclass
class PerceptionResult:
    """perception backend 的单目标定位结果。

    Parameters
    ----------
    bbox:
        目标在图像中的边界框 ``(x1, y1, x2, y2)``。
        backend 实现约定：使用千分比 ``[0, 1000]`` 坐标系，调用方
        （rodski 的 vision dispatch）负责再转换为像素坐标。
    coordinates:
        目标中心点的**像素坐标** ``(x, y)``。
    target_description:
        本次定位的目标描述（即调用时传入的 ``description``）。
    confidence:
        backend 自评的置信度，``0.0–1.0``；无法估算时为 ``None``。
    consensus_count:
        融合裁决场景下达成共识的 hint 数量（单目标 locate 时为 ``0``）。
    latency_ms:
        backend 内部的推理耗时（毫秒）。
    hint_results:
        融合裁决场景下，各个独立 hint 的原始结果（调试用）。
        单目标 locate 时为空字典。
    """

    bbox: Tuple[int, int, int, int]
    coordinates: Tuple[int, int]
    target_description: str
    confidence: Optional[float] = None
    consensus_count: int = 0
    latency_ms: int = 0
    hint_results: dict = field(default_factory=dict)


@dataclass
class LocatorHint:
    """融合裁决场景下，调用方传入 backend 的单个线索。

    Parameters
    ----------
    type:
        线索类型：``"vision_image"`` | ``"ocr"`` | ``"vision"``。
    value:
        线索值：参考图路径、待匹配文字或自然语言描述。
    """

    type: str
    value: str


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------


class PerceptionUnavailableError(RuntimeError):
    """perception backend 不可用时抛出的统一异常。

    触发场景：
        - 未安装任何 perception backend（``pip install rodski`` 但
          未装 ``rodski[perception]``）
        - 指定的 backend 不存在（如 ``perception_backend=remote``
          但未装远程 backend 包）
        - backend 已加载但 ``is_available()`` 返回 ``False``
          （如 ollama 未启动、远程服务不可达）

    错误信息必须包含可操作的安装指引（``pip install rodski[perception]``、
    ``ollama pull qwen3-vl:2b`` 等），调用方/用例的栈中**禁止**出现
    裸 ``ImportError`` / ``ConnectionError``。
    """

    DEFAULT_HINT: str = (
        "未发现可用的 perception backend。\n"
        "  推荐安装方式：\n"
        "    pip install rodski[perception]\n"
        "    brew install ollama && brew services start ollama\n"
        "    ollama pull qwen3-vl:2b\n"
        "  或在 globalvalue.xml / 环境变量中配置远程 backend\n"
        "  （perception_backend=remote, perception_server=http://...）。"
    )

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or self.DEFAULT_HINT)


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------


class PerceptionBackend(ABC):
    """所有 perception backend 实现必须遵守的契约。

    第三方 backend 实现要点：

    1. 继承本类并实现 ``is_available`` / ``locate``。
    2. 设置类属性 ``name`` 为唯一标识符（如 ``"local"`` / ``"remote"``）。
    3. 设置类属性 ``capabilities`` 描述可用能力。
    4. 在自身项目的 ``pyproject.toml`` 中通过
       ``[project.entry-points."rodski.perception_backends"]`` 注册。

    rodski 通过 ``importlib.metadata.entry_points`` 发现，无需修改 rodski 源码。
    """

    #: backend 唯一标识符（``"local"`` / ``"remote"`` 等）。
    name: str = "abstract"

    #: 能力集合，常用取值见 ``DEFAULT_CAPABILITIES``。
    capabilities: Set[str] = set()

    # ------------------------------------------------------------------
    # 必须实现
    # ------------------------------------------------------------------

    @abstractmethod
    def is_available(self) -> bool:
        """运行时可用性检查。

        实现要点：
            - 检查依赖是否齐全（包是否装好、模型是否下载）
            - 检查服务可达（ollama / 远程 HTTP 服务）
            - **不要**抛异常，可用 → ``True``，否则 ``False``
        """

    @abstractmethod
    def locate(
        self,
        image_path: str,
        description: str,
        element_type: Optional[str] = None,
    ) -> Optional[PerceptionResult]:
        """单目标定位。

        Parameters
        ----------
        image_path:
            截图文件绝对路径。
        description:
            目标的自然语言描述。
        element_type:
            element 标签的 ``type`` 属性（``button`` / ``input`` /
            ``text`` / ``icon`` / ...），作为先验送给 backend。可选。

        Returns
        -------
        定位结果；未找到返回 ``None``，**不要**抛 ``ElementNotFoundError``。
        """

    # ------------------------------------------------------------------
    # 默认实现（backend 可重载以做单次推理优化）
    # ------------------------------------------------------------------

    def locate_many(
        self,
        image_path: str,
        descriptions: List[str],
        element_types: Optional[List[Optional[str]]] = None,
    ) -> List[Optional[PerceptionResult]]:
        """批量定位。默认实现为多次 ``locate``；backend 可重载为单次推理。"""
        types = element_types or [None] * len(descriptions)
        if len(types) != len(descriptions):
            raise ValueError(
                "element_types length must match descriptions length"
            )
        return [
            self.locate(image_path, d, element_type=t)
            for d, t in zip(descriptions, types)
        ]

    def locate_fused(
        self,
        image_path: str,
        hints: List[LocatorHint],
        element_type: Optional[str] = None,
    ) -> Optional[PerceptionResult]:
        """融合裁决：多种线索共同决定坐标。

        默认实现：从 hints 中找出第一个 ``type == "vision"`` 的描述，
        转调 ``locate``；不实现真正的融合。完整的 IoU 共识聚类算法在
        54d 由 LocalBackend / FusionLocator 提供。

        本方法保留是为了让契约稳定：调用方今天就可以写
        ``backend.locate_fused(...)``，54d 上线 LocalBackend 后行为
        自动升级，rodski 代码无需改动。
        """
        for hint in hints:
            if hint.type == "vision":
                return self.locate(
                    image_path, hint.value, element_type=element_type
                )
        # 无 vision hint 时无法回退，返回 None（调用方走降级路径）
        return None

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return (
            f"<{type(self).__name__} name={self.name!r} "
            f"capabilities={sorted(self.capabilities)}>"
        )


#: 标准能力字符串集合。backend 可任选其中若干声明。
DEFAULT_CAPABILITIES: Set[str] = {
    "locate",         # 单目标定位
    "locate_many",    # 批量定位（单次推理）
    "locate_fused",   # 融合裁决
    "parse",          # 解析全部元素（无目标描述）
}


__all__ = [
    "PerceptionResult",
    "LocatorHint",
    "PerceptionBackend",
    "PerceptionUnavailableError",
    "DEFAULT_CAPABILITIES",
]
