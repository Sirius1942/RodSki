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
