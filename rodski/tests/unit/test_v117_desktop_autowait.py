"""v11.7.0 DesktopDriver 自动等待单元测试（spec §4.4：本机无感知服务，桌面端以单测覆盖）

用 mock 截图序列模拟"前 N 次无目标、第 N+1 次出现"：
- 每轮都重新截图（绕过 0.5s 截图缓存）
- 未匹配抛 ElementNotFoundError（不返回 False），由公共层在 AutoWait 内重试
- 始终无目标 → ≈AutoWait 后 ElementWaitTimeoutError
- PerceptionUnavailableError 立即失败，不重试
"""
import time
from unittest.mock import MagicMock, patch

import pytest

from core import auto_wait as aw
from core.exceptions import ElementNotFoundError, InvalidParameterError
from drivers.desktop_driver import DesktopDriver
from vision.perception_interface import PerceptionUnavailableError


class _Vision:
    def __init__(self, hits_after=None, error=None):
        self.calls = []
        self.hits_after = hits_after
        self.error = error

    def locate(self, t, v, shot):
        self.calls.append(shot)
        if self.error:
            raise self.error
        if self.hits_after is not None and len(self.calls) > self.hits_after:
            return (100, 200, 140, 240)
        return None


@pytest.fixture
def drv():
    d = DesktopDriver(target_platform="macos")
    shots = iter(range(10_000))
    d.take_screenshot = lambda: f"/tmp/shot_{next(shots)}.png"
    d.click = MagicMock()
    d.type_text = MagicMock()
    d.get_text = MagicMock(return_value="总计 99")
    return d


def _run(d, locator, act, ms):
    return aw.run_element(locator, [locator], probe=d.probe, act=act, deadline=aw.Deadline(ms),
                          interval_s=0.01)


def test_click_waits_until_target_appears_with_fresh_screenshots(drv):
    drv._vision_provider = _Vision(hits_after=3)
    _run(drv, "ocr=登录", lambda l, _h, d: drv.click_locator(l, timeout_ms=d.action_timeout_ms()), 3000)
    drv.click.assert_called_once_with(120, 220)
    shots = drv._vision_provider.calls
    assert len(shots) >= 4 and len(set(shots)) == len(shots)  # 每轮都是新截图


def test_never_appears_times_out_at_auto_wait(drv):
    drv._vision_provider = _Vision(hits_after=None)
    t0 = time.monotonic()
    with pytest.raises(aw.ElementWaitTimeoutError, match="AutoWait=300ms"):
        _run(drv, "ocr=登录", lambda l, _h, d: drv.click_locator(l), 300)
    assert 0.25 < time.monotonic() - t0 < 1.5
    drv.click.assert_not_called()


def test_perception_unavailable_fails_immediately(drv):
    drv._vision_provider = _Vision(error=PerceptionUnavailableError())
    with pytest.raises(PerceptionUnavailableError):
        _run(drv, "vision=登录按钮", lambda l, _h, d: drv.click_locator(l), 5000)
    assert len(drv._vision_provider.calls) == 1


def test_click_locator_raises_instead_of_false(drv):
    drv._vision_provider = _Vision(hits_after=None)
    with pytest.raises(ElementNotFoundError):
        drv.click_locator("ocr=不存在")


def test_vision_bbox_has_no_lookup(drv):
    drv._vision_provider = _Vision(hits_after=None)
    assert drv.probe("vision_bbox=10,20,30,40") is True
    drv.click_locator("vision_bbox=10,20,30,40")
    drv.click.assert_called_once_with(20, 30)
    assert drv._vision_provider.calls == []


def test_unsupported_locator_type_is_not_implemented(drv):
    with pytest.raises(NotImplementedError):
        drv.probe("id=loginBtn")


def test_get_text_locator_reads_region(drv):
    drv._vision_provider = _Vision(hits_after=0)
    assert drv.get_text_locator("ocr=总计") == "总计 99"
    drv.get_text.assert_called_once_with(100, 200, 140, 240)
    drv._vision_provider = _Vision(hits_after=None)
    assert drv.get_text_locator("ocr=总计") is None


def test_select_is_explicitly_unsupported(drv):
    with pytest.raises(InvalidParameterError, match="不支持 select"):
        drv.select("ocr=地区", "华东")


def test_key_press_and_drag_with_locators(drv):
    drv.press_key = MagicMock()
    drv.hotkey = MagicMock()
    drv.key_press("Enter")
    drv.press_key.assert_called_once_with("enter")
    drv.key_press("Control+A")
    drv.hotkey.assert_called_once_with("control", "a")
    drv._vision_provider = _Vision(hits_after=0)
    drv.move_to = MagicMock()
    with patch.object(drv, "_get_pyautogui") as pg:
        drv.drag("ocr=源", "ocr=目标")
        pg.return_value.drag.assert_called_once()
