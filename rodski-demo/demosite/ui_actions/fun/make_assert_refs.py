#!/usr/bin/env python3
"""生成 F011 assert 图片比对所用的参考图（可重复执行，输出确定）。

用法：python3 rodski-demo/demosite/ui_actions/fun/make_assert_refs.py

- images/assert/pattern_ref.png   与 fun/site/assert.html 中 #pattern 色块（4×2，每块 60×80）逐像素一致
- images/assert/pattern_other.png 同尺寸、换了配色与顺序的图案，页面中不存在（负向）
颜色直接取自 assert.html 的 CSS，用 numpy 绘制，不依赖浏览器截图。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

MODULE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = MODULE_DIR / "images" / "assert"

PAGE_COLORS = ["#d7263d", "#f46036", "#2e294e", "#1b998b", "#c5d86d", "#3f88c5", "#ffba08", "#6a4c93"]
OTHER_COLORS = ["#000000", "#ffffff", "#00ff00", "#ff00ff", "#ffffff", "#000000", "#ff00ff", "#00ff00"]


def bgr(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return b, g, r


def draw(colors) -> np.ndarray:
    img = np.zeros((160, 240, 3), dtype=np.uint8)
    for i, c in enumerate(colors):
        row, col = divmod(i, 4)
        img[row * 80:(row + 1) * 80, col * 60:(col + 1) * 60] = bgr(c)
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT_DIR / "pattern_ref.png"), draw(PAGE_COLORS))
    cv2.imwrite(str(OUT_DIR / "pattern_other.png"), draw(OTHER_COLORS))
    print(f"已生成 {OUT_DIR / 'pattern_ref.png'}、{OUT_DIR / 'pattern_other.png'}")


if __name__ == "__main__":
    main()
