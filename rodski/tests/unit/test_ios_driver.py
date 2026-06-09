"""iOS 驱动单元测试

测试 drivers/ios_driver.py 中的 iOS 移动端驱动。
覆盖：初始化配置、iOS 专属定位器（_text_xpath / _get_locator_map）、
      iOS 手势与按键（scroll/swipe/key_press/long_press）、start_app。
所有 Appium 调用通过 mock 隔离。
"""
import pytest
from unittest.mock import Mock, patch
from appium.webdriver.common.appiumby import AppiumBy
from drivers.ios_driver import IOSDriver


def _make_driver(mock_remote):
    """构造一个 driver，并将其底层 driver 替换为 Mock。"""
    driver = IOSDriver()
    driver.driver = Mock()
    driver.wait = Mock()
    return driver


class TestIOSDriverInit:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_minimal(self, mock_remote):
        driver = IOSDriver()
        call_args = mock_remote.call_args
        options = call_args.kwargs.get('options')
        caps = options.to_capabilities() if options else call_args[0][1]
        assert caps.get('platformName') == 'iOS'

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_init_with_bundle_id(self, mock_remote):
        driver = IOSDriver(bundle_id="com.example.app")
        call_args = mock_remote.call_args
        options = call_args.kwargs.get('options')
        caps = options.to_capabilities() if options else call_args[0][1]
        assert (caps.get('appium:bundleId') == 'com.example.app'
                or caps.get('bundleId') == 'com.example.app')

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_shake_success(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.driver.shake = Mock()
        assert driver.shake() is True
        driver.driver.shake.assert_called_once()


class TestIOSLocators:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_text_xpath_ios_format(self, mock_remote):
        driver = _make_driver(mock_remote)
        xpath = driver._text_xpath("登录")
        assert xpath == "//*[@label='登录' or @name='登录' or @value='登录']"
        assert "@label" in xpath and "@name" in xpath and "@value" in xpath

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_locator_map_contains_ios_specific(self, mock_remote):
        driver = _make_driver(mock_remote)
        m = driver._get_locator_map()
        # iOS：id 映射到 ACCESSIBILITY_ID（而非父类的 ID）
        assert m["id"] == AppiumBy.ACCESSIBILITY_ID
        assert m["name"] == AppiumBy.NAME
        assert m["class"] == AppiumBy.CLASS_NAME
        assert m["xpath"] == AppiumBy.XPATH
        # iOS 专属
        assert m["predicate"] == AppiumBy.IOS_PREDICATE
        assert m["class_chain"] == AppiumBy.IOS_CLASS_CHAIN

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_resolve_locator_predicate(self, mock_remote):
        driver = _make_driver(mock_remote)
        by, val = driver._resolve_locator("predicate", "label == 'OK'")
        assert by == AppiumBy.IOS_PREDICATE
        assert val == "label == 'OK'"

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_resolve_locator_text_uses_ios_xpath(self, mock_remote):
        driver = _make_driver(mock_remote)
        by, val = driver._resolve_locator("text", "提交")
        assert by == AppiumBy.XPATH
        assert val == "//*[@label='提交' or @name='提交' or @value='提交']"


class TestIOSGestures:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_scroll_calls_mobile_scroll(self, mock_remote):
        driver = _make_driver(mock_remote)
        assert driver.scroll("down") is True
        driver.driver.execute_script.assert_called_once_with(
            "mobile: scroll", {"direction": "down"}
        )

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_scroll_failure(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.driver.execute_script = Mock(side_effect=Exception("boom"))
        assert driver.scroll("up") is False

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_swipe_calls_mobile_swipe(self, mock_remote):
        driver = _make_driver(mock_remote)
        assert driver.swipe("left") is True
        driver.driver.execute_script.assert_called_once_with(
            "mobile: swipe", {"direction": "left"}
        )

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_key_press_supported_button(self, mock_remote):
        driver = _make_driver(mock_remote)
        assert driver.key_press("home") is True
        driver.driver.execute_script.assert_called_once_with(
            "mobile: pressButton", {"name": "home"}
        )

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_key_press_volume(self, mock_remote):
        driver = _make_driver(mock_remote)
        assert driver.key_press("volumeup") is True
        driver.driver.execute_script.assert_called_once_with(
            "mobile: pressButton", {"name": "volumeup"}
        )

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_key_press_unsupported(self, mock_remote):
        driver = _make_driver(mock_remote)
        assert driver.key_press("BACK") is False
        driver.driver.execute_script.assert_not_called()

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_long_press_calls_touch_and_hold(self, mock_remote):
        driver = _make_driver(mock_remote)
        assert driver.long_press(100, 200, duration=2.0) is True
        driver.driver.execute_script.assert_called_once_with(
            "mobile: touchAndHold", {"x": 100, "y": 200, "duration": 2.0}
        )


class TestIOSStartApp:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_app_activates_bundle(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.driver.activate_app = Mock()
        assert driver.start_app("com.example.app") is True
        driver.driver.activate_app.assert_called_once_with("com.example.app")

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_app_ignores_activity(self, mock_remote):
        """iOS 不走 adb 逻辑：即使传 activity 也只调 activate_app。"""
        driver = _make_driver(mock_remote)
        driver.driver.activate_app = Mock()
        assert driver.start_app("com.example.app", activity=".Main") is True
        driver.driver.activate_app.assert_called_once_with("com.example.app")

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_start_app_failure(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.driver.activate_app = Mock(side_effect=Exception("not installed"))
        assert driver.start_app("com.bad.app") is False
