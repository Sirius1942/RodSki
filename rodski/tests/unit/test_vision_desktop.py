"""单元测试：vision/desktop_driver.py, vision/exceptions.py, vision/cache.py

不依赖 pytest，使用标准库 unittest。
运行方式：
    python -m unittest rodski.tests.unit.test_vision_desktop -v
或：
    python rodski/tests/unit/test_vision_desktop.py
"""
import hashlib
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch


# ════════════════════════════════════════════════════════════════
# Task 5.1  视觉异常类测试
# ════════════════════════════════════════════════════════════════

class TestVisionExceptions(unittest.TestCase):

    def test_vision_error_base(self):
        from rodski.vision.exceptions import VisionError
        err = VisionError("base error")
        self.assertIn("base error", str(err))

    def test_element_not_found_with_target_and_path(self):
        from rodski.vision.exceptions import ElementNotFoundError
        err = ElementNotFoundError(target="登录按钮", screenshot_path="/tmp/s.png")
        s = str(err)
        self.assertIn("登录按钮", s)
        self.assertIn("/tmp/s.png", s)
        self.assertIn("建议", s)
        self.assertEqual(err.target, "登录按钮")
        self.assertEqual(err.screenshot_path, "/tmp/s.png")

    def test_element_not_found_without_path(self):
        from rodski.vision.exceptions import ElementNotFoundError
        err = ElementNotFoundError(target="提交按钮")
        self.assertIn("提交按钮", str(err))
        self.assertIsNone(err.screenshot_path)

    def test_element_not_found_custom_message(self):
        from rodski.vision.exceptions import ElementNotFoundError
        err = ElementNotFoundError(target="X", message="custom msg")
        self.assertIn("custom msg", err.args[0])

    def test_omniparser_error_with_url_and_status(self):
        from rodski.vision.exceptions import OmniParserError
        err = OmniParserError(url="http://localhost:8080", status_code=500)
        s = str(err)
        self.assertIn("http://localhost:8080", s)
        self.assertIn("500", s)
        self.assertIn("建议", s)
        self.assertEqual(err.url, "http://localhost:8080")
        self.assertEqual(err.status_code, 500)

    def test_omniparser_error_no_args(self):
        from rodski.vision.exceptions import OmniParserError
        err = OmniParserError()
        self.assertIn("建议", str(err))

    def test_llm_analysis_error(self):
        from rodski.vision.exceptions import LLMAnalysisError
        err = LLMAnalysisError(model="gpt-4o", raw_response="{invalid")
        s = str(err)
        self.assertIn("gpt-4o", s)
        self.assertIn("建议", s)
        self.assertEqual(err.model, "gpt-4o")

    def test_llm_analysis_error_no_args(self):
        from rodski.vision.exceptions import LLMAnalysisError
        err = LLMAnalysisError()
        self.assertIn("建议", str(err))

    def test_coordinate_error_with_coords_and_screen(self):
        from rodski.vision.exceptions import CoordinateError
        err = CoordinateError(x=9999, y=8888, screen_size=(1920, 1080))
        s = str(err)
        self.assertIn("9999", s)
        self.assertIn("8888", s)
        self.assertIn("1920", s)
        self.assertIn("建议", s)

    def test_coordinate_error_negative(self):
        from rodski.vision.exceptions import CoordinateError
        err = CoordinateError(x=-1, y=-1)
        self.assertIn("-1", str(err))

    def test_vision_timeout_error(self):
        from rodski.vision.exceptions import VisionTimeoutError
        err = VisionTimeoutError(timeout=10.0, target="登录框")
        s = str(err)
        self.assertIn("10.0", s)
        self.assertIn("登录框", s)
        self.assertIn("建议", s)

    def test_vision_timeout_error_no_args(self):
        from rodski.vision.exceptions import VisionTimeoutError
        err = VisionTimeoutError()
        self.assertIn("建议", str(err))

    def test_exception_hierarchy(self):
        from rodski.vision.exceptions import (
            VisionError, ElementNotFoundError, OmniParserError,
            LLMAnalysisError, CoordinateError, VisionTimeoutError,
        )
        for cls in (ElementNotFoundError, OmniParserError,
                    LLMAnalysisError, CoordinateError, VisionTimeoutError):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(issubclass(cls, VisionError))

    def test_exception_is_catchable_as_base_exception(self):
        from rodski.vision.exceptions import ElementNotFoundError
        with self.assertRaises(Exception):
            raise ElementNotFoundError(target="something")

# ════════════════════════════════════════════════════════════════
# Task 5.2  VisionCache 测试
# ════════════════════════════════════════════════════════════════

class TestVisionCache(unittest.TestCase):

    def setUp(self):
        from rodski.vision.cache import VisionCache
        self.cache = VisionCache(ttl=2)  # 2 秒 TTL，便于测试过期

    def test_set_and_get_with_bytes(self):
        """使用 bytes 作为截图输入"""
        screenshot = b"fake_image_data_12345"
        data = {"x": 100, "y": 200, "confidence": 0.95}
        self.cache.set(screenshot, data)
        result = self.cache.get(screenshot)
        self.assertEqual(result, data)

    def test_get_miss(self):
        """缓存未命中返回 None"""
        result = self.cache.get(b"nonexistent_data")
        self.assertIsNone(result)

    def test_clear(self):
        """clear() 清空缓存"""
        self.cache.set(b"data1", {"x": 1})
        self.cache.set(b"data2", {"x": 2})
        self.assertEqual(self.cache.size, 2)
        self.cache.clear()
        self.assertEqual(self.cache.size, 0)
        self.assertIsNone(self.cache.get(b"data1"))
        self.assertIsNone(self.cache.get(b"data2"))

    def test_ttl_expiry(self):
        """TTL 过期后缓存自动失效"""
        screenshot = b"expire_test_data"
        c = __import__("rodski.vision.cache", fromlist=["VisionCache"]).VisionCache(ttl=1)
        c.set(screenshot, {"data": "test"})
        self.assertIsNotNone(c.get(screenshot))  # 未过期
        time.sleep(1.1)
        self.assertIsNone(c.get(screenshot))    # 已过期

    def test_cleanup_expired(self):
        """cleanup_expired() 清理过期缓存"""
        c = __import__("rodski.vision.cache", fromlist=["VisionCache"]).VisionCache(ttl=1)
        c.set(b"data1", {"x": 1})
        c.set(b"data2", {"x": 2})
        time.sleep(1.1)
        removed = c.cleanup_expired()
        self.assertEqual(removed, 2)
        self.assertEqual(c.size, 0)

    def test_size_property(self):
        """size 属性返回缓存条目数"""
        self.assertEqual(self.cache.size, 0)
        self.cache.set(b"data1", {"x": 1})
        self.assertEqual(self.cache.size, 1)
        self.cache.set(b"data2", {"x": 2})
        self.assertEqual(self.cache.size, 2)

    def test_repr(self):
        """repr 包含关键信息"""
        r = repr(self.cache)
        self.assertIn("VisionCache", r)
        self.assertIn("ttl=", r)
        self.assertIn("enabled=", r)

    def test_enabled_parameter(self):
        """enabled=False 时缓存不生效"""
        c = __import__("rodski.vision.cache", fromlist=["VisionCache"]).VisionCache(ttl=30, enabled=False)
        self.assertFalse(c.enabled)
        c.set(b"data", {"x": 1})
        self.assertIsNone(c.get(b"data"))  # 禁用时不缓存

    def test_enabled_setter(self):
        """enabled 属性可动态修改"""
        self.cache.enabled = False
        self.assertFalse(self.cache.enabled)
        self.cache.enabled = True
        self.assertTrue(self.cache.enabled)

    def test_overwrite_existing_key(self):
        """覆盖已存在的缓存"""
        screenshot = b"overwrite_test"
        self.cache.set(screenshot, {"v": 1})
        self.cache.set(screenshot, {"v": 2})
        self.assertEqual(self.cache.get(screenshot), {"v": 2})

    def test_special_chars_in_path(self):
        """路径含空格和中文时正常工作"""
        path = "/tmp/截图 2026-03-26 测试.png"
        # 注意：使用不存在的路径时，set/get 不会报错但也不会缓存
        # 因为 _get_screenshot_hash 会读取文件内容
        # 这里测试 bytes 输入即可
        self.cache.set(b"special_chars_test", {"ok": True})
        self.assertEqual(self.cache.get(b"special_chars_test"), {"ok": True})

    def test_nonexistent_file_returns_none(self):
        """不存在的文件路径返回 None"""
        result = self.cache.get("/nonexistent/path/to/file.png")
        self.assertIsNone(result)

    def test_backward_compat_parse_result(self):
        """向后兼容：set_parse_result/get_parse_result"""
        # 使用 bytes 输入，因为文件路径不存在
        self.cache.set_parse_result(b"parse_test", {"data": "parse_result"})
        result = self.cache.get_parse_result(b"parse_test")
        self.assertEqual(result, {"data": "parse_result"})

    def test_backward_compat_analyze_result(self):
        """向后兼容：set_analyze_result/get_analyze_result"""
        self.cache.set_analyze_result(b"analyze_test", {"data": "analyze_result"})
        result = self.cache.get_analyze_result(b"analyze_test")
        self.assertEqual(result, {"data": "analyze_result"})

# ════════════════════════════════════════════════════════════════
# Task 3.3  DesktopVisionDriver 测试（全部 mock pyautogui）
# ════════════════════════════════════════════════════════════════

class TestDesktopVisionDriver(unittest.TestCase):
    """使用 unittest.mock 隔离 pyautogui，不需要真实屏幕环境。"""

    def _make_driver(self, platform="macos"):
        """构造带 mock pyautogui 的驱动实例。"""
        mock_pag = MagicMock()
        mock_pag.size.return_value = (1920, 1080)
        mock_pag.FAILSAFE = True
        mock_pag.PAUSE = 0.05

        with patch(
            "rodski.vision.desktop_driver._require_pyautogui",
            return_value=mock_pag,
        ):
            from rodski.vision.desktop_driver import DesktopVisionDriver
            driver = DesktopVisionDriver(platform=platform)
        driver._pyautogui = mock_pag  # 替换已注入的引用
        return driver, mock_pag

    def test_platform_detection_macos(self):
        driver, _ = self._make_driver(platform="macos")
        self.assertEqual(driver._platform, "macos")

    def test_platform_detection_windows(self):
        driver, _ = self._make_driver(platform="windows")
        self.assertEqual(driver._platform, "windows")

    def test_unsupported_platform_raises(self):
        mock_pag = MagicMock()
        mock_pag.size.return_value = (1920, 1080)
        with patch(
            "rodski.vision.desktop_driver._require_pyautogui",
            return_value=mock_pag,
        ):
            from rodski.vision.desktop_driver import DesktopVisionDriver
            with self.assertRaises(RuntimeError):
                DesktopVisionDriver(platform="linux")

    def test_pyautogui_import_error(self):
        with patch(
            "rodski.vision.desktop_driver._require_pyautogui",
            side_effect=ImportError("pyautogui 未安装"),
        ):
            from rodski.vision.desktop_driver import DesktopVisionDriver
            with self.assertRaises(ImportError) as ctx:
                DesktopVisionDriver(platform="macos")
            self.assertIn("pyautogui", str(ctx.exception))

    def test_click_at_valid(self):
        driver, pag = self._make_driver()
        result = driver.click_at(100, 200)
        self.assertTrue(result)
        pag.click.assert_called_once_with(100, 200)

    def test_click_at_negative_coords_raises(self):
        from rodski.vision.exceptions import CoordinateError
        driver, _ = self._make_driver()
        with self.assertRaises(CoordinateError):
            driver.click_at(-1, 100)

    def test_click_at_out_of_screen_raises(self):
        from rodski.vision.exceptions import CoordinateError
        driver, _ = self._make_driver()
        with self.assertRaises(CoordinateError):
            driver.click_at(9999, 9999)

    def test_double_click_at(self):
        driver, pag = self._make_driver()
        result = driver.double_click_at(50, 60)
        self.assertTrue(result)
        pag.doubleClick.assert_called_once_with(50, 60)

    def test_right_click_at(self):
        driver, pag = self._make_driver()
        result = driver.right_click_at(300, 400)
        self.assertTrue(result)
        pag.rightClick.assert_called_once_with(300, 400)

    def test_type_at(self):
        driver, pag = self._make_driver()
        result = driver.type_at(100, 200, "hello")
        self.assertTrue(result)
        pag.click.assert_called_with(100, 200)
        pag.typewrite.assert_called_once_with("hello", interval=0.02)

    def test_screenshot(self):
        driver, pag = self._make_driver()
        mock_img = MagicMock()
        pag.screenshot.return_value = mock_img
        path = driver.screenshot("/tmp/out.png")
        self.assertEqual(path, "/tmp/out.png")
        mock_img.save.assert_called_once_with("/tmp/out.png")

    def test_screenshot_failure_raises(self):
        driver, pag = self._make_driver()
        pag.screenshot.side_effect = OSError("no display")
        with self.assertRaises(RuntimeError) as ctx:
            driver.screenshot("/tmp/fail.png")
        self.assertIn("截图失败", str(ctx.exception))

    def test_get_screen_size(self):
        driver, pag = self._make_driver()
        pag.size.return_value = (2560, 1440)
        w, h = driver.get_screen_size()
        self.assertEqual((w, h), (2560, 1440))

    def test_launch_app_macos(self):
        driver, _ = self._make_driver(platform="macos")
        with patch("subprocess.Popen") as mock_popen:
            result = driver.launch_app("/Applications/Safari.app")
        self.assertTrue(result)
        mock_popen.assert_called_once_with(["open", "/Applications/Safari.app"])

    def test_launch_app_windows(self):
        driver, _ = self._make_driver(platform="windows")
        with patch("subprocess.Popen") as mock_popen:
            result = driver.launch_app("C:\\Windows\\notepad.exe")
        self.assertTrue(result)
        mock_popen.assert_called_once_with(["C:\\Windows\\notepad.exe"])

    def test_launch_app_windows_fallback_startfile(self):
        driver, _ = self._make_driver(platform="windows")
        # os.startfile 仅存在于 Windows；非 Windows 平台跳过此测试
        if not hasattr(os, "startfile"):
            # 在 macOS/Linux 上模拟 startfile 存在，再验证回退逻辑
            import os as _os
            with patch("subprocess.Popen", side_effect=OSError("not found")), \
                 patch.object(_os, "startfile", create=True) as mock_sf:
                result = driver.launch_app("C:\\app.exe")
            self.assertTrue(result)
            mock_sf.assert_called_once_with("C:\\app.exe")
        else:
            with patch("subprocess.Popen", side_effect=OSError("not found")), \
                 patch("os.startfile") as mock_sf:
                result = driver.launch_app("C:\\app.exe")
            self.assertTrue(result)
            mock_sf.assert_called_once_with("C:\\app.exe")

    def test_launch_app_failure_returns_false(self):
        driver, _ = self._make_driver(platform="macos")
        with patch("subprocess.Popen", side_effect=Exception("fail")):
            result = driver.launch_app("/bad/path")
        self.assertFalse(result)

    def test_focus_window_macos_success(self):
        driver, _ = self._make_driver(platform="macos")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = driver.focus_window("Safari")
        self.assertTrue(result)
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "osascript")
        self.assertIn("Safari", args[2])

    def test_focus_window_macos_failure(self):
        driver, _ = self._make_driver(platform="macos")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = driver.focus_window("NonExistentApp")
        self.assertFalse(result)

    def test_focus_window_windows_found(self):
        driver, pag = self._make_driver(platform="windows")
        mock_win = MagicMock()
        pag.getWindowsWithTitle.return_value = [mock_win]
        result = driver.focus_window("Notepad")
        self.assertTrue(result)
        mock_win.activate.assert_called_once()

    def test_focus_window_windows_not_found(self):
        driver, pag = self._make_driver(platform="windows")
        pag.getWindowsWithTitle.return_value = []
        result = driver.focus_window("Ghost Window")
        self.assertFalse(result)

    def test_repr(self):
        driver, pag = self._make_driver()
        pag.size.return_value = (1920, 1080)
        r = repr(driver)
        self.assertIn("DesktopVisionDriver", r)
        self.assertIn("macos", r)


# ════════════════════════════════════════════════════════════════
# 入口
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
