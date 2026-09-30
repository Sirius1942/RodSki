"""v11.7.0 AppiumDriver 自动等待契约单元测试

- 不再有 WebDriverWait(driver, 10) / self.wait；初始化时 implicitly_wait(0)
- 关键字层调用（带 timeout_ms）：一次即时查找 + 一次动作，失败抛异常
- 直接调用（无 timeout_ms）：按 AutoWait 走公共自动等待循环
- 原生异常转换：NoSuchElement → ElementNotFoundError、Stale → StaleElementError、
  NotInteractable / ClickIntercepted → ElementNotInteractableError
- _parse_locator 与 _resolve_locator 同一套映射
"""
from unittest.mock import Mock, patch

import pytest
from appium.webdriver.common.appiumby import AppiumBy

from drivers import AppiumDriver, AndroidDriver
from core.exceptions import (
    DriverError, ElementNotFoundError, ElementNotInteractableError, StaleElementError,
)
from core.auto_wait import ElementWaitTimeoutError


def _exc(name):
    return type(name, (Exception,), {})


@pytest.fixture
def drv():
    with patch('drivers.appium_driver.webdriver.Remote'):
        yield AppiumDriver({"platformName": "Android"})


def test_no_builtin_10s_wait_and_implicit_wait_zero():
    with patch('drivers.appium_driver.webdriver.Remote') as remote:
        d = AppiumDriver({"platformName": "Android"})
        remote.return_value.implicitly_wait.assert_called_once_with(0)
        assert "wait" not in vars(d)  # 不再有遮蔽 BaseDriver.wait() 的 WebDriverWait 实例属性


def test_click_single_attempt_with_timeout_ms(drv):
    el = Mock()
    drv.driver.find_elements.return_value = [el]
    assert drv.click_locator("id=btn", timeout_ms=100) is True
    el.click.assert_called_once()


def test_click_absent_raises_not_found_immediately(drv):
    drv.driver.find_elements.return_value = []
    with pytest.raises(ElementNotFoundError):
        drv.click_locator("id=btn", timeout_ms=100)
    assert drv.driver.find_elements.call_count == 1


def test_type_single_attempt(drv):
    el = Mock()
    drv.driver.find_elements.return_value = [el]
    assert drv.type_locator("id=user", "tom", timeout_ms=100) is True
    el.clear.assert_called_once()
    el.send_keys.assert_called_once_with("tom")


@pytest.mark.parametrize("native,expected", [
    ("StaleElementReferenceException", StaleElementError),
    ("ElementNotInteractableException", ElementNotInteractableError),
    ("ElementClickInterceptedException", ElementNotInteractableError),
    ("NoSuchElementException", ElementNotFoundError),
])
def test_native_error_translation(drv, native, expected):
    el = Mock()
    el.click.side_effect = _exc(native)("boom")
    drv.driver.find_elements.return_value = [el]
    with pytest.raises(expected):
        drv.click_locator("id=btn", timeout_ms=100)


def test_unknown_error_is_plain_driver_error(drv):
    el = Mock()
    el.click.side_effect = ValueError("weird")
    drv.driver.find_elements.return_value = [el]
    with pytest.raises(DriverError) as ei:
        drv.click_locator("id=btn", timeout_ms=100)
    assert type(ei.value) is DriverError


def test_direct_call_waits_until_element_appears(drv):
    """未传 timeout_ms（外部直接调用）：按 AutoWait 自动等待，出现即点击。"""
    el = Mock()
    drv.set_auto_wait(3000)
    drv.driver.find_elements.side_effect = [[], [], [el]]
    with patch('time.sleep'):
        assert drv.click("id=late") is True
    el.click.assert_called_once()


def test_direct_call_times_out_with_auto_wait(drv):
    drv.set_auto_wait(0)
    drv.driver.find_elements.return_value = []
    with pytest.raises(ElementWaitTimeoutError, match="AutoWait=0ms"):
        drv.click("id=never")


def test_check_returns_false_when_absent(drv):
    drv.set_auto_wait(0)
    drv.driver.find_elements.return_value = []
    assert drv.check("id=x") is False


def test_probe_is_instant(drv):
    drv.driver.find_elements.return_value = []
    assert drv.probe("id=x") is False
    drv.driver.find_elements.return_value = [Mock()]
    assert drv.probe("text=登录") is True
    by, value = drv.driver.find_elements.call_args[0]
    assert by == AppiumBy.XPATH and "登录" in value


def test_parse_locator_matches_resolve_locator(drv):
    for loc in ("name=submit", "id=a", "text=登录", "accessibility_id=x", "class=android.widget.Button"):
        t, v = loc.split("=", 1)
        assert drv._parse_locator(loc) == drv._resolve_locator(t, v)
    assert drv._parse_locator("name=submit")[0] == AppiumBy.ACCESSIBILITY_ID


def test_clear_and_get_text_locator(drv):
    el = Mock()
    el.text = "欢迎"
    drv.driver.find_elements.return_value = [el]
    assert drv.clear_locator("id=f", timeout_ms=100) is True
    el.clear.assert_called_once()
    assert drv.get_text_locator("id=f", timeout_ms=100) == "欢迎"


def test_long_press_and_hover_use_element_id(drv):
    el = Mock()
    el.id = "E1"
    drv.driver.find_elements.return_value = [el]
    assert drv.long_press("id=a", timeout_ms=10) is True
    assert drv.hover_locator("id=a", timeout_ms=10) is True
    assert drv.driver.execute_script.call_args[0] == ("mobile: longClick", {"elementId": "E1"})


def test_select_webview(drv):
    el = Mock()
    drv.driver.find_elements.return_value = [el]
    with patch("selenium.webdriver.support.ui.Select") as sel:
        assert drv.select("id=dd", "v1", timeout_ms=10) is True
        sel.return_value.select_by_value.assert_called_once_with("v1")


def test_android_driver_inherits():
    with patch('drivers.appium_driver.webdriver.Remote'):
        a = AndroidDriver()
    el = Mock()
    a.driver = Mock()
    a.driver.find_elements.return_value = [el]
    assert a.click("id=button") is True and a.type("id=input", "t") is True
