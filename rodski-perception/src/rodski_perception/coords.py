"""坐标转换 & Qwen3-VL 响应解析。

Qwen3-VL 原生 bbox 输出约定：

.. code-block:: json

   [{"bbox_2d": [x1, y1, x2, y2], "label": "..."}]

其中 x/y 在 ``[0, 1000]`` 千分比空间。本模块负责：

- 从 ollama chat 返回的 ``content`` 文本里把 JSON bbox 数组解析出来
  （模型有时会带 markdown fence、前后多余说明文字）
- 千分比 ↔ 像素互转
- 中心点计算
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .errors import InvalidResponseError

logger = logging.getLogger(__name__)


BBox = Tuple[int, int, int, int]


# ----------------------------------------------------------------------
# Qwen3-VL 响应解析
# ----------------------------------------------------------------------


# 兼容三种常见包裹：
#   1. ```json ... ```
#   2. ```... ```
#   3. 裸 JSON 数组
_JSON_BLOCK_PATTERNS = [
    re.compile(r"```(?:json)?\s*(\[.*?\])\s*```", re.DOTALL),
    re.compile(r"(\[[^\[\]]*\{.*?\}[^\[\]]*\])", re.DOTALL),
]


def parse_qwen_response(text: str) -> List[dict]:
    """从 Qwen3-VL 的 chat ``content`` 中提取 ``[{bbox_2d, label, ...}, ...]``。

    实现策略（依次尝试）：

    1. 整段当 JSON 解析
    2. 抽出第一个 ``[...]`` 代码块再解析
    3. 抽出第一个 JSON 数组样式的子串再解析

    解析后过滤掉缺少 ``bbox_2d`` 字段的项；如果最终一项都没有，抛
    :class:`InvalidResponseError`。
    """
    if not text or not text.strip():
        raise InvalidResponseError("模型返回空字符串")

    candidates: List[str] = [text]
    for pat in _JSON_BLOCK_PATTERNS:
        m = pat.search(text)
        if m:
            candidates.append(m.group(1))

    parsed: Optional[list] = None
    last_err: Optional[Exception] = None
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError as exc:
            last_err = exc
            continue
        if isinstance(obj, list):
            parsed = obj
            break
        # Qwen 偶尔包成 {"results": [...]}
        if isinstance(obj, dict):
            for key in ("results", "objects", "elements", "detections"):
                if isinstance(obj.get(key), list):
                    parsed = obj[key]
                    break
            if parsed is not None:
                break
            # 单个对象 {bbox_2d:..., label:...}
            if "bbox_2d" in obj:
                parsed = [obj]
                break

    if parsed is None:
        raise InvalidResponseError(
            f"无法从模型输出中解析 bbox 数组：{text[:200]}"
            + (f" (last error: {last_err})" if last_err else "")
        )

    items: List[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        bbox = item.get("bbox_2d") or item.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue
        try:
            x1, y1, x2, y2 = (int(round(float(v))) for v in bbox)
        except (TypeError, ValueError):
            continue
        items.append(
            {
                "bbox_2d": [x1, y1, x2, y2],
                "label": str(item.get("label", "")),
                # 透传 confidence 若有
                "confidence": _safe_float(item.get("confidence")),
                "raw": item,
            }
        )

    if not items:
        raise InvalidResponseError(
            f"模型输出中没有任何有效的 bbox 项：{text[:200]}"
        )
    return items


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------
# 千分比 <-> 像素
# ----------------------------------------------------------------------


def clamp_bbox_normalized(bbox: BBox, max_value: int = 1000) -> BBox:
    """把 bbox 截断到 ``[0, max_value]``，保证 x1<=x2 / y1<=y2。"""
    x1, y1, x2, y2 = bbox
    x1, x2 = sorted((max(0, min(max_value, x1)), max(0, min(max_value, x2))))
    y1, y2 = sorted((max(0, min(max_value, y1)), max(0, min(max_value, y2))))
    return (x1, y1, x2, y2)


def bbox_to_pixels(
    bbox_normalized: BBox,
    image_size: Tuple[int, int],
    max_value: int = 1000,
) -> BBox:
    """千分比 bbox → 像素 bbox。

    Parameters
    ----------
    bbox_normalized:
        ``(x1, y1, x2, y2)``，每个值在 ``[0, max_value]``。
    image_size:
        ``(width, height)`` 像素。
    max_value:
        归一化最大值，默认 1000（Qwen3-VL 约定）。
    """
    w, h = image_size
    x1, y1, x2, y2 = clamp_bbox_normalized(bbox_normalized, max_value=max_value)
    return (
        int(round(x1 * w / max_value)),
        int(round(y1 * h / max_value)),
        int(round(x2 * w / max_value)),
        int(round(y2 * h / max_value)),
    )


def bbox_center(bbox: BBox) -> Tuple[int, int]:
    """返回 bbox 的中心点（整数像素）。"""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) // 2, (y1 + y2) // 2)


# ----------------------------------------------------------------------
# 图片尺寸
# ----------------------------------------------------------------------


def read_image_size(path: Union[str, Path]) -> Tuple[int, int]:
    """读取 ``(width, height)``。延迟导入 PIL，避免 import 模块时的开销。"""
    from PIL import Image  # noqa: WPS433

    with Image.open(path) as im:
        return im.size  # (w, h)


__all__ = [
    "BBox",
    "parse_qwen_response",
    "clamp_bbox_normalized",
    "bbox_to_pixels",
    "bbox_center",
    "read_image_size",
]
