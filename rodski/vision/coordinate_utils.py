"""Coordinate utility functions for vision-based UI automation.

Two coordinate spaces are supported:

* **Web** – bounding boxes are normalised floats in [0, 1] and must be
  converted to pixel coordinates using the page's actual width/height.
* **Desktop** – bounding boxes are already in absolute screen pixels;
  ``get_screen_size()`` returns the full-screen dimensions.
"""

from __future__ import annotations

import logging
import platform
from typing import List, Tuple

from .exceptions import InvalidBBoxError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Web: normalised (0–1) → pixel
# ---------------------------------------------------------------------------

def normalized_to_pixel(
    bbox: list[float],
    width: int,
    height: int,
) -> tuple[int, int, int, int, int, int]:
    """Convert a normalised bounding box to pixel coordinates.

    Args:
        bbox: ``[x1, y1, x2, y2]`` with values in ``[0, 1]``.
        width: Page (or image) width in pixels.
        height: Page (or image) height in pixels.

    Returns:
        ``(cx, cy, x1, y1, x2, y2)`` — centre point followed by the four
        corner pixel coordinates, all as integers.

    Raises:
        ValueError: If *bbox* does not contain exactly four elements.
    """
    if len(bbox) != 4:
        raise ValueError(f"bbox must have 4 elements, got {len(bbox)}: {bbox}")

    x1n, y1n, x2n, y2n = bbox
    x1 = int(x1n * width)
    y1 = int(y1n * height)
    x2 = int(x2n * width)
    y2 = int(y2n * height)
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    return cx, cy, x1, y1, x2, y2


# ---------------------------------------------------------------------------
# Desktop: parse bbox string → centre point
# ---------------------------------------------------------------------------

def bbox_str_to_coords(bbox_str: str) -> tuple[int, int]:
    """Parse a ``"x1,y1,x2,y2"`` string and return the centre ``(cx, cy)``.

    The values are interpreted as absolute screen pixel coordinates.

    Args:
        bbox_str: Comma-separated string of four numbers, e.g.
            ``"100,200,300,400"``.

    Returns:
        ``(cx, cy)`` as integers.

    Raises:
        ValueError: If the string cannot be parsed into exactly four numbers.
    """
    parts = bbox_str.strip().split(",")
    if len(parts) != 4:
        raise ValueError(
            f"Expected 'x1,y1,x2,y2', got {len(parts)} fields: {bbox_str!r}"
        )
    try:
        x1, y1, x2, y2 = (float(p.strip()) for p in parts)
    except ValueError as exc:
        raise ValueError(f"Non-numeric value in bbox string {bbox_str!r}") from exc

    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    return cx, cy


# ---------------------------------------------------------------------------
# Desktop: screen dimensions
# ---------------------------------------------------------------------------

def get_screen_size() -> tuple[int, int]:
    """Return the primary screen size as ``(width, height)`` in pixels.

    Uses ``pyautogui`` on all supported platforms (Windows / macOS / Linux).

    Returns:
        ``(width, height)`` as integers.

    Raises:
        RuntimeError: If ``pyautogui`` is unavailable and no fallback exists.
    """
    try:
        import pyautogui  # type: ignore[import]
        width, height = pyautogui.size()
        return int(width), int(height)
    except ImportError:
        pass

    # Fallback for macOS via subprocess (no additional deps)
    if platform.system() == "Darwin":
        import subprocess
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "Resolution" in line:
                # e.g. "Resolution: 1920 x 1080"
                parts = line.split(":")
                if len(parts) == 2:
                    dims = parts[1].strip().split(" x ")
                    if len(dims) >= 2:
                        try:
                            return int(dims[0].strip()), int(dims[1].strip())
                        except ValueError:
                            pass

    raise RuntimeError(
        "Cannot determine screen size: install pyautogui (pip install pyautogui)"
    )


# ---------------------------------------------------------------------------
# Task 1.4: 核心坐标工具函数
# ---------------------------------------------------------------------------

def parse_bbox(bbox_str: str) -> Tuple[int, int, int, int]:
    """解析坐标字符串。

    Args:
        bbox_str: "x1,y1,x2,y2" 格式的字符串

    Returns:
        (x1, y1, x2, y2) 整数坐标元组

    Raises:
        InvalidBBoxError: 格式无效

    Examples:
        >>> parse_bbox("100,200,150,250")
        (100, 200, 150, 250)
    """
    if not bbox_str or not isinstance(bbox_str, str):
        raise InvalidBBoxError(
            bbox_str=str(bbox_str),
            reason="输入必须是非空字符串"
        )

    parts = bbox_str.strip().split(",")
    if len(parts) != 4:
        raise InvalidBBoxError(
            bbox_str=bbox_str,
            reason=f"需要 4 个坐标值，实际得到 {len(parts)} 个"
        )

    try:
        coords = [float(p.strip()) for p in parts]
    except ValueError as exc:
        raise InvalidBBoxError(
            bbox_str=bbox_str,
            reason="坐标值包含非数字字符"
        ) from exc

    x1, y1, x2, y2 = coords

    # 验证坐标顺序
    if x2 <= x1:
        raise InvalidBBoxError(
            bbox_str=bbox_str,
            reason=f"x2 ({x2}) 必须大于 x1 ({x1})"
        )
    if y2 <= y1:
        raise InvalidBBoxError(
            bbox_str=bbox_str,
            reason=f"y2 ({y2}) 必须大于 y1 ({y1})"
        )

    return (int(x1), int(y1), int(x2), int(y2))


def calculate_center(x1: int, y1: int, x2: int, y2: int) -> Tuple[int, int]:
    """计算边界框中心点。

    Args:
        x1: 左上角 x 坐标
        y1: 左上角 y 坐标
        x2: 右下角 x 坐标
        y2: 右下角 y 坐标

    Returns:
        (cx, cy) 中心点坐标

    Examples:
        >>> calculate_center(100, 200, 200, 300)
        (150, 250)
    """
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    return (cx, cy)


def normalize_to_pixel(
    bbox: List[float],
    width: int,
    height: int
) -> Tuple[int, int, int, int]:
    """归一化坐标转像素坐标。

    Args:
        bbox: [x1, y1, x2, y2] 归一化坐标 (0-1)
        width: 图像宽度
        height: 图像高度

    Returns:
        (x1, y1, x2, y2) 像素坐标

    Raises:
        InvalidBBoxError: bbox 格式无效或坐标值超出范围

    Examples:
        >>> normalize_to_pixel([0.1, 0.2, 0.3, 0.4], 1000, 800)
        (100, 160, 300, 320)
    """
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise InvalidBBoxError(
            bbox_str=str(bbox),
            reason=f"bbox 必须是包含 4 个元素的列表或元组，实际得到 {type(bbox).__name__}，长度 {len(bbox) if hasattr(bbox, '__len__') else 'N/A'}"
        )

    try:
        x1n, y1n, x2n, y2n = bbox
    except (ValueError, TypeError) as exc:
        raise InvalidBBoxError(
            bbox_str=str(bbox),
            reason="无法解析坐标值"
        ) from exc

    # 验证归一化范围
    for name, val in [('x1', x1n), ('y1', y1n), ('x2', x2n), ('y2', y2n)]:
        if not isinstance(val, (int, float)):
            raise InvalidBBoxError(
                bbox_str=str(bbox),
                reason=f"{name} 不是有效数字: {val!r}"
            )
        if not (0 <= val <= 1):
            raise InvalidBBoxError(
                bbox_str=str(bbox),
                reason=f"{name}={val} 超出归一化范围 [0, 1]"
            )

    x1 = int(x1n * width)
    y1 = int(y1n * height)
    x2 = int(x2n * width)
    y2 = int(y2n * height)

    return (x1, y1, x2, y2)


def pixel_to_normalize(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    width: int,
    height: int
) -> Tuple[float, float, float, float]:
    """像素坐标转归一化坐标。

    Args:
        x1: 左上角 x 像素坐标
        y1: 左上角 y 像素坐标
        x2: 右下角 x 像素坐标
        y2: 右下角 y 像素坐标
        width: 图像宽度
        height: 图像高度

    Returns:
        (x1, y1, x2, y2) 归一化坐标 (0-1)

    Raises:
        InvalidBBoxError: 宽度或高度无效

    Examples:
        >>> pixel_to_normalize(100, 160, 300, 320, 1000, 800)
        (0.1, 0.2, 0.3, 0.4)
    """
    if width <= 0 or height <= 0:
        raise InvalidBBoxError(
            bbox_str=f"({x1},{y1},{x2},{y2})",
            reason=f"图像尺寸必须为正数，实际 width={width}, height={height}"
        )

    nx1 = x1 / width
    ny1 = y1 / height
    nx2 = x2 / width
    ny2 = y2 / height

    return (nx1, ny1, nx2, ny2)
