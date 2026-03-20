"""移动端驱动单元测试"""
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
        driver.wait.until.return_value = element

        assert driver.select("id=dropdown", "option1") == True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_hover(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        driver.wait.until.return_value = element

        assert driver.hover("id=menu") == True

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_drag_success(self, mock_remote):
        driver = AppiumDriver({"platformName": "Android"})
        driver.driver = Mock()
        el1 = Mock()
        el2 = Mock()
        driver.driver.find_element.side_effect = [el1, el2]

        assert driver.drag("id=source", "id=target") == True
        driver.driver.drag_and_drop.assert_called_once_with(el1, el2)

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
        driver.driver.swipe.assert_called_once()

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
        driver.driver.find_element.side_effect = Exception("Not found")

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
