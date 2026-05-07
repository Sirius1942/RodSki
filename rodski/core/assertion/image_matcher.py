"""图片匹配器 - 使用 OpenCV 模板匹配实现图片断言"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None  # type: ignore
    np = None   # type: ignore

from .base_assertion import BaseAssertion

logger = logging.getLogger("rodski")


def _require_cv_deps() -> None:
    if cv2 is None or np is None:
        raise RuntimeError(
            "图片断言需要安装 OpenCV/Numpy 依赖: pip install 'rodski[vision]'"
        )


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
        scope: str = "full",
        wait: int = 0,
        element_bbox: Optional[Dict[str, int]] = None,
        poll_interval: float = 0.5,
    ) -> Dict[str, Any]:
        """执行图片模板匹配

        Args:
            screenshot: 当前截图 (BGR格式 numpy array)
            reference: 预期图片路径（相对于 images/assert/ 的路径或绝对路径）
            threshold: 匹配度阈值，范围 0.0~1.0
            scope: 断言范围，full（全屏截图）或 element（指定元素区域）
            wait: 等待秒数，0=立即断言，>0=轮询等待直到匹配成功或超时
            element_bbox: 元素边界框，scope=element 时需要提供，格式 {x, y, w, h}
            poll_interval: 轮询间隔（秒），wait>0 时生效

        Returns:
            结构化结果字典:
            {
                "matched": bool,       # 是否匹配成功
                "similarity": float,    # 实际匹配度
                "threshold": float,     # 判定阈值
                "screenshot": str,      # 截图路径（调试用）
                "reference": str,       # 预期图片路径
                "location": dict,       # 匹配位置 {x, y, w, h} 或 None
                "wait_attempts": int,   # wait 模式下尝试次数
                "first_match_time": float,  # wait 模式下首次匹配成功的时间戳（相对于开始时间），否则 None
            }
        """
        _require_cv_deps()
        if not isinstance(screenshot, np.ndarray):
            raise TypeError(f"screenshot 必须是 numpy.ndarray，实际为 {type(screenshot)}")

        if scope not in ("full", "element"):
            raise ValueError(f"scope 必须是 'full' 或 'element'，实际为 '{scope}'")

        if scope == "element" and not element_bbox:
            raise ValueError("scope=element 需要提供 element_bbox 参数")

        ref_path = Path(reference)
        if not ref_path.is_absolute():
            raise FileNotFoundError(f"预期图片路径不存在: {ref_path}")

        if not ref_path.exists():
            raise FileNotFoundError(f"预期图片不存在: {ref_path}")

        # 读取预期图片
        reference_img = cv2.imread(str(ref_path))
        if reference_img is None:
            raise ValueError(f"无法读取预期图片: {ref_path}")

        start_time = time.time()
        wait_attempts = 0
        first_match_time: Optional[float] = None

        while True:
            wait_attempts += 1

            # 根据 scope 截取区域
            if scope == "element" and element_bbox:
                cropped = self._crop_element_region(screenshot, element_bbox)
            else:
                cropped = screenshot

            # 执行模板匹配
            similarity, location = self._template_match(cropped, reference_img)

            # 对相似度取四位小数，避免浮点精度问题
            similarity_rounded = round(similarity, 4)
            matched = similarity_rounded >= threshold

            if matched:
                first_match_time = time.time() - start_time
                logger.info(
                    f"图片匹配成功: similarity={similarity:.4f} >= threshold={threshold}, "
                    f"reference={ref_path.name}, attempts={wait_attempts}"
                )
                break

            # wait<=0 → 立即断言（一次），不重试；wait>0 → 超时后停止轮询
            if wait <= 0 or (wait > 0 and (time.time() - start_time) >= wait):
                logger.warning(
                    f"图片匹配失败: similarity={similarity:.4f} < threshold={threshold}, "
                    f"reference={ref_path.name}, attempts={wait_attempts}"
                )
                break

            # 等待后重试
            time.sleep(poll_interval)

        # 构建结果
        result = {
            "matched": matched,
            "similarity": similarity_rounded,
            "threshold": threshold,
            "screenshot": None,  # 截图路径由调用方注入
            "reference": str(ref_path),
            "location": location,
            "wait_attempts": wait_attempts,
            "first_match_time": round(first_match_time, 3) if first_match_time is not None else None,
        }

        return result

    def _crop_element_region(
        self,
        screenshot: np.ndarray,
        bbox: Dict[str, int],
    ) -> np.ndarray:
        """根据元素边界框截取区域

        Args:
            screenshot: 原始截图 (BGR格式)
            bbox: 元素边界框 {x, y, w, h}

        Returns:
            截取后的图片区域
        """
        x = max(0, bbox["x"])
        y = max(0, bbox["y"])
        w = bbox["w"]
        h = bbox["h"]

        h_scr, w_scr = screenshot.shape[:2]

        # 确保不超出截图边界
        x2 = min(x + w, w_scr)
        y2 = min(y + h, h_scr)

        return screenshot[y:y2, x:x2]

    @staticmethod
    def save_failure_screenshot(
        screenshot: np.ndarray,
        reference_name: str,
        failures_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """保存匹配失败的截图到 failures 目录

        Args:
            screenshot: 当前截图 (BGR格式 numpy array)
            reference_name: 预期图片名称（用于命名）
            failures_dir: 失败截图目录，默认 images/assert/failures

        Returns:
            保存的文件路径，失败返回 None
        """
        _require_cv_deps()
        if failures_dir is None:
            # 默认使用项目 images/assert/failures 目录
            failures_dir = Path("images/assert/failures")

        try:
            failures_dir.mkdir(parents=True, exist_ok=True)

            # 文件名格式: assert_fail_{timestamp}_{reference_name}.png
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            safe_ref_name = Path(reference_name).stem
            filename = f"assert_fail_{timestamp}_{safe_ref_name}.png"
            file_path = failures_dir / filename

            success = cv2.imwrite(str(file_path), screenshot)
            if success:
                logger.info(f"失败截图已保存: {file_path}")
                return str(file_path)
            else:
                logger.warning(f"保存失败截图失败: {file_path}")
                return None
        except Exception as e:
            logger.warning(f"保存失败截图异常: {e}")
            return None

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
        _require_cv_deps()
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
