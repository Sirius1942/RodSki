"""视频分析器 - 提取视频关键帧并与预期图片进行匹配"""
import cv2
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import numpy as np

from core.assertion.base_assertion import BaseAssertion

logger = logging.getLogger("rodski")


class VideoAnalyzer(BaseAssertion):
    """视频分析器

    从视频中提取关键帧，并与预期图片进行模板匹配。
    支持 position 参数（start/middle/end）和 time_range 参数。
    """

    def __init__(self):
        self._last_frame: Optional[np.ndarray] = None

    def match(
        self,
        video_source: str,
        reference: Path,
        threshold: float = 0.8,
        position: str = "any",
        time_range: Optional[Dict[str, float]] = None,
        scope: str = "full",
        element_bbox: Optional[Dict[str, int]] = None,
        wait: int = 0,
        poll_interval: float = 0.5,
    ) -> Dict[str, Any]:
        """执行视频关键帧匹配

        Args:
            video_source: 视频源路径，或 'recording' 表示使用内置录屏
            reference: 预期图片路径
            threshold: 匹配度阈值，0.0~1.0
            position: 关键帧位置，start/middle/end/any
            time_range: 时间范围 {start: float, end: float}，单位秒
            scope: 断言范围，full 或 element
            element_bbox: 元素边界框，scope=element 时需要
            wait: 等待秒数，0=立即，>0=轮询直到匹配成功
            poll_interval: 轮询间隔（秒）

        Returns:
            结构化结果字典:
            {
                "matched": bool,
                "similarity": float,
                "threshold": float,
                "reference": str,
                "position": str,
                "matched_frame_time": float,   # 匹配帧的时间戳（秒）
                "total_frames_checked": int,
                "wait_attempts": int,
                "first_match_time": float,
            }
        """
        if position not in ("start", "middle", "end", "any"):
            raise ValueError(f"position 必须是 start/middle/end/any，实际为 '{position}'")

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
        matched_frame_time: Optional[float] = None
        total_frames_checked = 0
        matched = False
        similarity = 0.0
        similarity_rounded = 0.0

        while True:
            wait_attempts += 1

            # 获取当前视频帧
            frame, frame_time = self._extract_frame(
                video_source, position, time_range
            )
            if frame is None:
                logger.warning("无法提取视频帧")
                break

            total_frames_checked += 1

            # 根据 scope 截取区域
            if scope == "element" and element_bbox:
                frame = self._crop_element_region(frame, element_bbox)

            # 执行模板匹配
            similarity, _ = self._template_match(frame, reference_img)
            similarity_rounded = round(similarity, 4)
            matched = similarity_rounded >= threshold

            if matched:
                matched_frame_time = frame_time
                first_match_time = time.time() - start_time
                logger.info(
                    f"视频帧匹配成功: time={frame_time:.2f}s, "
                    f"similarity={similarity:.4f} >= threshold={threshold}, "
                    f"reference={ref_path.name}, attempts={wait_attempts}"
                )
                break

            # wait=0 或超时，停止
            if wait <= 0 or (time.time() - start_time) >= wait:
                logger.warning(
                    f"视频帧匹配失败: time={frame_time:.2f}s, "
                    f"similarity={similarity:.4f} < threshold={threshold}, "
                    f"reference={ref_path.name}, frames={total_frames_checked}"
                )
                break

            time.sleep(poll_interval)

        result = {
            "matched": matched,
            "similarity": similarity_rounded,
            "threshold": threshold,
            "reference": str(ref_path),
            "position": position,
            "matched_frame_time": matched_frame_time,
            "total_frames_checked": total_frames_checked,
            "wait_attempts": wait_attempts,
            "first_match_time": round(first_match_time, 3) if first_match_time is not None else None,
        }
        return result

    def _extract_frame(
        self,
        video_source: str,
        position: str,
        time_range: Optional[Dict[str, float]],
    ) -> tuple[Optional[np.ndarray], float]:
        """从视频中提取指定位置的帧

        Args:
            video_source: 视频文件路径或 'recording'
            position: start/middle/end/any
            time_range: 可选的时间范围 {start, end}（秒）

        Returns:
            (frame, timestamp) 或 (None, 0) 如果提取失败
        """
        cap = None
        try:
            if video_source == "recording":
                # 录屏模式：使用最新录制的视频文件
                recording_dir = Path("images/assert/recordings")
                if not recording_dir.exists():
                    logger.warning(f"录屏目录不存在: {recording_dir}")
                    return None, 0.0
                video_files = sorted(recording_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
                if not video_files:
                    logger.warning("没有找到录屏文件")
                    return None, 0.0
                video_path = video_files[-1]
            else:
                video_path = Path(video_source)

            if not video_path.exists():
                logger.warning(f"视频文件不存在: {video_path}")
                return None, 0.0

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.warning(f"无法打开视频: {video_path}")
                return None, 0.0

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0.0

            # 确定时间范围
            t_start, t_end = 0.0, duration
            if time_range:
                t_start = time_range.get("start", 0.0)
                t_end = time_range.get("end", duration)

            # 根据 position 确定要提取的帧时间
            if position == "start":
                target_time = t_start
            elif position == "middle":
                target_time = (t_start + t_end) / 2
            elif position == "end":
                target_time = t_end
            else:  # any - 取中间帧
                target_time = (t_start + t_end) / 2

            target_time = max(t_start, min(t_end, target_time))

            cap.set(cv2.CAP_PROP_POS_MSEC, target_time * 1000)
            ret, frame = cap.read()
            if ret:
                self._last_frame = frame
                return frame, target_time

            return None, 0.0
        except Exception as e:
            logger.warning(f"提取视频帧异常: {e}")
            return None, 0.0
        finally:
            if cap is not None:
                cap.release()

    def _crop_element_region(
        self,
        frame: np.ndarray,
        bbox: Dict[str, int],
    ) -> np.ndarray:
        """根据元素边界框截取区域"""
        x = max(0, bbox["x"])
        y = max(0, bbox["y"])
        w = bbox["w"]
        h = bbox["h"]
        h_fr, w_fr = frame.shape[:2]
        x2 = min(x + w, w_fr)
        y2 = min(y + h, h_fr)
        return frame[y:y2, x:x2]

    def _template_match(
        self,
        frame: np.ndarray,
        reference_img: np.ndarray,
    ) -> tuple[float, Optional[Dict[str, int]]]:
        """使用 TM_CCORR_NORMED 执行模板匹配"""
        frame_h, frame_w = frame.shape[:2]
        ref_h, ref_w = reference_img.shape[:2]

        if frame_h != ref_h or frame_w != ref_w:
            x1 = max(0, (frame_w - ref_w) // 2)
            y1 = max(0, (frame_h - ref_h) // 2)
            x2 = x1 + ref_w
            y2 = y1 + ref_h
            frame = frame[y1:y2, x1:x2]

        if len(frame.shape) == 3:
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            frame_gray = frame

        if len(reference_img.shape) == 3:
            reference_gray = cv2.cvtColor(reference_img, cv2.COLOR_BGR2GRAY)
        else:
            reference_gray = reference_img

        result = cv2.matchTemplate(frame_gray, reference_gray, cv2.TM_CCORR_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        similarity = float(max_val)

        location = None
        if similarity >= 0.0:
            x, y = max_loc
            location = {"x": int(x), "y": int(y), "w": int(ref_w), "h": int(ref_h)}

        return similarity, location
