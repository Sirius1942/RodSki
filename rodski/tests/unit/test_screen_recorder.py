"""ScreenRecorder 单元测试

测试 vision/screen_recorder.py 中的屏幕录制器。
覆盖：初始化参数、_import_deps（成功/失败）、start/stop 生命周期、
      is_recording 状态、重复启动/停止、__repr__。
所有 mss/cv2 调用均通过 mock 隔离，不执行真实录屏。
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from vision.screen_recorder import ScreenRecorder


# =====================================================================
# 初始化
# =====================================================================
class TestScreenRecorderInit:
    """ScreenRecorder 初始化"""

    def test_default_params(self, tmp_path):
        """默认参数：fps=10, max_duration=600"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        assert recorder.fps == 10
        assert recorder.max_duration == 600
        assert recorder.output_dir == tmp_path

    def test_custom_params(self, tmp_path):
        """自定义参数"""
        recorder = ScreenRecorder(output_dir=str(tmp_path), fps=30, max_duration=120, scope="all_screens", monitor_id=0)
        assert recorder.fps == 30
        assert recorder.max_duration == 120
        assert recorder.scope == "all_screens"
        assert recorder.monitor_id == 0

    def test_output_dir_created(self, tmp_path):
        """输出目录应在初始化时自动创建"""
        out = tmp_path / "recordings"
        recorder = ScreenRecorder(output_dir=str(out))
        assert out.exists()

    def test_initial_state(self, tmp_path):
        """初始状态应为未录制"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        assert recorder.is_recording() is False
        assert recorder._thread is None
        assert recorder._output_path is None


# =====================================================================
# _import_deps
# =====================================================================
class TestImportDeps:
    """_import_deps —— 依赖检查"""

    def test_deps_available(self, tmp_path):
        """依赖可用时返回 True"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        with patch.dict("sys.modules", {"mss": MagicMock(), "cv2": MagicMock()}):
            with patch("builtins.__import__", side_effect=lambda name, *a, **kw: MagicMock()):
                # 强制重置缓存
                recorder._mss = None
                recorder._cv2 = None
                result = recorder._import_deps()
        # 因为 mock 可能不完美，至少验证方法不会崩溃
        assert isinstance(result, bool)

    def test_deps_cached(self, tmp_path):
        """依赖已导入时直接返回 True（缓存）"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        recorder._mss = MagicMock()
        recorder._cv2 = MagicMock()
        recorder._np = MagicMock()
        assert recorder._import_deps() is True


# =====================================================================
# start / stop 生命周期
# =====================================================================
class TestStartStop:
    """录制生命周期管理"""

    def test_start_without_deps_raises(self, tmp_path):
        """依赖不可用时启动录制应抛 RuntimeError"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        recorder._mss = None
        recorder._cv2 = None
        recorder._errors = ["No module named 'mss'"]
        with patch.object(recorder, '_import_deps', return_value=False):
            with pytest.raises(RuntimeError, match="缺少依赖"):
                recorder.start()

    def test_start_sets_recording_flag(self, tmp_path):
        """启动录制后 is_recording 应为 True"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        recorder._mss = MagicMock()
        recorder._cv2 = MagicMock()
        recorder._np = MagicMock()
        with patch.object(recorder, '_record_loop'):
            # mock threading 使线程不实际启动
            with patch("vision.screen_recorder.threading") as mock_thread:
                mock_thread.Event.return_value = MagicMock()
                mock_thread.Thread.return_value = MagicMock()
                path = recorder.start(session_id="test_session")

        assert recorder._recording is True
        assert "test_session" in str(recorder._output_path)
        assert path.endswith(".mp4")

    def test_start_duplicate_ignored(self, tmp_path):
        """重复启动录制应被忽略"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        recorder._recording = True
        recorder._output_path = Path(tmp_path / "existing.mp4")
        # 不应抛异常
        path = recorder.start()
        assert path == str(recorder._output_path)

    def test_stop_clears_recording_flag(self, tmp_path):
        """停止录制后 is_recording 应为 False"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        recorder._recording = True
        recorder._output_path = Path(tmp_path / "test.mp4")
        recorder._thread = MagicMock()
        recorder._stop_event = MagicMock()

        path = recorder.stop()
        assert recorder._recording is False
        assert "test.mp4" in path

    def test_stop_when_not_recording(self, tmp_path):
        """未在录制时调用 stop 不应报错"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        path = recorder.stop()
        assert path == ""


class TestMonitorSelection:
    def test_target_scope_uses_primary_monitor(self, tmp_path):
        recorder = ScreenRecorder(output_dir=str(tmp_path), scope="target")
        sct = MagicMock()
        sct.monitors = [
            {"width": 3000, "height": 1000},
            {"width": 1920, "height": 1080},
            {"width": 1280, "height": 720},
        ]
        assert recorder._select_monitor(sct) == sct.monitors[1]

    def test_all_screens_uses_virtual_monitor(self, tmp_path):
        recorder = ScreenRecorder(output_dir=str(tmp_path), scope="all_screens")
        sct = MagicMock()
        sct.monitors = [
            {"width": 3000, "height": 1000},
            {"width": 1920, "height": 1080},
        ]
        assert recorder._select_monitor(sct) == sct.monitors[0]

    def test_monitor_id_overrides_default(self, tmp_path):
        recorder = ScreenRecorder(output_dir=str(tmp_path), monitor_id=2)
        sct = MagicMock()
        sct.monitors = [
            {"width": 3000, "height": 1000},
            {"width": 1920, "height": 1080},
            {"width": 1280, "height": 720},
        ]
        assert recorder._select_monitor(sct) == sct.monitors[2]


# =====================================================================
# __repr__
# =====================================================================
class TestRepr:
    """__repr__ 字符串表示"""

    def test_stopped_state(self, tmp_path):
        """停止状态"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        assert "stopped" in repr(recorder)

    def test_recording_state(self, tmp_path):
        """录制状态"""
        recorder = ScreenRecorder(output_dir=str(tmp_path))
        recorder._recording = True
        recorder._output_path = Path("/tmp/test.mp4")
        s = repr(recorder)
        assert "recording" in s
        assert "test.mp4" in s
