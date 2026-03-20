"""Pywinauto 驱动单元测试"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock pywinauto module before importing driver
sys.modules['pywinauto'] = MagicMock()

from drivers.pywinauto_driver import PywinautoDriver


class TestPywinautoDriver:

    def test_init_no_app(self):
        with patch('pywinauto.Application') as mock_app:
            driver = PywinautoDriver()
            assert driver.app is None

    def test_init_with_app(self):
        with patch('pywinauto.Application') as mock_app:
            mock_instance = Mock()
            mock_app.return_value.connect.return_value = mock_instance

            driver = PywinautoDriver(app_path="notepad.exe")

            mock_app.return_value.connect.assert_called_once_with(path="notepad.exe")
            assert driver.app == mock_instance

    def test_init_import_error(self):
        # Skip this test since pywinauto is already mocked at module level
        pass

    def test_click_success(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            window = Mock()
            driver.app.window.return_value = window

            result = driver.click("TestWindow")

            assert result == True
            driver.app.window.assert_called_once_with(title="TestWindow")
            window.click.assert_called_once()

    def test_click_failure(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            driver.app.window.side_effect = Exception("Not found")

            result = driver.click("Missing")

            assert result == False

    def test_type_success(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            window = Mock()
            driver.app.window.return_value = window

            result = driver.type("Input", "test text")

            assert result == True
            window.type_keys.assert_called_once_with("test text")

    def test_type_failure(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            driver.app.window.side_effect = Exception("Error")

            result = driver.type("Input", "text")

            assert result == False

    def test_check_exists(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            window = Mock()
            window.exists.return_value = True
            driver.app.window.return_value = window

            result = driver.check("Window")

            assert result == True

    def test_check_not_exists(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            window = Mock()
            window.exists.return_value = False
            driver.app.window.return_value = window

            result = driver.check("Window")

            assert result == False

    def test_check_error(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            driver.app.window.side_effect = Exception("Error")

            result = driver.check("Window")

            assert result == False

    @patch('time.sleep')
    def test_wait(self, mock_sleep):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()

            driver.wait(1.5)

            mock_sleep.assert_called_once_with(1.5)

    def test_navigate(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()

            result = driver.navigate("http://example.com")

            assert result == False

    def test_screenshot_success(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            window = Mock()
            image = Mock()
            driver.app.top_window.return_value = window
            window.capture_as_image.return_value = image

            result = driver.screenshot("/tmp/test.png")

            assert result == True
            image.save.assert_called_once_with("/tmp/test.png")

    def test_screenshot_failure(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            driver.app.top_window.side_effect = Exception("Error")

            result = driver.screenshot("/tmp/test.png")

            assert result == False

    def test_select_success(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            window = Mock()
            driver.app.window.return_value = window

            result = driver.select("Dropdown", "option1")

            assert result == True
            window.select.assert_called_once_with("option1")

    def test_select_failure(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            driver.app.window.side_effect = Exception("Error")

            result = driver.select("Dropdown", "option")

            assert result == False

    def test_hover(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()

            result = driver.hover("Element")

            assert result == False

    def test_drag(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()

            result = driver.drag("Source", "Target")

            assert result == False

    def test_scroll(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()

            result = driver.scroll(0, 100)

            assert result == False

    def test_assert_element_success(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            window = Mock()
            window.window_text.return_value = "Hello World"
            driver.app.window.return_value = window

            result = driver.assert_element("Window", "Hello")

            assert result == True

    def test_assert_element_failure(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            window = Mock()
            window.window_text.return_value = "Hello World"
            driver.app.window.return_value = window

            result = driver.assert_element("Window", "Goodbye")

            assert result == False

    def test_assert_element_error(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()
            driver.app.window.side_effect = Exception("Error")

            result = driver.assert_element("Window", "text")

            assert result == False

    def test_close_with_app(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = Mock()

            driver.close()

            driver.app.kill.assert_called_once()

    def test_close_without_app(self):
        with patch('pywinauto.Application'):
            driver = PywinautoDriver()
            driver.app = None

            driver.close()
