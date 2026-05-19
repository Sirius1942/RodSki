"""AppiumDriver 核心能力测试 — Iteration 47"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from appium.webdriver.common.appiumby import AppiumBy


def _make_driver(mock_remote):
    """创建 AppiumDriver 实例（mock Appium Server）"""
    mock_remote.return_value = MagicMock()
    from drivers.appium_driver import AppiumDriver
    driver = AppiumDriver.__new__(AppiumDriver)
    driver.driver = mock_remote.return_value
    driver.wait = MagicMock()
    return driver


def _mock_element(x=10, y=20, w=100, h=50):
    el = MagicMock()
    el.rect = {'x': x, 'y': y, 'width': w, 'height': h}
    el.text = ""
    el.get_attribute = Mock(return_value="")
    return el


@patch('drivers.appium_driver.webdriver.Remote')
class TestAppiumLocateElement:
    """T47-001: locate_element 12 种定位器正确映射"""

    def test_locate_id_uses_appium_id(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_el = _mock_element(10, 20, 100, 50)
        driver.driver.find_element.return_value = mock_el
        bbox = driver.locate_element("id", "com.rodski.demo:id/username")
        driver.driver.find_element.assert_called_with(AppiumBy.ID, "com.rodski.demo:id/username")
        assert bbox == (10, 20, 110, 70)

    def test_locate_name_uses_accessibility_id(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_el = _mock_element()
        driver.driver.find_element.return_value = mock_el
        driver.locate_element("name", "loginBtn")
        driver.driver.find_element.assert_called_with(AppiumBy.ACCESSIBILITY_ID, "loginBtn")

    def test_locate_text_uses_xpath(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_el = _mock_element()
        driver.driver.find_element.return_value = mock_el
        driver.locate_element("text", "登录")
        call_args = driver.driver.find_element.call_args
        assert call_args[0][0] == AppiumBy.XPATH
        assert "登录" in call_args[0][1]

    def test_locate_class_uses_class_name(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_el = _mock_element()
        driver.driver.find_element.return_value = mock_el
        driver.locate_element("class", "android.widget.Button")
        driver.driver.find_element.assert_called_with(AppiumBy.CLASS_NAME, "android.widget.Button")

    def test_locate_xpath_uses_xpath(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_el = _mock_element()
        driver.driver.find_element.return_value = mock_el
        driver.locate_element("xpath", "//android.widget.Button[@text='登录']")
        driver.driver.find_element.assert_called_with(AppiumBy.XPATH, "//android.widget.Button[@text='登录']")

    def test_locate_not_found_returns_none(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.driver.find_element.side_effect = Exception("No such element")
        result = driver.locate_element("id", "nonexistent")
        assert result is None

    def test_locate_returns_correct_bbox(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_el = _mock_element(x=50, y=100, w=200, h=60)
        driver.driver.find_element.return_value = mock_el
        bbox = driver.locate_element("id", "btn")
        assert bbox == (50, 100, 250, 160)


@patch('drivers.appium_driver.webdriver.Remote')
class TestAppiumGetElementText:
    """T47-002: get_element_text_by_locator 新增方法"""

    def test_get_text_from_text_attr(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_el = MagicMock()
        mock_el.text = "欢迎，admin"
        mock_el.get_attribute = Mock(return_value="")
        driver.driver.find_element.return_value = mock_el
        result = driver.get_element_text_by_locator("id", "com.rodski.demo:id/welcomeText")
        assert result == "欢迎，admin"

    def test_get_text_fallback_to_content_desc(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_el = MagicMock()
        mock_el.text = ""
        mock_el.get_attribute.side_effect = lambda attr: {
            "value": "", "label": "", "name": "", "content-desc": "欢迎按钮"
        }.get(attr, "")
        driver.driver.find_element.return_value = mock_el
        result = driver.get_element_text_by_locator("id", "btn")
        assert result == "欢迎按钮"

    def test_get_text_all_empty_raises_error(self, mock_remote):
        from core.exceptions import ElementNotFoundError
        driver = _make_driver(mock_remote)
        mock_el = MagicMock()
        mock_el.text = ""
        mock_el.get_attribute = Mock(return_value="")
        driver.driver.find_element.return_value = mock_el
        with pytest.raises(ElementNotFoundError):
            driver.get_element_text_by_locator("id", "emptyField")

    def test_get_text_element_not_found_raises_error(self, mock_remote):
        from core.exceptions import ElementNotFoundError
        driver = _make_driver(mock_remote)
        driver.driver.find_element.side_effect = Exception("No such element")
        with pytest.raises(ElementNotFoundError):
            driver.get_element_text_by_locator("id", "nonexistent")


@patch('drivers.appium_driver.webdriver.Remote')
class TestAppiumTypeText:
    """T47-003: type_text 使用 active_element.send_keys"""

    def test_type_text_taps_then_sends_keys(self, mock_remote):
        driver = _make_driver(mock_remote)
        mock_active = MagicMock()
        driver.driver.switch_to.active_element = mock_active
        driver.type_text(55, 45, "admin")
        driver.driver.tap.assert_called_once_with([(55, 45)])
        mock_active.clear.assert_called_once()
        mock_active.send_keys.assert_called_once_with("admin")

    def test_type_text_fallback_when_active_element_none(self, mock_remote):
        """active_element 为 None 时回退到 mobile: type"""
        driver = _make_driver(mock_remote)
        driver.driver.switch_to.active_element = None
        driver.type_text(55, 45, "admin")
        driver.driver.tap.assert_called_once_with([(55, 45)])
        # 回退路径：execute_script("mobile: type", ...)
        driver.driver.execute_script.assert_called()


@patch('drivers.appium_driver.webdriver.Remote')
class TestAppiumKeyPress:
    """T47-003: key_press 新增方法"""

    def test_key_press_back(self, mock_remote):
        driver = _make_driver(mock_remote)
        result = driver.key_press("BACK")
        driver.driver.press_keycode.assert_called_with(4)
        assert result is True

    def test_key_press_home(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.key_press("HOME")
        driver.driver.press_keycode.assert_called_with(3)

    def test_key_press_enter(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.key_press("ENTER")
        driver.driver.press_keycode.assert_called_with(66)

    def test_key_press_case_insensitive(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.key_press("back")
        driver.driver.press_keycode.assert_called_with(4)

    def test_key_press_unknown_returns_false(self, mock_remote):
        driver = _make_driver(mock_remote)
        result = driver.key_press("UNKNOWN_KEY_XYZ")
        assert result is False
        driver.driver.press_keycode.assert_not_called()
