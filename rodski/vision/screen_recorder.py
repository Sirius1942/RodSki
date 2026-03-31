"""屏幕录制器 - 基于 mss + opencv-python 的跨平台录屏工具

支持 macOS / Windows / Linux，在测试执行期间自动录制屏幕，出问题时可通过录像回放分析。
"""
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rodski")


class ScreenRecorder:
    """屏幕录制器，支持 macOS / Windows / Linux

    使用 mss 进行屏幕截图，opencv-python 编码为 MP4 视频。
    录制在独立线程中执行，不阻塞主测试流程。

    Args:
        output_dir: 录像输出目录，默认 "screenshots/"
        fps: 录制帧率，默认 10
        max_duration: 最大录制时长（秒），默认 600（10分钟）
    """

    def __init__(
        self,
        output_dir: str = "screenshots/",
        fps: int = 10,
        max_duration: int = 600,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.max_duration = max_duration

        self._recording = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._output_path: Optional[Path] = None
        self._session_id: Optional[str] = None

        # 延迟导入，避免在未安装时立即报错
        self._mss = None
        self._cv2 = None
        self._errors: list = []

    def _import_deps(self) -> bool:
        """尝试导入依赖，返回是否成功"""
        if self._mss is not None and self._cv2 is not None:
            return True
        try:
            import mss
            import cv2
            self._mss = mss
            self._cv2 = cv2
            return True
        except ImportError as e:
            self._errors.append(str(e))
            logger.warning(
                f"屏幕录制功能不可用，缺少依赖: {e}。"
                "请安装: pip install mss opencv-python"
            )
            return False

    def is_recording(self) -> bool:
        """是否正在录制"""
        return self._recording

    def start(self, session_id: Optional[str] = None) -> str:
        """开始录制

        Args:
            session_id: 会话标识，用于生成文件名，默认使用时间戳

        Returns:
            录像文件路径

        Raises:
            RuntimeError: 无法启动录制时抛出
        """
        if self._recording:
            logger.warning("屏幕录制已在进行中，忽略重复启动请求")
            return str(self._output_path) if self._output_path else ""

        if not self._import_deps():
            raise RuntimeError(
                f"屏幕录制启动失败，缺少依赖: {'; '.join(self._errors)}"
            )

        self._session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._output_path = self.output_dir / f"recording_{self._session_id}.mp4"

        self._recording = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

        logger.info(f"屏幕录制已启动: {self._output_path}")
        return str(self._output_path)

    def stop(self) -> str:
        """停止录制

        Returns:
            录像文件路径
        """
        if not self._recording:
            logger.warning("屏幕录制未在进行中，忽略停止请求")
            return str(self._output_path) if self._output_path else ""

        logger.info("正在停止屏幕录制...")
        self._recording = False
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

        output = str(self._output_path) if self._output_path else ""
        logger.info(f"屏幕录制已保存: {output}")
        return output

    def _record_loop(self) -> None:
        """录制主循环，在独立线程中运行"""
        try:
            with self._mss.mss() as sct:
                monitor = sct.monitors[0]  # 全屏
                # 获取屏幕尺寸
                screen_w = monitor["width"]
                screen_h = monitor["height"]

                # 计算视频写入器参数
                # 使用 H.264 编码 (mp4v 或 avc1)
                fourcc = self._cv2.VideoWriter_fourcc(*"mp4v")
                writer = self._cv2.VideoWriter(
                    str(self._output_path),
                    fourcc,
                    self.fps,
                    (screen_w, screen_h),
                )

                if not writer.isOpened():
                    # 回退方案：尝试 XVID
                    fourcc = self._cv2.VideoWriter_fourcc(*"XVID")
                    writer = self._cv2.VideoWriter(
                        str(self._output_path),
                        fourcc,
                        self.fps,
                        (screen_w, screen_h),
                    )

                if not writer.isOpened():
                    logger.error("无法打开视频写入器，录制失败")
                    self._recording = False
                    return

                frame_interval = 1.0 / self.fps
                start_time = time.time()
                frame_count = 0

                logger.debug(
                    f"录制线程启动: {screen_w}x{screen_h} @ {self.fps}fps"
                )

                while self._recording and not self._stop_event.is_set():
                    loop_start = time.time()

                    # 检查最大时长
                    if time.time() - start_time > self.max_duration:
                        logger.warning(
                            f"达到最大录制时长 ({self.max_duration}s)，自动停止"
                        )
                        break

                    # 截图
                    sct_img = sct.grab(monitor)
                    # 转换为 numpy 数组 (BGR 格式 for opencv)
                    img = self._cv2.cvtColor(
                        self._cv2.array_to_img(sct_img),
                        self._cv2.COLOR_BGRA2BGR,
                    )

                    writer.write(img)
                    frame_count += 1

                    # 控制帧率
                    elapsed = time.time() - loop_start
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        self._stop_event.wait(sleep_time)

                writer.release()
                elapsed = time.time() - start_time
                actual_fps = frame_count / elapsed if elapsed > 0 else 0
                logger.info(
                    f"录制完成: {frame_count} 帧, "
                    f"时长 {elapsed:.1f}s, 平均 {actual_fps:.1f}fps"
                )

        except Exception as e:
            logger.error(f"录制线程异常: {e}")
        finally:
            self._recording = False

    def __repr__(self) -> str:
        status = "recording" if self._recording else "stopped"
        path = str(self._output_path) if self._output_path else "N/A"
        return f"ScreenRecorder(status={status}, output={path})"
