"""图片模板匹配器 - 使用 OpenCV 进行模板图片匹配。

提供 ImageMatcher 类，支持在截图中定位模板图片的位置。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# 类型别名
BBox = Tuple[int, int, int, int]  # (x1, y1, x2, y2)
ScreenshotInput = Union[str, Path, "np.ndarray", "Image.Image"]


def _get_cv2():
    """延迟导入 cv2，避免在未安装时抛出 ImportError。"""
    try:
        import cv2  # type: ignore[import]
        return cv2
    except ImportError as exc:
        raise ImportError(
            "OpenCV (cv2) is required for image matching. "
            "Install it with: pip install opencv-python"
        ) from exc


class ImageMatcher:
    """图片模板匹配器 - 使用 OpenCV 进行模板匹配。

    在截图中搜索模板图片，返回匹配区域的边界框坐标。
    使用归一化相关系数方法 (TM_CCOEFF_NORMED) 进行匹配。

    Args:
        images_dir: 模板图片目录（相对于测试模块或绝对路径），默认 "images"。
        threshold: 匹配阈值 (0-1)，默认 0.8。值越高匹配越严格。

    Examples:
        >>> matcher = ImageMatcher(images_dir="images")
        >>> bbox = matcher.match("login_btn.png", screenshot)
        >>> if bbox:
        ...     print(f"Found at: {bbox}")
        ...     x1, y1, x2, y2 = bbox
        ...     center_x = (x1 + x2) // 2
        ...     center_y = (y1 + y2) // 2
    """

    def __init__(self, images_dir: str = "images", threshold: float = 0.8):
        self._images_dir = images_dir
        self._threshold = threshold
        self._template_cache: dict[str, np.ndarray] = {}

    @property
    def images_dir(self) -> str:
        """模板图片目录路径。"""
        return self._images_dir

    @images_dir.setter
    def images_dir(self, value: str) -> None:
        self._images_dir = value
        self._template_cache.clear()  # 切换目录时清除缓存

    @property
    def threshold(self) -> float:
        """当前匹配阈值。"""
        return self._threshold

    def set_threshold(self, threshold: float) -> None:
        """设置匹配阈值。

        Args:
            threshold: 匹配阈值 (0-1)。

        Raises:
            ValueError: 阈值不在有效范围内。
        """
        if not 0 <= threshold <= 1:
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")
        self._threshold = threshold

    def match(
        self,
        template_path: str,
        screenshot: ScreenshotInput,
    ) -> Optional[BBox]:
        """在截图中匹配模板图片。

        Args:
            template_path: 模板图片路径（相对于 images_dir，或绝对路径）。
            screenshot: 截图，支持以下格式：
                - 文件路径 (str 或 Path)
                - PIL Image 对象
                - numpy array (BGR 或 RGB 格式)

        Returns:
            (x1, y1, x2, y2) 匹配区域边界框，未找到返回 None。
            坐标为像素值，(x1, y1) 为左上角，(x2, y2) 为右下角。

        Raises:
            FileNotFoundError: 模板图片不存在。
            ValueError: 截图为空或格式无效。
        """
        # 加载模板图片
        template = self._load_template(template_path)
        if template is None:
            raise FileNotFoundError(f"Template image not found: {template_path}")

        th, tw = template.shape[:2]  # 模板尺寸

        # 加载截图
        screenshot_array = self._screenshot_to_array(screenshot)
        if screenshot_array is None:
            raise ValueError("Failed to convert screenshot to array")

        sh, sw = screenshot_array.shape[:2]  # 截图尺寸

        # 检查模板是否大于截图
        if th > sh or tw > sw:
            logger.warning(
                "Template (%dx%d) larger than screenshot (%dx%d), cannot match",
                tw, th, sw, sh,
            )
            return None

        # 执行模板匹配
        cv2 = _get_cv2()
        result = cv2.matchTemplate(
            screenshot_array,
            template,
            cv2.TM_CCOEFF_NORMED,
        )

        # 查找最佳匹配位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        logger.debug(
            "Template matching: max_val=%.3f, threshold=%.3f, location=%s",
            max_val, self._threshold, max_loc,
        )

        # 判断是否达到阈值
        if max_val < self._threshold:
            logger.info(
                "No match found: max_val=%.3f < threshold=%.3f",
                max_val, self._threshold,
            )
            return None

        # 计算边界框
        x1, y1 = max_loc
        x2, y2 = x1 + tw, y1 + th

        logger.info(
            "Match found: bbox=(%d, %d, %d, %d), confidence=%.3f",
            x1, y1, x2, y2, max_val,
        )

        return (x1, y1, x2, y2)

    def match_all(
        self,
        template_path: str,
        screenshot: ScreenshotInput,
        min_distance: int = 10,
    ) -> list[Tuple[BBox, float]]:
        """在截图中查找所有匹配的模板位置。

        Args:
            template_path: 模板图片路径。
            screenshot: 截图。
            min_distance: 相邻匹配点之间的最小像素距离，用于去重。

        Returns:
            列表，每项为 ((x1, y1, x2, y2), confidence) 元组。
            按置信度降序排列。

        Raises:
            FileNotFoundError: 模板图片不存在。
        """
        # 加载模板图片
        template = self._load_template(template_path)
        if template is None:
            raise FileNotFoundError(f"Template image not found: {template_path}")

        th, tw = template.shape[:2]

        # 加载截图
        screenshot_array = self._screenshot_to_array(screenshot)
        if screenshot_array is None:
            raise ValueError("Failed to convert screenshot to array")

        sh, sw = screenshot_array.shape[:2]

        if th > sh or tw > sw:
            return []

        # 执行模板匹配
        cv2 = _get_cv2()
        result = cv2.matchTemplate(
            screenshot_array,
            template,
            cv2.TM_CCOEFF_NORMED,
        )

        # 查找所有超过阈值的位置
        locations = np.where(result >= self._threshold)
        matches: list[Tuple[BBox, float]] = []

        for pt in zip(*locations[::-1]):  # (x, y) 格式
            confidence = result[pt[1], pt[0]]
            x1, y1 = pt
            x2, y2 = x1 + tw, y1 + th

            # 检查与已有匹配的距离
            too_close = False
            for (existing_bbox, _) in matches:
                ex1, ey1, _, _ = existing_bbox
                dist = ((x1 - ex1) ** 2 + (y1 - ey1) ** 2) ** 0.5
                if dist < min_distance:
                    too_close = True
                    break

            if not too_close:
                matches.append(((x1, y1, x2, y2), float(confidence)))

        # 按置信度降序排列
        matches.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            "Found %d match(es) for template '%s'",
            len(matches), template_path,
        )

        return matches

    def _load_template(self, template_path: str) -> Optional[np.ndarray]:
        """加载模板图片并转换为 BGR numpy array。

        支持缓存，避免重复加载。

        Args:
            template_path: 模板图片路径（相对或绝对）。

        Returns:
            BGR 格式的 numpy array，加载失败返回 None。
        """
        # 检查缓存
        if template_path in self._template_cache:
            return self._template_cache[template_path]

        # 解析路径
        path = self._resolve_template_path(template_path)
        if path is None or not path.exists():
            logger.warning("Template image not found: %s", template_path)
            return None

        # 加载图片
        cv2 = _get_cv2()
        template = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if template is None:
            logger.warning("Failed to load template image: %s", path)
            return None

        # 缓存
        self._template_cache[template_path] = template
        logger.debug("Loaded template: %s (%dx%d)", path, template.shape[1], template.shape[0])

        return template

    def _resolve_template_path(self, template_path: str) -> Optional[Path]:
        """解析模板图片路径。

        支持绝对路径和相对路径（相对于 images_dir）。

        Args:
            template_path: 原始路径字符串。

        Returns:
            解析后的 Path 对象，无法解析返回 None。
        """
        # 尝试作为绝对路径
        p = Path(template_path)
        if p.is_absolute() and p.exists():
            return p

        # 尝试相对于 images_dir
        p = Path(self._images_dir) / template_path
        if p.exists():
            return p

        # 尝试相对于当前工作目录
        p = Path.cwd() / template_path
        if p.exists():
            return p

        return None

    def _screenshot_to_array(self, screenshot: ScreenshotInput) -> Optional[np.ndarray]:
        """将截图转换为 BGR numpy array。

        支持多种输入格式：文件路径、PIL Image、numpy array。

        Args:
            screenshot: 截图输入。

        Returns:
            BGR 格式的 numpy array，转换失败返回 None。
        """
        # 文件路径
        if isinstance(screenshot, (str, Path)):
            path = Path(screenshot)
            if not path.exists():
                logger.warning("Screenshot file not found: %s", path)
                return None
            cv2 = _get_cv2()
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("Failed to load screenshot: %s", path)
                return None
            return img

        # numpy array
        if isinstance(screenshot, np.ndarray):
            return self._normalize_array(screenshot)

        # PIL Image
        try:
            from PIL import Image  # type: ignore[import]
            if isinstance(screenshot, Image.Image):
                cv2 = _get_cv2()
                # PIL 使用 RGB，OpenCV 使用 BGR
                rgb_array = np.array(screenshot)
                if rgb_array.ndim == 2:
                    # 灰度图转 BGR
                    return cv2.cvtColor(rgb_array, cv2.COLOR_GRAY2BGR)
                elif rgb_array.ndim == 3:
                    if rgb_array.shape[2] == 4:
                        # RGBA -> BGR
                        return cv2.cvtColor(rgb_array, cv2.COLOR_RGBA2BGR)
                    else:
                        # RGB -> BGR
                        return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
        except ImportError:
            logger.debug("PIL not available, skipping PIL Image handling")

        logger.warning("Unsupported screenshot type: %s", type(screenshot))
        return None

    def _normalize_array(self, arr: np.ndarray) -> np.ndarray:
        """规范化 numpy array 格式。

        - 确保是 BGR 格式
        - 确保 dtype 为 uint8
        """
        cv2 = _get_cv2()
        if arr.dtype != np.uint8:
            # 浮点数组（0-1 范围）转换为 uint8
            if arr.dtype in (np.float32, np.float64):
                if arr.max() <= 1.0:
                    arr = (arr * 255).astype(np.uint8)
                else:
                    arr = arr.astype(np.uint8)
            else:
                arr = arr.astype(np.uint8)

        # 灰度图转 BGR
        if arr.ndim == 2:
            return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)

        # RGBA -> BGR
        if arr.ndim == 3 and arr.shape[2] == 4:
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)

        # RGB -> BGR（假设 3 通道数组是 RGB）
        # 注意：如果是 BGR 则无需转换，但无法自动判断
        # 调用方需确保 3 通道数组的格式

        return arr

    def clear_cache(self) -> None:
        """清除模板图片缓存。"""
        self._template_cache.clear()
        logger.debug("Template cache cleared")

    def get_center(self, bbox: BBox) -> Tuple[int, int]:
        """计算边界框的中心点坐标。

        Args:
            bbox: (x1, y1, x2, y2) 边界框。

        Returns:
            (cx, cy) 中心点坐标。
        """
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)