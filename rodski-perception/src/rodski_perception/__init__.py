"""rodski-perception — GUI 元素感知组件 (v7.1.0)

提供基于本地 ollama + VLM (Qwen3-VL) 的图像元素定位能力。

公共 API
--------

.. code-block:: python

    from rodski_perception import VLMAgent, ImageParser

    agent = VLMAgent(model="qwen3-vl:2b", ollama_host="http://localhost:11434")
    result = agent.locate(prompt="登录按钮", image="screenshot.png")
    # result.bbox: (x1,y1,x2,y2) 千分比
    # result.coordinates: (x,y) 像素中心
    # result.latency_ms / result.confidence

    parsed = ImageParser(model="qwen3-vl:2b").parse("screenshot.png")
    # parsed.elements / parsed.latency_ms

约束
----

- ``import rodski_perception`` **不** 触发任何网络 / 模型加载
- ollama 服务由用户自行启动（``brew services start ollama``）
- 集成到 rodski：通过 entry_points ``rodski.perception_backends``
  注册的 ``LocalPerceptionBackend`` 自动被 rodski 发现

参考
----

- ``.pb/specs/v7.1.0-perception-design.md`` §3
- ``.pb/iterations/iteration-54c/tasks.md``
"""

from __future__ import annotations

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "VLMAgent",
    "LocateResult",
    "ImageParser",
    "ParseResult",
    "ParsedElement",
    "OllamaUnreachableError",
    "ModelNotFoundError",
    "PerceptionError",
]


# 延迟导入以避免 ``import rodski_perception`` 触发可选依赖的加载。
# Pillow / requests 是必须的，但 backend.py 会 import rodski（可选），
# 所以单独 lazy import。
def __getattr__(name: str):
    if name in {"VLMAgent", "LocateResult"}:
        from .agent import VLMAgent, LocateResult  # noqa: WPS433

        globals()["VLMAgent"] = VLMAgent
        globals()["LocateResult"] = LocateResult
        return globals()[name]
    if name in {"ImageParser", "ParseResult", "ParsedElement"}:
        from .parser import ImageParser, ParseResult, ParsedElement  # noqa: WPS433

        globals()["ImageParser"] = ImageParser
        globals()["ParseResult"] = ParseResult
        globals()["ParsedElement"] = ParsedElement
        return globals()[name]
    if name in {"OllamaUnreachableError", "ModelNotFoundError", "PerceptionError"}:
        from .errors import (  # noqa: WPS433
            OllamaUnreachableError,
            ModelNotFoundError,
            PerceptionError,
        )

        globals()["OllamaUnreachableError"] = OllamaUnreachableError
        globals()["ModelNotFoundError"] = ModelNotFoundError
        globals()["PerceptionError"] = PerceptionError
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
