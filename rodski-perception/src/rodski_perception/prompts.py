"""Qwen3-VL prompt 模板。

约定全部用英文做主提示词（Qwen3-VL 对英文 grounding 提示词响应最稳），
但允许目标描述本身是任意语言（中/英/日均可，模型多语言能力足够）。

输出格式约束：要求模型只返回严格的 JSON 数组：

.. code-block:: json

   [{"bbox_2d": [x1,y1,x2,y2], "label": "..."}]

坐标范围 ``[0, 1000]`` 千分比。
"""

from __future__ import annotations

from typing import List, Optional


# ----------------------------------------------------------------------
# element_type 先验
# ----------------------------------------------------------------------

_ELEMENT_TYPE_HINTS = {
    "button":   "The target is a clickable button.",
    "input":    "The target is a text input field where users type text.",
    "text":     "The target is a static text label or message displayed on screen.",
    "select":   "The target is a dropdown / select control.",
    "link":     "The target is a hyperlink.",
    "icon":     "The target is an icon-only button (likely without text label).",
    "image":    "The target is an image element.",
    "checkbox": "The target is a checkbox.",
    "radio":    "The target is a radio button.",
}


def _element_type_clause(element_type: Optional[str]) -> str:
    if not element_type:
        return ""
    et = element_type.strip().lower()
    hint = _ELEMENT_TYPE_HINTS.get(et)
    if hint:
        return f" Hint: {hint}"
    return f" Hint: The target is a '{et}' type widget."


# ----------------------------------------------------------------------
# locate (单目标)
# ----------------------------------------------------------------------


def build_locate_prompt(
    description: str,
    element_type: Optional[str] = None,
) -> str:
    """单目标定位 prompt。

    Parameters
    ----------
    description:
        目标的自然语言描述。
    element_type:
        控件类型先验，作为 prompt hint 注入。
    """
    if not description or not description.strip():
        raise ValueError("description must not be empty")

    desc = description.strip()
    type_hint = _element_type_clause(element_type)
    return (
        f"Locate the UI element described as: {desc!r}.{type_hint}\n"
        f"Return ONLY a JSON array (no prose, no markdown fence) of the form:\n"
        f'  [{{"bbox_2d": [x1, y1, x2, y2], "label": "..."}}]\n'
        f"Coordinates are in the 0-1000 normalized scale "
        f"(0,0 = top-left, 1000,1000 = bottom-right).\n"
        f"If the element is not present, return an empty array []."
    )


# ----------------------------------------------------------------------
# locate_many (批量定位)
# ----------------------------------------------------------------------


def build_locate_many_prompt(
    descriptions: List[str],
    element_type: Optional[str] = None,
) -> str:
    """多目标批量定位 prompt — 单次推理返回多个 bbox。

    要求模型返回的数组长度 = 描述数量，顺序与描述对齐（``index``）。
    若某项找不到，模型可以返回 ``"bbox_2d": null`` 或省略该项；解析端
    会按 ``label`` 反查映射。
    """
    if not descriptions:
        raise ValueError("descriptions must not be empty")

    type_hint = _element_type_clause(element_type)
    lines = []
    for i, d in enumerate(descriptions):
        d_str = (d or "").strip()
        if not d_str:
            raise ValueError(f"description[{i}] is empty")
        lines.append(f"  {i}. {d_str}")
    bulleted = "\n".join(lines)
    return (
        f"Locate ALL of the following UI elements in this screenshot.{type_hint}\n"
        f"Targets (one per line):\n"
        f"{bulleted}\n\n"
        f"Return ONLY a JSON array (no prose, no markdown fence) of the form:\n"
        f'  [{{"index": <number>, "bbox_2d": [x1,y1,x2,y2], "label": "..."}}, ...]\n'
        f"Where 'index' MUST match the number above (0-based) so the caller can\n"
        f"correlate. Coordinates are in 0-1000 normalized scale.\n"
        f"If a target is not present, omit it from the array (do NOT invent boxes)."
    )


# ----------------------------------------------------------------------
# parse (全量解析)
# ----------------------------------------------------------------------


def build_parse_prompt() -> str:
    """全量解析 prompt — 不给描述，让模型列出所有可交互元素。"""
    return (
        "Identify ALL interactive UI elements in this screenshot.\n"
        "For each element, return its bounding box, a short label and the\n"
        "element kind (one of: button | input | text | link | icon | image |\n"
        "checkbox | radio | select | other).\n\n"
        "Return ONLY a JSON array (no prose, no markdown fence) of the form:\n"
        '  [{"bbox_2d": [x1,y1,x2,y2], "label": "...", "kind": "..."}]\n'
        "Coordinates are in 0-1000 normalized scale."
    )


__all__ = [
    "build_locate_prompt",
    "build_locate_many_prompt",
    "build_parse_prompt",
]
