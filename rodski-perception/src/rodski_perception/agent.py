"""VLMAgent — VLM 驱动的单 / 多目标定位。

入口类 :class:`VLMAgent` 负责把"截图 + 自然语言描述"转换为
:class:`LocateResult`（含千分比 bbox、像素中心点、置信度、耗时）。

设计要点
--------

- ``import rodski_perception`` 不会触发 ollama 调用；``VLMAgent`` 的构造
  函数也不联网，仅在第一次 ``locate`` 时通过 :class:`OllamaClient` 发起请求
- ``locate_many`` 默认单次推理（一次 ollama 调用拿 N 个 bbox），失败时
  回退为 N 次串行 ``locate``，保证调用方拿到的列表长度恒等于输入长度
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
from .prompts import (
    build_locate_many_prompt,
    build_locate_prompt,
)

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "qwen3-vl:2b"


# ---------------------------------------------------------------------------
# 数据载体
# ---------------------------------------------------------------------------


@dataclass
class LocateResult:
    """VLMAgent 的单目标定位结果。

    Attributes
    ----------
    bbox:
        千分比 bbox ``(x1, y1, x2, y2)``，范围 ``[0, 1000]``。
    coordinates:
        像素坐标中心点 ``(x, y)``。
    target_description:
        本次定位的目标描述。
    label:
        模型返回的 label（可能与 description 不同）。
    confidence:
        模型自评置信度；Qwen3-VL 默认不输出，可为 ``None``。
    image_size:
        ``(width, height)``。
    latency_ms:
        本次 chat 调用耗时（毫秒）。
    model:
        实际使用的模型名。
    raw:
        模型原始响应字典（调试用）。
    """

    bbox: BBox
    coordinates: Tuple[int, int]
    target_description: str
    label: str = ""
    confidence: Optional[float] = None
    image_size: Tuple[int, int] = (0, 0)
    latency_ms: int = 0
    model: str = ""
    raw: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class VLMAgent:
    """基于 ollama 的 VLM 定位 agent。

    Parameters
    ----------
    model:
        ollama 中已 pull 的 VLM 模型名。默认 ``qwen3-vl:2b``。
    ollama_host:
        ollama 服务地址。默认 ``http://localhost:11434``。
    weights:
        预留——本类不直接使用，由调用方在融合裁决时参考。本迭代不实现
        融合（54d），此参数仅为契约预留。
    timeout:
        单次 chat 超时秒数。
    client:
        可选注入自定义 :class:`OllamaClient`（测试用）。
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        ollama_host: str = DEFAULT_OLLAMA_HOST,
        weights: Optional[dict] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Optional[OllamaClient] = None,
    ) -> None:
        self._model = model
        self._ollama_host = ollama_host
        self._weights = weights or {"vision_image": 1.0, "ocr": 0.8, "vision": 0.6}
        self._timeout = timeout
        self._client = client or OllamaClient(host=ollama_host, timeout=timeout)

    # ------------------------------------------------------------------
    # locate
    # ------------------------------------------------------------------

    def locate(
        self,
        prompt: str,
        image: Union[str, Path],
        element_type: Optional[str] = None,
    ) -> Optional[LocateResult]:
        """定位单个目标。

        Returns
        -------
        :class:`LocateResult` — 命中；``None`` — 模型返回空数组（目标不存在）。

        Raises
        ------
        OllamaUnreachableError, ModelNotFoundError, InvalidResponseError:
            分别对应网络故障、模型未安装、模型输出无法解析。
        FileNotFoundError:
            截图文件不存在。
        """
        image_path = Path(image)
        if not image_path.exists():
            raise FileNotFoundError(f"image not found: {image_path}")

        image_size = read_image_size(image_path)
        chat_prompt = build_locate_prompt(prompt, element_type=element_type)

        t0 = time.perf_counter()
        try:
            payload = self._client.chat(
                model=self._model,
                prompt=chat_prompt,
                images=[image_path],
                options={"temperature": 0, "num_predict": 300},
            )
        except InvalidResponseError:
            raise
        latency_ms = int((time.perf_counter() - t0) * 1000)

        content = _extract_content(payload)
        try:
            items = parse_qwen_response(content)
        except InvalidResponseError as exc:
            # 模型可能返回了 "[]"（空数组）—— parse 抛出"没有任何有效 bbox 项"
            # 这种情况下我们认为是"未找到"而不是"模型出错"
            if _is_empty_array(content):
                logger.debug("model returned empty array for %r", prompt)
                return None
            raise exc

        # 多个候选时取第一个（最相关）
        item = items[0]
        bbox = tuple(item["bbox_2d"])  # type: ignore[assignment]
        return LocateResult(
            bbox=bbox,  # type: ignore[arg-type]
            coordinates=bbox_center(bbox_to_pixels(bbox, image_size)),  # type: ignore[arg-type]
            target_description=prompt,
            label=item.get("label", ""),
            confidence=item.get("confidence"),
            image_size=image_size,
            latency_ms=latency_ms,
            model=self._model,
            raw=item.get("raw", {}),
        )

    # ------------------------------------------------------------------
    # locate_many
    # ------------------------------------------------------------------

    def locate_many(
        self,
        prompts: List[str],
        image: Union[str, Path],
        element_type: Optional[str] = None,
    ) -> List[Optional[LocateResult]]:
        """批量定位 N 个目标，返回长度等于 ``len(prompts)`` 的列表。

        策略：

        1. 单次 chat 推理，prompt 内列出所有目标。模型返回带 ``index`` 的数组
        2. 解析后按 ``index`` / ``label`` 回填，缺失的 index 标记为 ``None``
        3. 单次推理失败（``InvalidResponseError``）时退回为 N 次串行 ``locate``

        失败的单个项以 ``None`` 占位，不抛异常（除非整批连 fallback 也失败）。
        """
        if not prompts:
            return []

        image_path = Path(image)
        if not image_path.exists():
            raise FileNotFoundError(f"image not found: {image_path}")

        image_size = read_image_size(image_path)
        try:
            return self._locate_many_single_inference(
                prompts, image_path, image_size, element_type
            )
        except InvalidResponseError as exc:
            logger.info(
                "locate_many 单次推理无法解析（%s），回退为 N 次串行 locate",
                exc,
            )
            return self._locate_many_fallback(prompts, image_path, element_type)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _locate_many_single_inference(
        self,
        prompts: List[str],
        image_path: Path,
        image_size: Tuple[int, int],
        element_type: Optional[str],
    ) -> List[Optional[LocateResult]]:
        chat_prompt = build_locate_many_prompt(prompts, element_type=element_type)
        t0 = time.perf_counter()
        payload = self._client.chat(
            model=self._model,
            prompt=chat_prompt,
            images=[image_path],
            options={"temperature": 0, "num_predict": 800},
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        content = _extract_content(payload)
        if _is_empty_array(content):
            return [None] * len(prompts)
        items = parse_qwen_response(content)

        # 按 index 把模型返回的项映射回原 prompt 列表
        results: List[Optional[LocateResult]] = [None] * len(prompts)
        used_indices: set[int] = set()
        for item in items:
            raw = item.get("raw") or {}
            idx_v = raw.get("index", item.get("raw", {}).get("index"))
            try:
                idx = int(idx_v) if idx_v is not None else -1
            except (TypeError, ValueError):
                idx = -1
            if not (0 <= idx < len(prompts)):
                # 模型没给 index 或 index 越界：尝试按 label 匹配 prompt
                label = item.get("label", "")
                idx = _match_prompt_by_label(label, prompts, used_indices)
            if idx < 0 or idx in used_indices:
                continue
            bbox = tuple(item["bbox_2d"])  # type: ignore[assignment]
            results[idx] = LocateResult(
                bbox=bbox,  # type: ignore[arg-type]
                coordinates=bbox_center(bbox_to_pixels(bbox, image_size)),  # type: ignore[arg-type]
                target_description=prompts[idx],
                label=item.get("label", ""),
                confidence=item.get("confidence"),
                image_size=image_size,
                latency_ms=latency_ms,
                model=self._model,
                raw=raw,
            )
            used_indices.add(idx)
        return results

    def _locate_many_fallback(
        self,
        prompts: List[str],
        image_path: Path,
        element_type: Optional[str],
    ) -> List[Optional[LocateResult]]:
        results: List[Optional[LocateResult]] = []
        for p in prompts:
            try:
                results.append(self.locate(p, image_path, element_type=element_type))
            except InvalidResponseError as exc:
                logger.warning("locate(%r) 解析失败: %s", p, exc)
                results.append(None)
        return results


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------


def _extract_content(payload: dict) -> str:
    """从 ollama chat 响应里抽出 ``message.content``。"""
    if not isinstance(payload, dict):
        return ""
    msg = payload.get("message") or {}
    if isinstance(msg, dict):
        return str(msg.get("content", ""))
    return ""


def _is_empty_array(content: str) -> bool:
    """识别模型返回的"空数组" — 模型表示"没找到"。"""
    if not content:
        return False
    stripped = content.strip().strip("`").strip()
    # 去掉 json fence
    if stripped.lower().startswith("json"):
        stripped = stripped[4:].strip()
    return stripped in {"[]", "[ ]"}


def _match_prompt_by_label(
    label: str,
    prompts: List[str],
    used: set,
) -> int:
    """模糊匹配：

    1. 直接 substring 命中
    2. 共享至少一个长度 >= 3 的词（按非字母数字切词）
    """
    if not label:
        return -1
    label_lower = label.lower()
    label_words = _tokenize(label_lower)

    # 第一轮：substring
    for i, p in enumerate(prompts):
        if i in used:
            continue
        p_lower = p.lower()
        if p_lower and (p_lower in label_lower or label_lower in p_lower):
            return i

    # 第二轮：共享词
    best_i = -1
    best_overlap = 0
    for i, p in enumerate(prompts):
        if i in used:
            continue
        p_words = _tokenize(p.lower())
        overlap = len(label_words & p_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_i = i
    if best_overlap > 0:
        return best_i
    return -1


def _tokenize(text: str) -> set:
    """切成 ``{word, ...}``，过滤短词。"""
    import re
    tokens = re.findall(r"[a-z0-9\u4e00-\u9fff]+", text.lower())
    return {t for t in tokens if len(t) >= 2}


__all__ = [
    "VLMAgent",
    "LocateResult",
    "DEFAULT_MODEL",
]
