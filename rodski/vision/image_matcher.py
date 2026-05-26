"""ImageTemplateMatcher — vision_image 定位器实现

基于 OpenCV ``matchTemplate`` 的离线图片模板匹配定位器。

特性：
    - 完全离线：仅依赖 ``opencv-python`` / ``numpy``，不调用任何外部服务
    - 多尺度匹配：默认尝试 5 个 scale 以容忍 DPI/缩放差异
    - 毫秒级：1920×1080 截图 + 100×40 模板 < 50ms

用法::

    matcher = ImageTemplateMatcher(threshold=0.85)
    bbox = matcher.locate("screen.png", "templates/login_btn.png")
    if bbox:
        x1, y1, x2, y2 = bbox

参考：``.pb/specs/v7.1.0-perception-design.md`` §4.5
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# 默认多尺度因子，按照"原尺寸优先"排列；超出截图大小的 scale 会被自动跳过
DEFAULT_SCALES: Tuple[float, ...] = (1.0, 0.9, 1.1, 0.75, 1.25)
DEFAULT_THRESHOLD: float = 0.85


class ImageTemplateMatcher:
    """OpenCV 模板匹配定位器。

    Parameters
    ----------
    method:
        OpenCV ``matchTemplate`` 方法，默认 ``cv2.TM_CCOEFF_NORMED``
        （对光照/对比度鲁棒，输出 0–1 的相似度分数）。
    threshold:
        最低相似度阈值；最佳匹配低于该值时返回 None。
    scales:
        多尺度因子序列；模板会被按这些比例缩放后逐一与截图匹配，
        选取整体最高分作为最终结果。

    Notes
    -----
    本类不负责截图采集，调用方应先有截图文件路径。
    参考图路径由上层（locator 分发逻辑）解析为绝对路径后再传入。
    """

    def __init__(
        self,
        method: Optional[int] = None,
        threshold: float = DEFAULT_THRESHOLD,
        scales: Tuple[float, ...] = DEFAULT_SCALES,
    ) -> None:
        # 延迟 import cv2，避免在不需要时强制依赖
        import cv2  # noqa: F401

        self._method = method if method is not None else cv2.TM_CCOEFF_NORMED
        self._threshold = float(threshold)
        self._scales = tuple(scales) if scales else (1.0,)

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def scales(self) -> Tuple[float, ...]:
        return self._scales

    def locate(
        self,
        screenshot_path: str,
        template_path: str,
    ) -> Optional[Tuple[int, int, int, int]]:
        """在截图中匹配参考图，返回 ``(x1, y1, x2, y2)`` 像素坐标。

        Parameters
        ----------
        screenshot_path:
            截图文件绝对路径。
        template_path:
            参考图文件绝对路径。

        Returns
        -------
        ``(x1, y1, x2, y2)`` 边界框，或 ``None``（未达阈值）。

        Raises
        ------
        FileNotFoundError:
            截图或参考图文件不存在，错误信息包含具体路径。
        ValueError:
            文件存在但无法被 OpenCV 解码（损坏 / 不支持的格式）。
        """
        import cv2

        # 1. 文件存在性检查
        if not os.path.exists(screenshot_path):
            raise FileNotFoundError(
                f"vision_image 截图文件不存在: {screenshot_path}"
            )
        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"vision_image 参考图文件不存在: {template_path}"
            )

        # 2. 解码
        screen = cv2.imread(str(screenshot_path))
        template = cv2.imread(str(template_path))
        if screen is None:
            raise ValueError(
                f"vision_image 截图无法解码（损坏或格式不支持）: {screenshot_path}"
            )
        if template is None:
            raise ValueError(
                f"vision_image 参考图无法解码（损坏或格式不支持）: {template_path}"
            )

        screen_h, screen_w = screen.shape[:2]
        template_h0, template_w0 = template.shape[:2]
        logger.debug(
            "ImageTemplateMatcher.locate screen=%dx%d template=%dx%d scales=%s threshold=%.2f",
            screen_w, screen_h, template_w0, template_h0, self._scales, self._threshold,
        )

        # 3. 多尺度匹配
        best_score: float = -1.0
        best_bbox: Optional[Tuple[int, int, int, int]] = None
        best_scale: Optional[float] = None

        for scale in self._scales:
            if scale <= 0:
                continue
            if scale == 1.0:
                t = template
            else:
                # cv2.resize 接受 fx/fy 缩放因子
                t = cv2.resize(template, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)

            t_h, t_w = t.shape[:2]
            # 模板比截图大 → matchTemplate 会报错，跳过
            if t_h > screen_h or t_w > screen_w:
                logger.debug(
                    "skip scale=%.2f: template %dx%d > screen %dx%d",
                    scale, t_w, t_h, screen_w, screen_h,
                )
                continue
            if t_h <= 0 or t_w <= 0:
                continue

            result = cv2.matchTemplate(screen, t, self._method)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_score:
                x1, y1 = int(max_loc[0]), int(max_loc[1])
                x2, y2 = x1 + t_w, y1 + t_h
                best_score = float(max_val)
                best_bbox = (x1, y1, x2, y2)
                best_scale = scale

        if best_bbox is None:
            logger.debug(
                "ImageTemplateMatcher: 所有 scale 都跳过（模板始终大于截图）"
            )
            return None

        logger.debug(
            "ImageTemplateMatcher best_score=%.3f bbox=%s scale=%.2f",
            best_score, best_bbox, best_scale,
        )

        if best_score < self._threshold:
            logger.info(
                "vision_image 未达阈值 (score=%.3f < %.2f) screen=%s template=%s",
                best_score, self._threshold, screenshot_path, template_path,
            )
            return None

        return best_bbox


def resolve_template_path(
    raw_value: str,
    model_dir: Optional[str] = None,
    global_vars: Optional[dict] = None,
) -> str:
    """解析参考图路径，支持三种形式：

    - 绝对路径 → 原样返回
    - 相对路径 → 以 ``model_dir`` 为基目录解析
    - 含 ``${var}`` 引用 → 用 ``global_vars`` 替换后再解析

    Parameters
    ----------
    raw_value:
        XML 中 ``<location type="vision_image">value</location>`` 的原始值。
    model_dir:
        model.xml 所在目录的绝对路径。相对路径基于此解析。
    global_vars:
        全局变量字典，用于替换 ``${var}`` 引用。可为 None。

    Returns
    -------
    解析后的绝对路径字符串。
    """
    if raw_value is None:
        raise ValueError("vision_image 参考图路径为空")

    value = raw_value.strip()
    if not value:
        raise ValueError("vision_image 参考图路径为空")

    # 1. 替换 ${var} 变量
    if "${" in value and global_vars:
        import re
        def _replace(match):
            name = match.group(1)
            if name not in global_vars:
                # 保留占位符，便于上层报错
                return match.group(0)
            return str(global_vars[name])
        value = re.sub(r"\$\{([^}]+)\}", _replace, value)

    # 2. 绝对路径直接返回
    p = Path(value)
    if p.is_absolute():
        return str(p)

    # 3. 相对路径基于 model_dir 解析
    if model_dir:
        return str((Path(model_dir) / value).resolve())

    # 没有 model_dir 上下文时只能基于当前工作目录解析
    return str(p.resolve())
