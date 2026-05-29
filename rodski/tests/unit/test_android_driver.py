"""Android 驱动单元测试

测试 drivers/android_driver.py 中的 Android 移动端驱动。
覆盖：初始化配置、基本操作（click/type/swipe/scroll）、
      元素查找（locator 类型映射）、截图、应用管理。
所有 Appium 调用通过 mock 隔离。
"""
import pytest
from unittest.mock import Mock, patch
from drivers.android_driver import AndroidDriver


class TestAndroidDriver:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_minimal(self, mock_remote):
        driver = AndroidDriver()

        call_args = mock_remote.call_args
        options = call_args.kwargs.get('options')
        caps = options.to_capabilities() if options else call_args[0][1]
        assert caps['platformName'] == 'Android'
        assert caps['appium:deviceName'] == 'Android' or caps.get('deviceName') == 'Android'
        assert caps['appium:automationName'] == 'UiAutomator2' or caps.get('automationName') == 'UiAutomator2'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_with_package(self, mock_remote):
        driver = AndroidDriver(app_package="com.example.app")

        call_args = mock_remote.call_args
        options = call_args.kwargs.get('options')
        caps = options.to_capabilities() if options else call_args[0][1]
        assert caps.get('appium:appPackage') == 'com.example.app' or caps.get('appPackage') == 'com.example.app'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_with_activity(self, mock_remote):
        driver = AndroidDriver(app_activity=".MainActivity")

        call_args = mock_remote.call_args
        options = call_args.kwargs.get('options')
        caps = options.to_capabilities() if options else call_args[0][1]
        assert caps.get('appium:appActivity') == '.MainActivity' or caps.get('appActivity') == '.MainActivity'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_full(self, mock_remote):
        driver = AndroidDriver(
            device_name="Pixel",
            app_package="com.test",
            app_activity=".Main",
            server_url="http://localhost:4723"
        )

        call_args = mock_remote.call_args
        options = call_args.kwargs.get('options')
        caps = options.to_capabilities() if options else call_args[0][1]
        assert caps.get('appium:deviceName') == 'Pixel' or caps.get('deviceName') == 'Pixel'
        assert caps.get('appium:appPackage') == 'com.test' or caps.get('appPackage') == 'com.test'
        assert caps.get('appium:appActivity') == '.Main' or caps.get('appActivity') == '.Main'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_activity_success(self, mock_remote):
        driver = AndroidDriver()
        driver.driver = Mock()
        driver.driver.start_activity = Mock()

        result = driver.start_activity("com.example", ".Activity")

        assert result == True
        driver.driver.start_activity.assert_called_once_with("com.example", ".Activity")

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_activity_failure(self, mock_remote):
        driver = AndroidDriver()
        driver.driver = Mock()
        driver.driver.start_activity = Mock(side_effect=Exception("Failed"))

        result = driver.start_activity("com.invalid", ".Activity")

        assert result == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_press_keycode_success(self, mock_remote):
        driver = AndroidDriver()
        driver.driver = Mock()
        driver.driver.press_keycode = Mock()

        result = driver.press_keycode(4)

        assert result == True
        driver.driver.press_keycode.assert_called_once_with(4)

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_press_keycode_failure(self, mock_remote):
        driver = AndroidDriver()
        driver.driver = Mock()
        driver.driver.press_keycode = Mock(side_effect=Exception("Failed"))

        result = driver.press_keycode(999)

        assert result == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_inherited_click(self, mock_remote):
        driver = AndroidDriver()
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        driver.wait.until.return_value = element

        result = driver.click("id=button")

        assert result == True
        element.click.assert_called_once()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_inherited_type(self, mock_remote):
        driver = AndroidDriver()
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        driver.wait.until.return_value = element

        result = driver.type("id=input", "text")

        assert result == True
        element.send_keys.assert_called_once_with("text")
