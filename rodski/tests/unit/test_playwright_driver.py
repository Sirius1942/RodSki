"""Playwright 驱动单元测试

测试 drivers/playwright_driver.py 中的 Playwright Web 驱动。
覆盖：初始化（chromium/firefox/headless）、navigate、type/type_locator、
      click、get_text、screenshot、close、assert_element。
所有 Playwright API 调用通过 mock 隔离。
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
try:
    from rodski.drivers.playwright_driver import PlaywrightDriver
    from rodski.core.exceptions import DriverError
except ImportError:
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

        # 懒加载：__init__ 不启动浏览器
        assert driver.browser is None
        assert driver.page is None

        # 首次调用 _ensure_browser 才启动
        driver._ensure_browser()
        mock_playwright.chromium.launch.assert_called_once_with(
            headless=True,
            args=[
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
            ],
        )
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

    @patch('playwright.sync_api.sync_playwright')
    def test_start_case_recording_uses_context_video_dir(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        initial_page = Mock()
        mock_browser.new_page.return_value = initial_page
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_page.video = Mock()
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=True)
        target = tmp_path / "TC001.webm"
        path = driver.start_case_recording(str(tmp_path), "TC001", str(target))

        assert path == str(target)
        mock_browser.new_context.assert_called_once()
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["record_video_dir"] == str(tmp_path)
        assert "record_video_size" in call_kwargs
        mock_context.new_page.assert_called_once()
        initial_page.close.assert_called_once()
        assert driver.page == recording_page

    @patch('playwright.sync_api.sync_playwright')
    def test_start_case_recording_preserves_headed_viewport(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        initial_page = Mock()
        initial_page.evaluate.return_value = {"width": 1512, "height": 846}
        mock_browser.new_page.return_value = initial_page
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_page.video = Mock()
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=False)
        target = tmp_path / "TC001.webm"
        path = driver.start_case_recording(str(tmp_path), "TC001", str(target))

        assert path == str(target)
        mock_browser.new_context.assert_called_once()
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["record_video_dir"] == str(tmp_path)
        # headed 模式：no_viewport=True 保留原生窗口，避免 Chromium 设备模拟导致闪屏
        assert call_kwargs.get("no_viewport") is True
        assert "viewport" not in call_kwargs
        assert call_kwargs["record_video_size"] == {"width": 1512, "height": 846}
        mock_context.new_page.assert_called_once()
        initial_page.close.assert_called_once()
        assert driver.page == recording_page

    @patch('playwright.sync_api.sync_playwright')
    def test_start_case_recording_headed_screen_uses_content_size(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        initial_page = Mock()
        initial_page.evaluate.return_value = {"width": 1470, "height": 754}
        mock_browser.new_page.return_value = initial_page
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_page.video = Mock()
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=False)
        target = tmp_path / "TC001.webm"
        path = driver.start_case_recording(str(tmp_path), "TC001", str(target), video_size="screen")

        assert path == str(target)
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["record_video_size"] == {"width": 1470, "height": 754}
        assert call_kwargs.get("no_viewport") is True
        assert "viewport" not in call_kwargs
        # evaluate 被调用2次：第1次注入监控脚本，第2次测量窗口尺寸
        assert initial_page.evaluate.call_count == 2
        # 检查第2次调用是测量窗口尺寸
        last_call_args = initial_page.evaluate.call_args_list[-1][0]
        assert "window.innerWidth" in last_call_args[0]
        initial_page.close.assert_called_once()

    @patch('playwright.sync_api.sync_playwright')
    def test_start_case_recording_headed_explicit_size_is_preserved(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        initial_page = Mock()
        mock_browser.new_page.return_value = initial_page
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_page.video = Mock()
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=False)
        target = tmp_path / "TC001.webm"
        path = driver.start_case_recording(str(tmp_path), "TC001", str(target), video_size="hd")

        assert path == str(target)
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["record_video_size"] == {"width": 1920, "height": 1080}
        assert call_kwargs.get("no_viewport") is True
        assert "viewport" not in call_kwargs
        # 用户显式指定分辨率时不测量窗口，但仍会注入监控脚本（1次调用）
        assert initial_page.evaluate.call_count == 1

    @patch('playwright.sync_api.sync_playwright')
    def test_start_case_recording_headless_sets_viewport(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        initial_page = Mock()
        mock_browser.new_page.return_value = initial_page
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_page.video = Mock()
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=True)
        target = tmp_path / "TC001.webm"
        path = driver.start_case_recording(str(tmp_path), "TC001", str(target), video_size="1280x720")

        assert path == str(target)
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["record_video_size"] == {"width": 1280, "height": 720}
        assert call_kwargs["viewport"] == {"width": 1280, "height": 720}
        assert "no_viewport" not in call_kwargs
        # headless 模式下仍会注入监控脚本（1次调用）
        assert initial_page.evaluate.call_count == 1

    @patch('playwright.sync_api.sync_playwright')
    @patch('rodski.drivers.playwright_driver._resolve_video_size')
    def test_start_case_recording_headed_measure_failure_falls_back(self, mock_resolve, mock_pw, tmp_path):
        mock_resolve.return_value = {"width": 1366, "height": 768}
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        initial_page = Mock()
        initial_page.evaluate.side_effect = Exception("evaluate failed")
        initial_page.viewport_size = None
        mock_browser.new_page.return_value = initial_page
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_page.video = Mock()
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=False)
        target = tmp_path / "TC001.webm"
        path = driver.start_case_recording(str(tmp_path), "TC001", str(target))

        assert path == str(target)
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["record_video_size"] == {"width": 1366, "height": 768}
        assert call_kwargs.get("no_viewport") is True
        mock_resolve.assert_called_once_with("screen")

    @patch('playwright.sync_api.sync_playwright')
    def test_start_case_recording_headed_measures_temp_page_when_page_missing(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        initial_page = Mock()
        temp_page = Mock()
        temp_page.evaluate.return_value = {"width": 1500, "height": 760}
        mock_browser.new_page.side_effect = [initial_page, temp_page]
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_page.video = Mock()
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=False)
        driver._ensure_browser()
        driver.page = None
        target = tmp_path / "TC001.webm"
        path = driver.start_case_recording(str(tmp_path), "TC001", str(target))

        assert path == str(target)
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["record_video_size"] == {"width": 1500, "height": 760}
        mock_browser.new_page.assert_any_call(no_viewport=True)
        temp_page.close.assert_called_once()

    @patch('playwright.sync_api.sync_playwright')
    def test_stop_case_recording_saves_video(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_video = Mock()
        recording_page.video = recording_video
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=True)
        target = tmp_path / "TC001.webm"
        driver.start_case_recording(str(tmp_path), "TC001", str(target))
        path = driver.stop_case_recording("TC001", str(target))

        assert path == str(target)
        recording_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        recording_video.save_as.assert_called_once_with(str(target))

    @patch('playwright.sync_api.sync_playwright')
    def test_close_then_stop_case_recording_is_idempotent(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_video = Mock()
        recording_page.video = recording_video
        mock_context.new_page.return_value = recording_page

        driver = PlaywrightDriver(headless=True)
        target = tmp_path / "TC001.webm"
        driver.start_case_recording(str(tmp_path), "TC001", str(target))

        driver.close()
        path = driver.stop_case_recording("TC001", str(target))

        assert path == str(target)
        recording_video.save_as.assert_called_once_with(str(target))

    @patch('playwright.sync_api.sync_playwright')
    def test_stop_case_recording_removes_original_video(self, mock_pw, tmp_path):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = Mock()
        mock_context = Mock()
        mock_browser.new_context.return_value = mock_context
        recording_page = Mock()
        recording_video = Mock()
        recording_page.video = recording_video
        mock_context.new_page.return_value = recording_page
        original = tmp_path / "hash.webm"
        target = tmp_path / "TC001.webm"
        original.write_bytes(b"video")
        recording_video.path.return_value = str(original)
        recording_video.save_as.side_effect = lambda path: Path(path).write_bytes(original.read_bytes())

        driver = PlaywrightDriver(headless=True)
        driver.start_case_recording(str(tmp_path), "TC001", str(target))
        path = driver.stop_case_recording("TC001", str(target))

        assert path == str(target)
        assert target.exists()
        assert not original.exists()

    @patch('playwright.sync_api.sync_playwright')
    def test_cdp_attach_uses_default_context(self, mock_pw):
        """CDP 附加模式：_ensure_browser 走 connect_over_cdp，复用远端默认 context 首页。"""
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        existing_page = Mock()
        mock_context = Mock()
        mock_context.pages = [existing_page]
        mock_browser.contexts = [mock_context]

        driver = PlaywrightDriver(cdp_endpoint="http://127.0.0.1:9222")

        # 懒加载：__init__ 不连接
        assert driver.browser is None
        assert driver.page is None
        assert driver.attached is True

        driver._ensure_browser()
        mock_playwright.chromium.connect_over_cdp.assert_called_once_with(
            "http://127.0.0.1:9222"
        )
        # 不 launch
        mock_playwright.chromium.launch.assert_not_called()
        # context/page 取自远端默认 context
        assert driver.context == mock_context
        assert driver.page == existing_page
        # 有已有页面时不 new_page
        mock_context.new_page.assert_not_called()

    @patch('playwright.sync_api.sync_playwright')
    def test_cdp_attach_context_without_page_creates_new_page(self, mock_pw):
        """CDP 附加模式：远端默认 context 无页面（浏览器重启）时 new_page 兜底。"""
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        new_page = Mock()
        mock_context = Mock()
        mock_context.pages = []
        mock_context.new_page.return_value = new_page
        mock_browser.contexts = [mock_context]

        driver = PlaywrightDriver(cdp_endpoint=":9222")
        driver._ensure_browser()

        assert driver.context == mock_context
        assert driver.page == new_page
        mock_context.new_page.assert_called_once()

    @patch('playwright.sync_api.sync_playwright')
    def test_cdp_attach_close_only_disconnects(self, mock_pw):
        """attached close() 只断连：browser.close() + _pw.stop()，绝不 context.close()。"""
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.connect_over_cdp.return_value = mock_browser
        mock_context = Mock()
        mock_context.pages = [Mock()]
        mock_browser.contexts = [mock_context]

        driver = PlaywrightDriver(cdp_endpoint="http://127.0.0.1:9222")
        driver._ensure_browser()
        driver.browser.close = Mock()
        driver.context.close = Mock()
        driver._pw.stop = Mock()

        driver.close()

        # 断连 + 停 playwright，不关远端 context/页面
        driver.browser.close.assert_called_once()
        driver._pw.stop.assert_called_once()
        driver.context.close.assert_not_called()

    @patch('playwright.sync_api.sync_playwright')
    def test_owning_close_still_closes_context(self, mock_pw):
        """回归：owning 模式 close() 行为不变 —— 关 context + 关 browser + 停 playwright。"""
        driver = self._create_driver(mock_pw)
        driver.context = Mock()  # owning 模式 context 由 start_case_recording 等创建后持有
        driver.browser.close = Mock()
        driver.context.close = Mock()
        driver._pw.stop = Mock()

        driver.close()

        driver.context.close.assert_called_once()
        driver.browser.close.assert_called_once()
        driver._pw.stop.assert_called_once()

    def _create_driver(self, mock_pw):
        mock_playwright = MagicMock()
        mock_pw.return_value.start.return_value = mock_playwright
        mock_browser = Mock()
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_page = Mock()
        mock_browser.new_page.return_value = mock_page
        driver = PlaywrightDriver()
        driver._ensure_browser()
        return driver
