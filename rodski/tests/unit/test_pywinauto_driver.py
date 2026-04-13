"""Pywinauto 驱动单元测试

测试 drivers/pywinauto_driver.py 中的 Windows 桌面驱动。
覆盖：初始化、窗口查找、控件操作（click/type）、
      截图、平台检查（仅 Windows）。
所有 pywinauto 调用通过 mock 隔离。
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock pywinauto and pyautogui modules before importing driver
mock_pywinauto = MagicMock()
mock_pyautogui = MagicMock()
sys.modules['pywinauto'] = mock_pywinauto
sys.modules['pywinauto.Application'] = MagicMock()
sys.modules['pyautogui'] = mock_pyautogui

from drivers.pywinauto_driver import PywinautoDriver


class TestPywinautoDriver:
    """PywinautoDriver 单元测试

    PywinautoDriver 使用坐标操作（x, y），底层依赖 pyautogui。
    所有操作方法返回 None（非 bool）。
    """

    def setup_method(self):
        """每个测试前重置 pyautogui mock"""
        mock_pyautogui.reset_mock()

    # ── 构造函数测试 ──────────────────────────────────────────────────

    def test_init_no_app(self):
        """无 app_path 时，driver.app 应为 None"""
        driver = PywinautoDriver()
        assert driver.app is None

    def test_init_with_app(self):
        """提供 app_path 时，应调用 Application().connect(path=...)"""
        mock_app_class = MagicMock()
        mock_instance = Mock()
        mock_app_class.return_value.connect.return_value = mock_instance
        mock_pywinauto.Application = mock_app_class

        driver = PywinautoDriver(app_path="notepad.exe")

        mock_app_class.return_value.connect.assert_called_once_with(path="notepad.exe")
        assert driver.app == mock_instance

    def test_init_import_error(self):
        """pywinauto 未安装时应抛出 ImportError"""
        # 临时移除 pywinauto mock 以模拟未安装状态
        saved = sys.modules.get('pywinauto')
        try:
            # 让 import 抛出 ImportError
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == 'pywinauto':
                    raise ImportError("No module named 'pywinauto'")
                return original_import(name, *args, **kwargs)

            # 需要重新加载模块才能触发 __init__ 中的 import
            # 由于 pywinauto 是在 __init__ 内部 import 的，我们需要 patch
            with patch.dict(sys.modules, {'pywinauto': None}):
                with patch('builtins.__import__', side_effect=mock_import):
                    with pytest.raises(ImportError, match="pywinauto not installed"):
                        # 需要强制重新执行 __init__
                        import importlib
                        import drivers.pywinauto_driver as mod
                        importlib.reload(mod)
                        mod.PywinautoDriver()
        finally:
            # 恢复 mock
            if saved is not None:
                sys.modules['pywinauto'] = saved

    # ── click 测试 ────────────────────────────────────────────────────

    def test_click(self):
        """click(x, y) 应调用 pyautogui.click(x, y)"""
        driver = PywinautoDriver()
        driver.click(100, 200)

        import pyautogui
        pyautogui.click.assert_called_with(100, 200)

    def test_click_returns_none(self):
        """click 返回值应为 None"""
        driver = PywinautoDriver()
        result = driver.click(100, 200)
        assert result is None

    # ── type_text 测试 ────────────────────────────────────────────────

    def test_type_text(self):
        """type_text(x, y, text) 应先点击坐标再输入文字"""
        driver = PywinautoDriver()
        driver.type_text(100, 200, "hello world")

        import pyautogui
        pyautogui.click.assert_called_with(100, 200)
        pyautogui.typewrite.assert_called_with("hello world")

    def test_type_text_returns_none(self):
        """type_text 返回值应为 None"""
        driver = PywinautoDriver()
        result = driver.type_text(100, 200, "text")
        assert result is None

    # ── get_text 测试 ─────────────────────────────────────────────────

    def test_get_text(self):
        """get_text(x1, y1, x2, y2) 应返回空字符串（当前实现）"""
        driver = PywinautoDriver()
        result = driver.get_text(0, 0, 100, 100)
        assert result == ""

    def test_get_text_returns_str(self):
        """get_text 始终返回 str 类型"""
        driver = PywinautoDriver()
        result = driver.get_text(10, 20, 30, 40)
        assert isinstance(result, str)

    # ── take_screenshot 测试 ──────────────────────────────────────────

    def test_take_screenshot_success(self):
        """截图成功时应返回文件路径"""
        driver = PywinautoDriver()
        mock_window = Mock()
        mock_image = Mock()
        driver.app = Mock()
        driver.app.top_window.return_value = mock_window
        mock_window.capture_as_image.return_value = mock_image

        result = driver.take_screenshot()

        assert result != ""
        assert result.endswith('.png')
        mock_image.save.assert_called_once()

    def test_take_screenshot_failure(self):
        """截图失败时应返回空字符串"""
        driver = PywinautoDriver()
        driver.app = Mock()
        driver.app.top_window.side_effect = Exception("Window not found")

        result = driver.take_screenshot()

        assert result == ""

    def test_take_screenshot_no_app(self):
        """app 为 None 时截图应返回空字符串"""
        driver = PywinautoDriver()
        driver.app = None

        result = driver.take_screenshot()

        assert result == ""

    # ── double_click 测试 ─────────────────────────────────────────────

    def test_double_click(self):
        """double_click(x, y) 应调用 pyautogui.doubleClick(x, y)"""
        driver = PywinautoDriver()
        driver.double_click(150, 250)

        import pyautogui
        pyautogui.doubleClick.assert_called_with(150, 250)

    def test_double_click_returns_none(self):
        """double_click 返回值应为 None"""
        driver = PywinautoDriver()
        result = driver.double_click(150, 250)
        assert result is None

    # ── right_click 测试 ──────────────────────────────────────────────

    def test_right_click(self):
        """right_click(x, y) 应调用 pyautogui.rightClick(x, y)"""
        driver = PywinautoDriver()
        driver.right_click(300, 400)

        import pyautogui
        pyautogui.rightClick.assert_called_with(300, 400)

    def test_right_click_returns_none(self):
        """right_click 返回值应为 None"""
        driver = PywinautoDriver()
        result = driver.right_click(300, 400)
        assert result is None

    # ── hover 测试 ────────────────────────────────────────────────────

    def test_hover(self):
        """hover(x, y) 应调用 pyautogui.moveTo(x, y)"""
        driver = PywinautoDriver()
        driver.hover(500, 600)

        import pyautogui
        pyautogui.moveTo.assert_called_with(500, 600)

    def test_hover_returns_none(self):
        """hover 返回值应为 None"""
        driver = PywinautoDriver()
        result = driver.hover(500, 600)
        assert result is None

    # ── scroll 测试 ───────────────────────────────────────────────────

    def test_scroll(self):
        """scroll(x, y) 应将 y 转换为 clicks 并调用 pyautogui.scroll"""
        driver = PywinautoDriver()
        driver.scroll(0, 240)

        import pyautogui
        # clicks = -int(240 / 120) = -2
        pyautogui.scroll.assert_called_with(-2)

    def test_scroll_negative(self):
        """向上滚动时 clicks 应为正值"""
        driver = PywinautoDriver()
        driver.scroll(0, -360)

        import pyautogui
        # clicks = -int(-360 / 120) = -(-3) = 3
        pyautogui.scroll.assert_called_with(3)

    def test_scroll_returns_none(self):
        """scroll 返回值应为 None"""
        driver = PywinautoDriver()
        result = driver.scroll(0, 120)
        assert result is None

    # ── close 测试 ────────────────────────────────────────────────────

    def test_close_with_app(self):
        """有 app 时 close 应调用 app.kill()"""
        driver = PywinautoDriver()
        driver.app = Mock()

        driver.close()

        driver.app.kill.assert_called_once()

    def test_close_without_app(self):
        """app 为 None 时 close 不应报错"""
        driver = PywinautoDriver()
        driver.app = None

        driver.close()  # 不应抛出异常

    # ── launch 测试 ───────────────────────────────────────────────────

    def test_launch(self):
        """launch 当前为空实现，不应抛出异常"""
        driver = PywinautoDriver()
        result = driver.launch()
        assert result is None

    # ── locate_element 测试 ───────────────────────────────────────────

    def test_locate_element(self):
        """locate_element 当前实现始终返回 None"""
        driver = PywinautoDriver()
        result = driver.locate_element("id", "some_element")
        assert result is None

    # ── wait 测试（继承自 BaseDriver）────────────────────────────────

    @patch('time.sleep')
    def test_wait(self, mock_sleep):
        """wait 应调用 time.sleep"""
        driver = PywinautoDriver()
        driver.wait(1.5)

        mock_sleep.assert_called_once_with(1.5)
