"""录制分辨率功能单元测试"""
import argparse
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path

# 确保 rodski 包可导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from drivers.playwright_driver import _resolve_video_size
from core.config_manager import DEFAULTS


class TestResolveVideoSize:
    """_resolve_video_size 辅助函数测试"""

    def test_screen_returns_valid_dict(self):
        """screen 应返回有效的 width/height 字典"""
        result = _resolve_video_size("screen")
        assert isinstance(result, dict)
        assert "width" in result
        assert "height" in result
        assert isinstance(result["width"], int)
        assert isinstance(result["height"], int)
        assert result["width"] > 0
        assert result["height"] > 0

    def test_2k_returns_2560x1440(self):
        """2k 应返回 2560x1440"""
        result = _resolve_video_size("2k")
        assert result == {"width": 2560, "height": 1440}

    def test_hd_returns_1920x1080(self):
        """hd 应返回 1920x1080"""
        result = _resolve_video_size("hd")
        assert result == {"width": 1920, "height": 1080}

    def test_custom_wxh(self):
        """WxH 格式应正确解析"""
        result = _resolve_video_size("1280x720")
        assert result == {"width": 1280, "height": 720}

    def test_custom_wxh_large(self):
        """大分辨率 WxH 格式应正确解析"""
        result = _resolve_video_size("3840x2160")
        assert result == {"width": 3840, "height": 2160}

    def test_invalid_empty_string_raises(self):
        """空字符串应抛出 ValueError"""
        with pytest.raises(ValueError):
            _resolve_video_size("")

    def test_invalid_none_raises(self):
        """None 应抛出 ValueError"""
        with pytest.raises(ValueError):
            _resolve_video_size(None)

    def test_invalid_random_string_raises(self):
        """无效字符串应抛出 ValueError"""
        with pytest.raises(ValueError):
            _resolve_video_size("invalid")

    def test_invalid_partial_format_raises(self):
        """不完整的 WxH 格式应抛出 ValueError"""
        with pytest.raises(ValueError):
            _resolve_video_size("1920x")

    def test_invalid_zero_dimension_raises(self):
        """宽高为 0 应抛出 ValueError"""
        with pytest.raises(ValueError):
            _resolve_video_size("0x1080")

    def test_case_insensitive(self):
        """应不区分大小写"""
        assert _resolve_video_size("HD") == {"width": 1920, "height": 1080}
        assert _resolve_video_size("2K") == {"width": 2560, "height": 1440}
        assert _resolve_video_size("Screen") == _resolve_video_size("screen")

    def test_screen_fallback_when_mss_unavailable(self):
        """当 mss 不可用时应回退到 1920x1080"""
        with patch.dict("sys.modules", {"mss": None}):
            # 强制 import 失败
            with patch("builtins.__import__", side_effect=lambda name, *a, **kw: (_ for _ in ()).throw(ImportError()) if name == "mss" else __builtins__.__import__(name, *a, **kw)):
                result = _resolve_video_size("screen")
                assert result["width"] > 0
                assert result["height"] > 0


class TestConfigDefault:
    """配置默认值测试"""

    def test_recording_video_size_default(self):
        """DEFAULTS 中 recording.video_size 默认值应为 screen"""
        recording = DEFAULTS.get("recording", {})
        assert "video_size" in recording
        assert recording["video_size"] == "screen"


class TestCLIRecordResolution:
    """CLI --record-resolution 参数测试"""

    def test_parser_accepts_record_resolution(self):
        """argparse 应能解析 --record-resolution 参数"""
        from rodski_cli.run import setup_parser

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        setup_parser(subparsers)

        args = parser.parse_args(["run", "case/", "--record", "--record-resolution", "2k"])
        assert args.record_resolution == "2k"

    def test_parser_record_resolution_default_none(self):
        """--record-resolution 未指定时应为 None"""
        from rodski_cli.run import setup_parser

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        setup_parser(subparsers)

        args = parser.parse_args(["run", "case/", "--record"])
        assert args.record_resolution is None

    def test_apply_recording_args_with_resolution(self):
        """_apply_recording_args 应将 record_resolution 写入 recording.video_size"""
        from rodski_cli.run import _apply_recording_args

        config = MagicMock()
        config.get.return_value = {"enabled": False, "video_size": "screen"}
        config.config = {}

        args = argparse.Namespace(
            record=True,
            record_mode=None,
            record_scope=None,
            record_monitor=None,
            record_resolution="2k",
        )
        _apply_recording_args(config, args)
        assert config.config["recording"]["video_size"] == "2k"

    def test_apply_recording_args_without_resolution(self):
        """_apply_recording_args 未指定 resolution 时不覆盖配置"""
        from rodski_cli.run import _apply_recording_args

        config = MagicMock()
        config.get.return_value = {"enabled": False, "video_size": "screen"}
        config.config = {}

        args = argparse.Namespace(
            record=True,
            record_mode=None,
            record_scope=None,
            record_monitor=None,
            record_resolution=None,
        )
        _apply_recording_args(config, args)
        assert config.config["recording"]["video_size"] == "screen"
