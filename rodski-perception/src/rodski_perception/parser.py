"""ImageParser — 不带目标描述，一次性发现所有可交互元素。

主要用例：
- 评测数据集半自动标注（``rodski-perception parse > draft.json``）
- 调试时快速看模型对截图的整体理解

API 故意与 :class:`VLMAgent` 保持解耦：parser 不接受 prompt，agent 不做全量解析。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .coords import (
    BBox,
    bbox_center,
    bbox_to_pixels,
    parse_qwen_response,
    read_image_size,
)
from .errors import InvalidResponseError
from .ollama_client import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_TIMEOUT_SECONDS,
    OllamaClient,
)
from .prompts import build_parse_prompt

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "qwen3-vl:2b"


@dataclass
class ParsedElement:
    """单个被发现的元素。"""

    bbox: BBox                              # 千分比
    coordinates: Tuple[int, int]            # 像素中心
    label: str
    kind: str = "other"                     # button / input / text / icon / ...
    confidence: Optional[float] = None
    raw: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    """全量解析结果。"""

    elements: List[ParsedElement]
    image_size: Tuple[int, int]
    latency_ms: int
    model: str = ""


class ImageParser:
    """全量元素解析器。

    与 :class:`VLMAgent` 共用 :class:`OllamaClient`，但语义上完全独立。
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        ollama_host: str = DEFAULT_OLLAMA_HOST,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Optional[OllamaClient] = None,
    ) -> None:
        self._model = model
        self._ollama_host = ollama_host
        self._timeout = timeout
        self._client = client or OllamaClient(host=ollama_host, timeout=timeout)

    def parse(self, image: Union[str, Path]) -> ParseResult:
        """解析截图中的所有可交互元素。

        Raises
        ------
        FileNotFoundError, OllamaUnreachableError, ModelNotFoundError,
        InvalidResponseError
        """
        image_path = Path(image)
        if not image_path.exists():
            raise FileNotFoundError(f"image not found: {image_path}")

        image_size = read_image_size(image_path)
        t0 = time.perf_counter()
        payload = self._client.chat(
            model=self._model,
            prompt=build_parse_prompt(),
            images=[image_path],
            options={"temperature": 0, "num_predict": 1500},
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        content = _extract_content(payload)

        try:
            items = parse_qwen_response(content)
        except InvalidResponseError:
            # parse 任务允许返回空 — 模型说"没找到任何元素"
            if _is_empty_array(content):
                items = []
            else:
                raise

        elements: List[ParsedElement] = []
        for item in items:
            bbox = tuple(item["bbox_2d"])  # type: ignore[assignment]
            raw = item.get("raw") or {}
            elements.append(
                ParsedElement(
                    bbox=bbox,  # type: ignore[arg-type]
                    coordinates=bbox_center(
                        bbox_to_pixels(bbox, image_size)  # type: ignore[arg-type]
                    ),
                    label=item.get("label", ""),
                    kind=str(raw.get("kind", "other")),
                    confidence=item.get("confidence"),
                    raw=raw,
                )
            )

        return ParseResult(
            elements=elements,
            image_size=image_size,
            latency_ms=latency_ms,
            model=self._model,
        )


# ----------------------------------------------------------------------
# 内部
# ----------------------------------------------------------------------


def _extract_content(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    msg = payload.get("message") or {}
    if isinstance(msg, dict):
        return str(msg.get("content", ""))
    return ""


def _is_empty_array(content: str) -> bool:
    if not content:
        return False
    stripped = content.strip().strip("`").strip()
    if stripped.lower().startswith("json"):
        stripped = stripped[4:].strip()
    return stripped in {"[]", "[ ]"}


__all__ = ["ImageParser", "ParseResult", "ParsedElement", "DEFAULT_MODEL"]
