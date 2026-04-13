"""iOS 驱动单元测试

测试 drivers/ios_driver.py 中的 iOS 移动端驱动。
覆盖：初始化配置、基本操作（click/type/swipe）、
      元素查找（iOS 特有 locator）、截图。
所有 Appium 调用通过 mock 隔离。
"""
import pytest
from unittest.mock import Mock, patch
from drivers.ios_driver import IOSDriver


class TestIOSDriver:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_minimal(self, mock_remote):
        driver = IOSDriver()

        call_args = mock_remote.call_args
        caps = call_args[0][1]
        assert caps['platformName'] == 'iOS'
        assert caps['deviceName'] == 'iPhone'
        assert caps['automationName'] == 'XCUITest'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_with_device_name(self, mock_remote):
        driver = IOSDriver(device_name="iPad")

        call_args = mock_remote.call_args
        caps = call_args[0][1]
        assert caps['deviceName'] == 'iPad'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_with_bundle_id(self, mock_remote):
        driver = IOSDriver(bundle_id="com.example.app")

        call_args = mock_remote.call_args
        caps = call_args[0][1]
        assert caps['bundleId'] == 'com.example.app'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_full(self, mock_remote):
        driver = IOSDriver(
            device_name="iPhone 14",
            bundle_id="com.test.app",
            server_url="http://localhost:4723"
        )

        call_args = mock_remote.call_args
        caps = call_args[0][1]
        assert caps['deviceName'] == 'iPhone 14'
        assert caps['bundleId'] == 'com.test.app'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_shake_success(self, mock_remote):
        driver = IOSDriver()
        driver.driver = Mock()
        driver.driver.shake = Mock()

        result = driver.shake()

        assert result == True
        driver.driver.shake.assert_called_once()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_shake_failure(self, mock_remote):
        driver = IOSDriver()
        driver.driver = Mock()
        driver.driver.shake = Mock(side_effect=Exception("Failed"))

        result = driver.shake()

        assert result == False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_inherited_click(self, mock_remote):
        driver = IOSDriver()
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        driver.wait.until.return_value = element

        result = driver.click("id=button")

        assert result == True
        element.click.assert_called_once()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_inherited_type(self, mock_remote):
        driver = IOSDriver()
        driver.driver = Mock()
        driver.wait = Mock()
        element = Mock()
        driver.wait.until.return_value = element

        result = driver.type("id=input", "text")

        assert result == True
        element.send_keys.assert_called_once_with("text")

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_inherited_swipe(self, mock_remote):
        driver = IOSDriver()
        driver.driver = Mock()

        result = driver.swipe(100, 200, 100, 500)

        assert result == True
        driver.driver.swipe.assert_called_once_with(100, 200, 100, 500, 500)
