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
    """T48-002: drag 使用 mobile: dragGesture"""

    def test_drag_uses_mobile_drag_gesture(self, mock_remote):
        """drag 使用 mobile: dragGesture"""
        driver = _make_driver(mock_remote)
        # mock locate_element 返回两个 bbox
        driver.locate_element = Mock(side_effect=[
            (10, 20, 60, 70),    # 源元素
            (200, 300, 250, 350) # 目标元素
        ])
        driver.drag("id=source", "id=target")
        call_args = driver.driver.execute_script.call_args
        assert call_args[0][0] == "mobile: dragGesture"
        params = call_args[0][1]
        assert params["startX"] == 35   # (10+60)//2
        assert params["startY"] == 45   # (20+70)//2
        assert params["endX"] == 225    # (200+250)//2
        assert params["endY"] == 325    # (300+350)//2

    def test_drag_source_not_found_returns_false(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.locate_element = Mock(return_value=None)
        result = driver.drag("id=source", "id=target")
        assert result is False

    def test_drag_target_not_found_returns_false(self, mock_remote):
        driver = _make_driver(mock_remote)
        driver.locate_element = Mock(side_effect=[(10, 20, 60, 70), None])
        result = driver.drag("id=source", "id=target")
        assert result is False
