"""v11.7.0 PlaywrightDriver 自动等待契约单元测试

- 动作只做一次，可操作性等待上限 = timeout_ms（默认 AutoWait），永不传 0
- 失败以异常表示，并按"未找到 / 不可操作 / 已失效 / 驱动已停止 / 其他"转换
- 无 force 点击、无 JS 点击 / JS 赋值降级
- probe 即时探测（count），不等待
"""
from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from rodski.drivers.playwright_driver import PlaywrightDriver
    from rodski.core.exceptions import (
        DriverError, DriverStoppedError, ElementNotFoundError, ElementNotInteractableError, StaleElementError,
    )
except ImportError:  # pragma: no cover
    from drivers.playwright_driver import PlaywrightDriver
    from core.exceptions import (
        DriverError, DriverStoppedError, ElementNotFoundError, ElementNotInteractableError, StaleElementError,
    )


class PWTimeout(Exception):
    """模拟 playwright._impl._errors.TimeoutError（按类名识别）"""


PWTimeout.__name__ = "TimeoutError"


def _driver(count=1):
    d = PlaywrightDriver(headless=True)
    d.page = MagicMock()
    d.browser = MagicMock()
    d._ensure_browser = lambda: None
    loc = d.page.locator.return_value
    loc.count.return_value = count
    el = loc.first
    return d, el


class TestActions:
    @pytest.mark.parametrize("method,args,el_attr,expected_kwargs", [
        ("click_locator", ("id=btn",), "click", {}),
        ("type_locator", ("id=user", "tom"), "fill", {}),
        ("select", ("#region", "华东"), "select_option", {}),
        ("hover_locator", ("#menu",), "hover", {}),
        ("double_click_locator", ("#row",), "dblclick", {}),
        ("right_click_locator", ("#row",), "click", {"button": "right"}),
        ("clear", ("#user",), "fill", {}),
        ("upload_file", ("#file", "/tmp/a.txt"), "set_input_files", {}),
    ])
    def test_single_action_with_timeout_ms(self, method, args, el_attr, expected_kwargs):
        d, el = _driver()
        assert getattr(d, method)(*args, timeout_ms=1234) is True
        call = getattr(el, el_attr).call_args
        assert call.kwargs["timeout"] == 1234
        for k, v in expected_kwargs.items():
            assert call.kwargs[k] == v
        assert getattr(el, el_attr).call_count == 1

    def test_default_timeout_is_auto_wait(self):
        d, el = _driver()
        d.set_auto_wait(5000)
        d.click_locator("#btn")
        assert el.click.call_args.kwargs["timeout"] == 5000
        d.set_auto_wait(0)
        d.click_locator("#btn")
        assert el.click.call_args.kwargs["timeout"] == 500  # 永不为 0（Playwright 0 = 无限），保底 500ms

    def test_locator_conversion(self):
        d, _ = _driver()
        d.select("id=region", "x", timeout_ms=10)
        d.page.locator.assert_called_with("#region")
        d.hover_locator("name=q", timeout_ms=10)
        d.page.locator.assert_called_with('[name="q"]')

    def test_frame_scope(self):
        d, _ = _driver()
        scope_el = d.page.frame_locator.return_value.locator.return_value.first
        d.click_locator("#pay", frame="#payFrame", timeout_ms=100)
        d.page.frame_locator.assert_called_with("#payFrame")
        assert scope_el.click.call_args.kwargs["timeout"] == 500  # 下限 500ms

    def test_drag_uses_target_locator(self):
        d, el = _driver()
        assert d.drag("#src", "#dst", timeout_ms=300) is True
        assert el.drag_to.call_args.kwargs["timeout"] == 500  # 下限 500ms


class TestErrorTranslation:
    def test_timeout_absent_is_not_found(self):
        d, el = _driver(count=0)
        el.click.side_effect = PWTimeout("Timeout 100ms exceeded")
        with pytest.raises(ElementNotFoundError):
            d.click_locator("#missing", timeout_ms=100)

    def test_timeout_present_is_not_interactable(self):
        d, el = _driver(count=1)
        el.click.side_effect = PWTimeout("Timeout 100ms exceeded. element is not enabled")
        with pytest.raises(ElementNotInteractableError):
            d.click_locator("#disabled", timeout_ms=100)

    def test_overlay_is_not_interactable_and_no_force_click(self):
        d, el = _driver(count=1)
        el.click.side_effect = PWTimeout("Timeout exceeded. <div id=mask> intercepts pointer events")
        with pytest.raises(ElementNotInteractableError):
            d.click_locator("#covered", timeout_ms=100)
        assert el.click.call_count == 1
        assert all("force" not in c.kwargs for c in el.click.call_args_list)
        d.page.evaluate.assert_not_called()

    def test_type_failure_has_no_js_fallback(self):
        d, el = _driver(count=1)
        el.fill.side_effect = PWTimeout("Timeout exceeded. element is not editable")
        with pytest.raises(ElementNotInteractableError):
            d.type_locator("#ro", "x", timeout_ms=100)
        d.page.evaluate.assert_not_called()

    def test_detached_is_stale(self):
        d, el = _driver()
        el.click.side_effect = Exception("Element is not attached to the DOM")
        with pytest.raises(StaleElementError):
            d.click_locator("#x", timeout_ms=100)

    def test_other_error_is_plain_driver_error(self):
        d, el = _driver()
        el.click.side_effect = Exception("Unexpected token in selector")
        with pytest.raises(DriverError) as ei:
            d.click_locator("#x", timeout_ms=100)
        assert type(ei.value) is DriverError

    def test_browser_closed_is_driver_stopped(self):
        d, el = _driver()
        el.click.side_effect = Exception("Target page, context or browser has been closed")
        with pytest.raises(DriverStoppedError):
            d.click_locator("#x", timeout_ms=100)


class TestProbeAndRead:
    def test_probe_is_instant_count(self):
        d, _ = _driver(count=0)
        assert d.probe("#x") is False
        d.page.locator.return_value.count.return_value = 2
        assert d.probe("id=x") is True
        d.page.locator.assert_called_with("#x")

    def test_probe_translates_navigation_error(self):
        d, _ = _driver()
        d.page.locator.return_value.count.side_effect = Exception("Execution context was destroyed")
        with pytest.raises(StaleElementError):
            d.probe("#x")

    def test_get_text_waits_with_timeout(self):
        d, el = _driver()
        el.text_content.return_value = "hello"
        assert d.get_text_locator("#t", timeout_ms=700) == "hello"
        assert el.text_content.call_args.kwargs["timeout"] == 700

    def test_check_returns_false_when_not_visible(self):
        d, el = _driver(count=0)
        el.wait_for.side_effect = PWTimeout("Timeout")
        assert d.check("#x", timeout_ms=50) is False

    def test_assert_element(self):
        d, el = _driver()
        el.text_content.return_value = "Hello World"
        assert d.assert_element("#e", "Hello", timeout_ms=10) is True
        assert d.assert_element("#e", "Bye", timeout_ms=10) is False
