"""图片匹配器 - 使用 OpenCV 模板匹配实现图片断言"""
import cv2
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

from core.assertion.base_assertion import BaseAssertion

logger = logging.getLogger("rodski")


class ImageMatcher(BaseAssertion):
    """图片匹配器

    使用 OpenCV TM_CCORR_NORMED 模板匹配算法，
    将截图与预期图片进行匹配度比对。
    """

    def __init__(self):
        self._last_screenshot: Optional[np.ndarray] = None

    def match(
        self,
        screenshot: np.ndarray,
        reference: Path,
        threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """执行图片模板匹配

        Args:
            screenshot: 当前截图 (BGR格式 numpy array)
            reference: 预期图片路径（相对于 images/assert/ 的路径或绝对路径）
            threshold: 匹配度阈值，范围 0.0~1.0

        Returns:
            结构化结果字典:
            {
                "matched": bool,       # 是否匹配成功
                "similarity": float,    # 实际匹配度
                "threshold": float,    # 判定阈值
                "screenshot": str,     # 截图路径（调试用）
                "reference": str,      # 预期图片路径
                "location": dict,      # 匹配位置 {x, y, w, h} 或 None
            }
        """
        if not isinstance(screenshot, np.ndarray):
            raise TypeError(f"screenshot 必须是 numpy.ndarray，实际为 {type(screenshot)}")

        ref_path = Path(reference)
        if not ref_path.is_absolute():
            raise FileNotFoundError(f"预期图片路径不存在: {ref_path}")

        if not ref_path.exists():
            raise FileNotFoundError(f"预期图片不存在: {ref_path}")

        # 读取预期图片
        reference_img = cv2.imread(str(ref_path))
        if reference_img is None:
            raise ValueError(f"无法读取预期图片: {ref_path}")

        # 执行模板匹配
        similarity, location = self._template_match(screenshot, reference_img)

        # 对相似度取四位小数，避免浮点精度问题（如 0.9999999 实际应为 1.0）
        similarity_rounded = round(similarity, 4)
        matched = similarity_rounded >= threshold

        result = {
            "matched": matched,
            "similarity": similarity_rounded,
            "threshold": threshold,
            "screenshot": None,  # 截图路径由调用方注入
            "reference": str(ref_path),
            "location": location,
        }

        if matched:
            logger.info(
                f"图片匹配成功: similarity={similarity:.4f} >= threshold={threshold}, "
                f"reference={ref_path.name}"
            )
        else:
            logger.warning(
                f"图片匹配失败: similarity={similarity:.4f} < threshold={threshold}, "
                f"reference={ref_path.name}"
            )

        return result

    def _template_match(
        self,
        screenshot: np.ndarray,
        reference_img: np.ndarray,
    ) -> tuple[float, Optional[Dict[str, int]]]:
        """使用 TM_CCOEFF_NORMED 执行模板匹配

        Args:
            screenshot: 实际截图
            reference_img: 预期图片

        Returns:
            (similarity, location) - 匹配度和匹配位置
        """
        # 如果尺寸不一致，按预期图片尺寸裁剪截图中心区域
        screenshot_h, screenshot_w = screenshot.shape[:2]
        ref_h, ref_w = reference_img.shape[:2]

        if screenshot_h != ref_h or screenshot_w != ref_w:
            logger.debug(
                f"尺寸不一致: screenshot={screenshot_w}x{screenshot_h}, "
                f"reference={ref_w}x{ref_h}，裁剪截图后匹配"
            )
            # 中心裁剪
            x1 = max(0, (screenshot_w - ref_w) // 2)
            y1 = max(0, (screenshot_h - ref_h) // 2)
            x2 = x1 + ref_w
            y2 = y1 + ref_h
            screenshot = screenshot[y1:y2, x1:x2]

        # 转为灰度图以提高匹配准确性
        if len(screenshot.shape) == 3:
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        else:
            screenshot_gray = screenshot

        if len(reference_img.shape) == 3:
            reference_gray = cv2.cvtColor(reference_img, cv2.COLOR_BGR2GRAY)
        else:
            reference_gray = reference_img

        # TM_CCORR_NORMED：对纯色/低对比度图片更稳定
        # （TM_CCOEFF_NORMED 在 OpenCV 4.11+ 对纯色图片有已知问题，返回 0）
        result = cv2.matchTemplate(
            screenshot_gray,
            reference_gray,
            cv2.TM_CCORR_NORMED,
        )

        # 获取最佳匹配位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        similarity = float(max_val)

        # 获取匹配位置和尺寸
        location = None
        if similarity >= 0.0:  # 始终返回位置信息
            x, y = max_loc
            location = {
                "x": int(x),
                "y": int(y),
                "w": int(ref_w),
                "h": int(ref_h),
            }

        return similarity, location
