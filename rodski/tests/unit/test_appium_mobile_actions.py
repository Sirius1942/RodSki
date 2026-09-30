"""AppiumDriver 移动端字段动作测试 — Iteration 48"""
import pytest
from unittest.mock import Mock, MagicMock, patch


def _make_driver(mock_remote):
    mock_remote.return_value = MagicMock()
    from drivers.appium_driver import AppiumDriver
    driver = AppiumDriver.__new__(AppiumDriver)
    driver.driver = mock_remote.return_value
    driver.wait = MagicMock()
    return driver


@patch('drivers.appium_driver.webdriver.Remote')
class TestAppiumScroll:
    """T48-001: scroll 使用 mobile: scrollGesture"""

    def test_scroll_down_uses_mobile_scroll_gesture(self, mock_remote):
        """scroll(0, 300) → mobile: scrollGesture direction=down"""
        driver = _make_driver(mock_remote)
        driver.driver.get_window_size.return_value = {'width': 1080, 'height': 1920}
        driver.scroll(0, 300)
        calls = [str(c) for c in driver.driver.execute_script.call_args_list]
        assert any("scrollGesture" in c for c in calls)
        # 验证 direction=down
        call_args = driver.driver.execute_script.call_args
        assert call_args[0][0] == "mobile: scrollGesture"
        assert call_args[0][1]["direction"] == "down"

    def test_scroll_up_direction(self, mock_remote):
        """scroll(0, -300) → direction=up"""
        driver = _make_driver(mock_remote)
        driver.driver.get_window_size.return_value = {'width': 1080, 'height': 1920}
        driver.scroll(0, -300)
        call_args = driver.driver.execute_script.call_args
        assert call_args[0][1]["direction"] == "up"

    def test_scroll_right_direction(self, mock_remote):
        """scroll(300, 0) → direction=right"""
        driver = _make_driver(mock_remote)
        driver.driver.get_window_size.return_value = {'width': 1080, 'height': 1920}
        driver.scroll(300, 0)
        call_args = driver.driver.execute_script.call_args
        assert call_args[0][1]["direction"] == "right"

    def test_scroll_left_direction(self, mock_remote):
        """scroll(-300, 0) → direction=left"""
        driver = _make_driver(mock_remote)
        driver.driver.get_window_size.return_value = {'width': 1080, 'height': 1920}
        driver.scroll(-300, 0)
        call_args = driver.driver.execute_script.call_args
        assert call_args[0][1]["direction"] == "left"

    def test_scroll_returns_true_on_success(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.driver.get_window_size.return_value = {'width': 1080, 'height': 1920}
        result = driver.scroll(0, 300)
        assert result is True

    def test_scroll_returns_false_on_exception(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.driver.get_window_size.side_effect = Exception("driver error")
        result = driver.scroll(0, 300)
        assert result is False


@patch('drivers.appium_driver.webdriver.Remote')
class TestAppiumDrag:
    """T48-002 / v11.7.0: drag 使用 mobile: dragGesture；元素未找到抛 ElementNotFoundError"""

    @staticmethod
    def _el(x, y, w, h):
        el = Mock()
        el.rect = {"x": x, "y": y, "width": w, "height": h}
        return el

    def test_drag_uses_mobile_drag_gesture(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.driver.find_elements.side_effect = [[self._el(10, 20, 50, 50)], [self._el(200, 300, 50, 50)]]
        assert driver.drag("id=source", "id=target", timeout_ms=100) is True
        call_args = driver.driver.execute_script.call_args
        assert call_args[0][0] == "mobile: dragGesture"
        assert call_args[0][1] == {"startX": 35, "startY": 45, "endX": 225, "endY": 325}

    def test_drag_source_not_found_raises(self, mock_remote):
        from core.exceptions import ElementNotFoundError
        driver = _make_driver(mock_remote)
        driver.driver.find_elements.return_value = []
        with pytest.raises(ElementNotFoundError):
            driver.drag("id=source", "id=target", timeout_ms=100)

