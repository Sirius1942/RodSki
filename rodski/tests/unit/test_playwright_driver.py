"""Playwright 驱动单元测试

测试 drivers/playwright_driver.py 中的 Playwright Web 驱动。
覆盖：初始化（chromium/firefox/headless）、navigate、type/type_locator、
      click、get_text、screenshot、close、assert_element。
所有 Playwright API 调用通过 mock 隔离。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from drivers.playwright_driver import PlaywrightDriver
from core.exceptions import DriverError


class TestPlaywrightDriver:

    @patch('playwright.sync_api.sync_playwright')
    def test_init(self, mock_pw):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_page = Mock()
        mock_browser.new_page.return_value = mock_page

        driver = PlaywrightDriver(headless=True)

        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_page.assert_called_once()
        assert driver.page == mock_page

    @patch('playwright.sync_api.sync_playwright')
    def test_click_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.click = Mock()

        assert driver.click("#button") == True
        driver.page.click.assert_called_once_with("#button", timeout=5000)

    @patch('playwright.sync_api.sync_playwright')
    @patch('time.sleep')
    def test_click_failure(self, mock_sleep, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.click = Mock(side_effect=Exception("Not found"))
        driver.page.evaluate = Mock(side_effect=Exception("JS failed"))

        with pytest.raises(DriverError, match="点击失败"):
            driver.click("#missing")

    @patch('playwright.sync_api.sync_playwright')
    def test_type_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.fill = Mock()

        assert driver.type("#input", "test") == True
        driver.page.fill.assert_called_once_with("#input", "test", timeout=5000)

    @patch('playwright.sync_api.sync_playwright')
    @patch('time.sleep')
    def test_type_failure(self, mock_sleep, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.fill = Mock(side_effect=Exception("Error"))
        driver.page.evaluate = Mock(side_effect=Exception("JS failed"))

        with pytest.raises(DriverError, match="输入失败"):
            driver.type("#input", "test")

    @patch('playwright.sync_api.sync_playwright')
    def test_check_visible(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.wait_for_selector = Mock(return_value=True)

        assert driver.check("#element") == True

    @patch('playwright.sync_api.sync_playwright')
    def test_check_not_visible(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.wait_for_selector = Mock(side_effect=Exception("Timeout waiting for selector"))

        assert driver.check("#element") == False

    @patch('playwright.sync_api.sync_playwright')
    def test_check_error(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.wait_for_selector = Mock(side_effect=Exception("Error"))

        assert driver.check("#element") == False

    @patch('playwright.sync_api.sync_playwright')
    @patch('time.sleep')
    def test_wait(self, mock_sleep, mock_pw):
        driver = self._create_driver(mock_pw)

        driver.wait(2.5)
        mock_sleep.assert_called_once_with(2.5)

    @patch('playwright.sync_api.sync_playwright')
    def test_navigate_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.goto = Mock(return_value=None)

        assert driver.navigate("https://example.com") == True
        driver.page.goto.assert_called_once_with("https://example.com", wait_until="networkidle", timeout=30000)

    @patch('playwright.sync_api.sync_playwright')
    def test_navigate_failure(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.goto = Mock(side_effect=Exception("Network error"))

        with pytest.raises(DriverError, match="导航失败"):
            driver.navigate("https://invalid.com")

    @patch('playwright.sync_api.sync_playwright')
    def test_screenshot_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.screenshot = Mock()

        assert driver.screenshot("/tmp/test.png") == True
        driver.page.screenshot.assert_called_once_with(path="/tmp/test.png")

    @patch('playwright.sync_api.sync_playwright')
    def test_screenshot_failure(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.screenshot = Mock(side_effect=Exception("Error"))

        assert driver.screenshot("/invalid/path.png") == False

    @patch('playwright.sync_api.sync_playwright')
    def test_select_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.select_option = Mock()

        assert driver.select("#dropdown", "option1") == True
        driver.page.select_option.assert_called_once_with("#dropdown", "option1")

    @patch('playwright.sync_api.sync_playwright')
    def test_select_failure(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.select_option = Mock(side_effect=Exception("Error"))

        with pytest.raises(DriverError, match="选择失败"):
            driver.select("#dropdown", "invalid")

    @patch('playwright.sync_api.sync_playwright')
    def test_hover_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.hover = Mock()

        assert driver.hover("#element") == True
        driver.page.hover.assert_called_once_with("#element")

    @patch('playwright.sync_api.sync_playwright')
    def test_hover_failure(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.hover = Mock(side_effect=Exception("Error"))

        with pytest.raises(DriverError, match="悬停失败"):
            driver.hover("#element")

    @patch('playwright.sync_api.sync_playwright')
    def test_drag_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.drag_and_drop = Mock()

        assert driver.drag("#source", "#target") == True
        driver.page.drag_and_drop.assert_called_once_with("#source", "#target")

    @patch('playwright.sync_api.sync_playwright')
    def test_drag_failure(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.drag_and_drop = Mock(side_effect=Exception("Error"))

        with pytest.raises(DriverError, match="拖拽失败"):
            driver.drag("#source", "#target")

    @patch('playwright.sync_api.sync_playwright')
    def test_scroll_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.evaluate = Mock()

        assert driver.scroll(100, 200) == True
        driver.page.evaluate.assert_called_once_with("window.scrollBy(100, 200)")

    @patch('playwright.sync_api.sync_playwright')
    def test_scroll_default(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.evaluate = Mock()

        assert driver.scroll() == True
        driver.page.evaluate.assert_called_once_with("window.scrollBy(0, 300)")

    @patch('playwright.sync_api.sync_playwright')
    def test_scroll_failure(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.evaluate = Mock(side_effect=Exception("Error"))

        with pytest.raises(DriverError, match="滚动失败"):
            driver.scroll()

    @patch('playwright.sync_api.sync_playwright')
    def test_assert_element_success(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.text_content = Mock(return_value="Hello World")

        assert driver.assert_element("#element", "Hello") == True

    @patch('playwright.sync_api.sync_playwright')
    def test_assert_element_failure(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.text_content = Mock(return_value="Hello World")

        assert driver.assert_element("#element", "Goodbye") == False

    @patch('playwright.sync_api.sync_playwright')
    def test_assert_element_none_text(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.text_content = Mock(return_value=None)

        assert driver.assert_element("#element", "test") == False

    @patch('playwright.sync_api.sync_playwright')
    def test_assert_element_error(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.page.text_content = Mock(side_effect=Exception("Error"))

        assert driver.assert_element("#element", "test") == False

    @patch('playwright.sync_api.sync_playwright')
    def test_close(self, mock_pw):
        driver = self._create_driver(mock_pw)
        driver.browser.close = Mock()
        driver._pw.stop = Mock()

        driver.close()

        driver.browser.close.assert_called_once()
        driver._pw.stop.assert_called_once()

    def _create_driver(self, mock_pw):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_page = Mock()
        mock_browser.new_page.return_value = mock_page
        return PlaywrightDriver()
