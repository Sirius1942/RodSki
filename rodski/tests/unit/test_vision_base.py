"""视觉基础工具单元测试

覆盖:
  - coordinate_utils: normalized_to_pixel、bbox_str_to_coords、get_screen_size
  - screenshot: capture_web、capture_desktop、auto_cleanup

v7.1.0 起 OmniClient 已从 rodski 核心移除（由 PerceptionBackend 抽象
+ rodski-perception 插件取代）。原 ``TestOmniClient*`` 测试类一并移除；
PerceptionRegistry / Backend 的单元测试在 ``test_perception_registry.py``。

不依赖 pytest，使用 RodSki 自有 RodskiTestRunner。
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from core.test_runner import assert_raises

# ── 被测模块 ──────────────────────────────────────────────────
from vision.coordinate_utils import (
    normalized_to_pixel,
    bbox_str_to_coords,
    get_screen_size,
)
from vision.screenshot import capture_web, capture_desktop, auto_cleanup


# ═══════════════════════════════════════════════════════════════
# coordinate_utils 测试
# ═══════════════════════════════════════════════════════════════

class TestNormalizedToPixel:
    """normalized_to_pixel 正常路径与边界。"""

    def test_basic_conversion(self):
        cx, cy, x1, y1, x2, y2 = normalized_to_pixel([0.0, 0.0, 1.0, 1.0], 1920, 1080)
        assert x1 == 0 and y1 == 0
        assert x2 == 1920 and y2 == 1080
        assert cx == 960 and cy == 540

    def test_centre_point_is_midpoint(self):
        cx, cy, x1, y1, x2, y2 = normalized_to_pixel([0.1, 0.2, 0.3, 0.4], 1000, 1000)
        assert x1 == 100 and y1 == 200
        assert x2 == 300 and y2 == 400
        assert cx == 200 and cy == 300

    def test_fractional_truncation(self):
        cx, cy, x1, y1, x2, y2 = normalized_to_pixel([1/3, 1/3, 2/3, 2/3], 300, 300)
        assert isinstance(cx, int)
        assert isinstance(x1, int)

    def test_wrong_length_raises_value_error(self):
        assert_raises(ValueError, normalized_to_pixel, [0.1, 0.2, 0.3], 100, 100)
        assert_raises(ValueError, normalized_to_pixel, [0.1, 0.2, 0.3, 0.4, 0.5], 100, 100)

    def test_returns_six_values(self):
        result = normalized_to_pixel([0.1, 0.1, 0.9, 0.9], 800, 600)
        assert len(result) == 6


class TestBboxStrToCoords:
    """bbox_str_to_coords 正常路径与异常。"""

    def test_basic_parsing(self):
        cx, cy = bbox_str_to_coords("100,200,300,400")
        assert cx == 200
        assert cy == 300

    def test_float_values(self):
        cx, cy = bbox_str_to_coords("10.5,20.5,30.5,40.5")
        assert cx == 20  # int((10.5+30.5)/2)
        assert cy == 30  # int((20.5+40.5)/2)

    def test_spaces_around_values(self):
        cx, cy = bbox_str_to_coords(" 0 , 0 , 200 , 100 ")
        assert cx == 100
        assert cy == 50

    def test_wrong_field_count_raises(self):
        assert_raises(ValueError, bbox_str_to_coords, "100,200,300")
        assert_raises(ValueError, bbox_str_to_coords, "100,200,300,400,500")

    def test_non_numeric_raises(self):
        assert_raises(ValueError, bbox_str_to_coords, "a,b,c,d")

    def test_returns_two_ints(self):
        result = bbox_str_to_coords("0,0,640,480")
        assert len(result) == 2
        assert all(isinstance(v, int) for v in result)


class TestGetScreenSize:
    """get_screen_size — mock pyautogui 以保证离线可运行。"""

    def test_returns_two_positive_ints(self):
        mock_pyautogui = MagicMock()
        mock_pyautogui.size.return_value = (1920, 1080)
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.coordinate_utils as cu
            importlib.reload(cu)
            w, h = cu.get_screen_size()
        assert isinstance(w, int) and isinstance(h, int)
        assert w > 0 and h > 0

    def test_values_match_mock(self):
        mock_pyautogui = MagicMock()
        mock_pyautogui.size.return_value = (2560, 1440)
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.coordinate_utils as cu
            importlib.reload(cu)
            w, h = cu.get_screen_size()
        assert w == 2560
        assert h == 1440


# ═══════════════════════════════════════════════════════════════
# screenshot 测试
# ═══════════════════════════════════════════════════════════════

class TestCaptureWeb:
    """capture_web — selenium driver mock。"""

    def test_returns_absolute_path(self, tmp_path):
        driver = Mock()
        driver.save_screenshot.return_value = True
        out = tmp_path / "web_shot.png"
        result = capture_web(driver, str(out))
        assert os.path.isabs(result)

    def test_calls_save_screenshot(self, tmp_path):
        driver = Mock()
        driver.save_screenshot.return_value = True
        out = tmp_path / "web_shot.png"
        capture_web(driver, str(out))
        driver.save_screenshot.assert_called_once()

    def test_creates_parent_directory(self, tmp_path):
        driver = Mock()
        driver.save_screenshot.return_value = True
        out = tmp_path / "nested" / "dir" / "shot.png"
        capture_web(driver, str(out))
        assert out.parent.exists()

    def test_raises_on_driver_failure(self, tmp_path):
        driver = Mock()
        driver.save_screenshot.return_value = False
        out = tmp_path / "shot.png"
        assert_raises(RuntimeError, capture_web, driver, str(out))


class TestCaptureDesktop:
    """capture_desktop — mock pyautogui.screenshot。"""

    def test_returns_absolute_path(self, tmp_path):
        mock_img = Mock()
        mock_img.save = Mock()
        mock_pyautogui = MagicMock()
        mock_pyautogui.screenshot.return_value = mock_img
        out = tmp_path / "desktop_shot.png"
        def _fake_save(path):
            Path(path).touch()
        mock_img.save.side_effect = _fake_save
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.screenshot as ss
            importlib.reload(ss)
            result = ss.capture_desktop(str(out))
        assert os.path.isabs(result)

    def test_calls_pyautogui_screenshot(self, tmp_path):
        mock_img = Mock()
        def _fake_save(path):
            Path(path).touch()
        mock_img.save.side_effect = _fake_save
        mock_pyautogui = MagicMock()
        mock_pyautogui.screenshot.return_value = mock_img
        out = tmp_path / "shot.png"
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.screenshot as ss
            importlib.reload(ss)
            ss.capture_desktop(str(out))
        mock_pyautogui.screenshot.assert_called_once()

    def test_creates_parent_directory(self, tmp_path):
        mock_img = Mock()
        def _fake_save(path):
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
        mock_img.save.side_effect = _fake_save
        mock_pyautogui = MagicMock()
        mock_pyautogui.screenshot.return_value = mock_img
        out = tmp_path / "sub" / "shot.png"
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            import importlib
            import vision.screenshot as ss
            importlib.reload(ss)
            ss.capture_desktop(str(out))
        assert out.parent.exists()


class TestAutoCleanup:
    """auto_cleanup — 文件清理逻辑。"""

    def _write_pngs(self, directory: Path, count: int) -> list:
        files = []
        for i in range(count):
            f = directory / f"shot_{i:03d}.png"
            f.write_bytes(b"fake")
            files.append(f)
        return files

    def test_no_deletion_when_under_limit(self, tmp_path):
        self._write_pngs(tmp_path, 5)
        deleted = auto_cleanup(str(tmp_path), max_files=10)
        assert deleted == 0
        assert len(list(tmp_path.iterdir())) == 5

    def test_deletes_excess_files(self, tmp_path):
        self._write_pngs(tmp_path, 25)
        deleted = auto_cleanup(str(tmp_path), max_files=20)
        assert deleted == 5
        assert len(list(tmp_path.iterdir())) == 20

    def test_exact_limit_no_deletion(self, tmp_path):
        self._write_pngs(tmp_path, 20)
        deleted = auto_cleanup(str(tmp_path), max_files=20)
        assert deleted == 0

    def test_nonexistent_directory_returns_zero(self, tmp_path):
        deleted = auto_cleanup(str(tmp_path / "no_such_dir"), max_files=10)
        assert deleted == 0

    def test_invalid_max_files_raises(self, tmp_path):
        assert_raises(ValueError, auto_cleanup, str(tmp_path), 0)
        assert_raises(ValueError, auto_cleanup, str(tmp_path), -1)

    def test_non_image_files_not_deleted(self, tmp_path):
        self._write_pngs(tmp_path, 25)
        for i in range(5):
            (tmp_path / f"log_{i}.txt").write_text("log")
        deleted = auto_cleanup(str(tmp_path), max_files=20)
        assert deleted == 5
        txt_files = list(tmp_path.glob("*.txt"))
        assert len(txt_files) == 5

    def test_keeps_newest_files(self, tmp_path):
        import time
        files = self._write_pngs(tmp_path, 5)
        newest = files[-1]
        time.sleep(0.01)
        newest.write_bytes(b"newer")
        deleted = auto_cleanup(str(tmp_path), max_files=4)
        assert deleted == 1
        assert newest.exists()
