"""移动端驱动单元测试

测试 drivers/ 中的 AppiumDriver、AndroidDriver、IOSDriver。
覆盖：驱动初始化、平台差异化行为、capabilities 组装、
      基本操作（click/type/navigate/screenshot）。
所有 Appium WebDriver 调用通过 mock 隔离。
"""
import pytest
from unittest.mock import Mock, patch
from drivers import AppiumDriver, AndroidDriver, IOSDriver


class TestAppiumDriver:
    
    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init(self, mock_remote):
        caps = {"platformName": "Android"}
        driver = AppiumDriver(caps)
        mock_remote.assert_called_once()
    
    @patch('drivers.appium_driver.webdriver.Remote')
    def test_click(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()

        element = Mock()
        driver.wait.until.return_value = element

        assert driver.click("id=test") == True
        element.click.assert_called_once()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_type_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        driver.wait.until.return_value = element

        assert driver.type("id=input", "test text") == True
        element.clear.assert_called_once()
        element.send_keys.assert_called_once_with("test text")

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_check_element_visible(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        element.is_displayed.return_value = True
        driver.wait.until.return_value = element

        assert driver.check("id=element") == True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_check_element_not_found(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        driver.wait.until.side_effect = Exception("Not found")

        assert driver.check("id=missing") == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_swipe(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()

        assert driver.swipe(100, 200, 100, 500) == True
        driver.driver.swipe.assert_called_once_with(100, 200, 100, 500, 500)

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_tap(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()

        assert driver.tap(150, 300) == True
        driver.driver.tap.assert_called_once_with([(150, 300)])

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_parse_locator_default(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        from appium.webdriver.common.appiumby import AppiumBy

        by, value = driver._parse_locator("test_id")
        assert by == AppiumBy.ID
        assert value == "test_id"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_parse_locator_xpath(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        from appium.webdriver.common.appiumby import AppiumBy

        by, value = driver._parse_locator("xpath=//button[@id='test']")
        assert by == AppiumBy.XPATH
        assert value == "//button[@id='test']"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_screenshot_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.save_screenshot.return_value = True

        assert driver.screenshot("/tmp/test.png") == True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_screenshot_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.save_screenshot.side_effect = Exception("Failed")

        assert driver.screenshot("/invalid/path.png") == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_navigate_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.get.return_value = None

        assert driver.navigate("https://example.com") == True
        driver.driver.get.assert_called_once_with("https://example.com")

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_navigate_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.get.side_effect = Exception("Failed")

        assert driver.navigate("invalid_url") == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_select(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        element.tag_name = 'select'
        element.find_elements.return_value = [Mock()]
        driver.wait.until.return_value = element

        assert driver.select("id=dropdown", "option1") == True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_hover(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        element.id = 'elem123'
        driver.wait.until.return_value = element

        assert driver.hover("id=menu") == True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_drag_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        # mock locate_element to return bboxes for the new W3C dragGesture API
        driver.locate_element = Mock(side_effect=[
            (10, 20, 60, 70),
            (200, 300, 250, 350),
        ])

        assert driver.drag("id=source", "id=target") == True
        driver.driver.execute_script.assert_called_once_with("mobile: dragGesture", {
            "startX": 35, "startY": 45,
            "endX": 225, "endY": 325,
        })

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_drag_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.find_element.side_effect = Exception("Not found")

        assert driver.drag("id=source", "id=target") == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_scroll_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.get_window_size.return_value = {"width": 1080, "height": 1920}

        assert driver.scroll(0, 300) == True
        # New W3C Actions API uses execute_script("mobile: scrollGesture", ...)
        driver.driver.execute_script.assert_called_once()
        call_args = driver.driver.execute_script.call_args
        assert call_args[0][0] == "mobile: scrollGesture"
        assert call_args[0][1]["direction"] == "down"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_scroll_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.get_window_size.side_effect = Exception("Failed")

        assert driver.scroll(0, 300) == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_assert_element_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        element = Mock()
        element.text = "Hello World"
        driver.driver.find_element.return_value = element

        assert driver.assert_element("id=title", "Hello") == True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_assert_element_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.find_element.side_effect = Exception("Not found")

        assert driver.assert_element("id=missing", "text") == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_close(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()

        driver.close()
        driver.driver.quit.assert_called_once()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_swipe_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.swipe.side_effect = Exception("Failed")

        assert driver.swipe(100, 200, 100, 500) == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_tap_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.tap.side_effect = Exception("Failed")

        assert driver.tap(150, 300) == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_long_press_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        element = Mock()
        element.id = "element123"
        driver.driver.find_element.return_value = element

        assert driver.long_press("id=button") == True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_long_press_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        driver.wait.until.side_effect = Exception("Not found")

        assert driver.long_press("id=missing") == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_hide_keyboard_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()

        assert driver.hide_keyboard() == True
        driver.driver.hide_keyboard.assert_called_once()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_hide_keyboard_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.hide_keyboard.side_effect = Exception("Failed")

        assert driver.hide_keyboard() == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_parse_locator_accessibility_id(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        from appium.webdriver.common.appiumby import AppiumBy

        by, value = driver._parse_locator("accessibility_id=login_button")
        assert by == AppiumBy.ACCESSIBILITY_ID
        assert value == "login_button"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_parse_locator_class(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        from appium.webdriver.common.appiumby import AppiumBy

        by, value = driver._parse_locator("class=android.widget.Button")
        assert by == AppiumBy.CLASS_NAME
        assert value == "android.widget.Button"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_parse_locator_name(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        from appium.webdriver.common.appiumby import AppiumBy

        by, value = driver._parse_locator("name=submit")
        assert by == AppiumBy.NAME
        assert value == "submit"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_get_supported_keywords(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        keywords = driver.get_supported_keywords()
        assert "swipe" in keywords
        assert "tap" in keywords
        assert "long_press" in keywords
        assert "hide_keyboard" in keywords

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_click_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        driver.wait.until.side_effect = Exception("Element not found")

        assert driver.click("id=missing") == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_type_failure(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        driver.wait.until.side_effect = Exception("Element not found")

        assert driver.type("id=input", "text") == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_with_custom_server_url(self, mock_remote):
        caps = {"platformName": "iOS"}
        driver = AppiumDriver(caps, server_url="http://192.168.1.100:4723")
        mock_remote.assert_called_once_with("http://192.168.1.100:4723", caps)


class TestAppiumDriverRecording:
    """AppiumDriver 用例级原生录屏（与 PlaywrightDriver 同契约）"""

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_recording_backend_attr(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        assert driver.recording_backend == "appium"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_case_recording(self, mock_remote, tmp_path):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        target = str(tmp_path / "rec" / "APP001_01.mp4")
        result = driver.start_case_recording(str(tmp_path / "rec"), "APP001", target)
        assert result == target
        assert driver._recording_active is True
        driver.driver.start_recording_screen.assert_called_once()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_case_recording_normalizes_suffix(self, mock_remote, tmp_path):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        # 传入 .webm，应被规范成 .mp4
        result = driver.start_case_recording(str(tmp_path), "APP001", str(tmp_path / "x.webm"))
        assert result.endswith(".mp4")

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_passes_video_size(self, mock_remote, tmp_path):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.start_case_recording(str(tmp_path), "C1", str(tmp_path / "v.mp4"), video_size="1280x720")
        _, kwargs = driver.driver.start_recording_screen.call_args
        assert kwargs.get("videoSize") == "1280x720"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_stop_case_recording_decodes_base64(self, mock_remote, tmp_path):
        import base64
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        payload = b"fake-mp4-bytes"
        driver.driver.stop_recording_screen.return_value = base64.b64encode(payload).decode()
        target = str(tmp_path / "out.mp4")
        driver.start_case_recording(str(tmp_path), "C1", target)
        saved = driver.stop_case_recording("C1", target)
        assert saved == target
        with open(saved, "rb") as f:
            assert f.read() == payload
        assert driver._recording_active is False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_failure_returns_none(self, mock_remote, tmp_path):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.driver.start_recording_screen.side_effect = Exception("not supported")
        result = driver.start_case_recording(str(tmp_path), "C1", str(tmp_path / "v.mp4"))
        assert result is None
        assert driver._recording_active is False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_stop_without_active_returns_target(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        # 未启动录像时 stop 不应抛错
        assert driver.stop_case_recording("C1") is None
