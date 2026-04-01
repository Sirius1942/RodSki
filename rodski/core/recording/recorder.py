"""录屏器 - 集成 Playwright 录屏能力"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("rodski")


class Recorder:
    """录屏器

    基于 Playwright 的视频录制能力，在断言失败时自动录制短视频。
    配置项（通过 global_vars 传入）:
    - recording.enabled: bool，是否启用录屏，默认 True
    - recording.output_dir: str，录屏输出目录，默认 images/assert/recordings
    - recording.duration: int，录屏时长（秒），默认 5
    - recording.format: str，录屏格式，默认 mp4
    """

    DEFAULT_CONFIG = {
        "enabled": True,
        "output_dir": "images/assert/recordings",
        "duration": 5,
        "format": "mp4",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._active_recordings: Dict[str, str] = {}  # case_id -> output_path
        self._output_dir = Path(self._config["output_dir"])
        self._playwright_page: Optional[Any] = None
        self._recording_start_time: Optional[float] = None

    @property
    def enabled(self) -> bool:
        return self._config.get("enabled", True)

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def ensure_output_dir(self) -> None:
        """确保输出目录存在"""
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def start_recording(self, case_id: str, page: Any) -> Optional[str]:
        """开始录屏

        Args:
            case_id: 用例唯一标识
            page: Playwright page 对象

        Returns:
            录屏文件路径，失败返回 None
        """
        if not self.enabled:
            return None

        try:
            self.ensure_output_dir()
            self._playwright_page = page

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"recording_{timestamp}_{case_id}.{self._config['format']}"
            output_path = str(self._output_dir / filename)

            # Playwright 录屏
            page.start_recording_video(output_path, duration=self._config.get("duration", 5))
            self._active_recordings[case_id] = output_path
            self._recording_start_time = time.time()
            logger.info(f"开始录屏: {output_path}")
            return output_path
        except Exception as e:
            logger.warning(f"开始录屏失败: {e}")
            return None

    def stop_recording(self, case_id: str) -> Optional[str]:
        """停止录屏

        Args:
            case_id: 用例唯一标识

        Returns:
            录屏文件路径，失败返回 None
        """
        if case_id not in self._active_recordings:
            return None

        try:
            if self._playwright_page is not None:
                self._playwright_page.stop_recording_video()
                path = self._active_recordings.pop(case_id)
                elapsed = time.time() - self._recording_start_time if self._recording_start_time else 0
                logger.info(f"录屏完成: {path} (时长: {elapsed:.1f}s)")
                return path
        except Exception as e:
            logger.warning(f"停止录屏失败: {e}")
            self._active_recordings.pop(case_id, None)

        return None

    def save_failure_recording(self, case_id: str) -> Optional[str]:
        """保存失败时的录屏（自动调用 stop）"""
        return self.stop_recording(case_id)

    def get_video_path(self, case_id: str) -> Optional[str]:
        """获取活跃录屏的文件路径"""
        return self._active_recordings.get(case_id)

    def cleanup_old_recordings(self, max_count: int = 20) -> int:
        """清理旧录屏文件，保留最近 max_count 个

        Args:
            max_count: 最多保留文件数

        Returns:
            删除的文件数量
        """
        try:
            if not self._output_dir.exists():
                return 0
            video_files = sorted(
                self._output_dir.glob(f"*.{self._config['format']}"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            removed = 0
            for f in video_files[max_count:]:
                f.unlink()
                removed += 1
            if removed:
                logger.info(f"清理旧录屏: 删除了 {removed} 个文件")
            return removed
        except Exception as e:
            logger.warning(f"清理旧录屏失败: {e}")
            return 0


# 全局单例
recorder = Recorder()
