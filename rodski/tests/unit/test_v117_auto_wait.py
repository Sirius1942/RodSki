"""v11.7.0 WI-65-04 自动等待（AutoWait）公共层单元测试

覆盖 rodski/core/auto_wait.py：
- resolve_auto_wait_ms：默认 5000 / 0 / 数值 / 空值；VerifyTimeout 更名报错；负数 / 非数字报错
- session_mode.validate_default_values 与 KeywordEngine 共用同一解析
- Deadline：剩余预算、动作 timeout 下限 1ms（永不为 0）
- run_element：第 N 次探测才命中、多定位器共享一个预算、AutoWait=0 每个定位器恰好探测一次、
  视觉最小间隔 1s、致命错误立即失败、不支持的定位器跳过、动作失败换下一个定位器
- ElementWaitTimeoutError：DriverError 子类、错误消息格式
- BaseDriver 默认实现：probe / set_auto_wait / get_text_locator
"""
from typing import Optional, Tuple

import pytest

try:
    from rodski.core import auto_wait as aw
    from rodski.core.auto_wait import (
        AutoWaitConfigError, Deadline, ElementWaitTimeoutError, resolve_auto_wait_ms, run_element,
    )
    from rodski.core.exceptions import (
        DriverError, DriverStoppedError, ElementNotFoundError, ElementNotInteractableError,
        InvalidParameterError, StaleElementError,
    )
    from rodski.core.session_mode import validate_default_values
    from rodski.drivers.base_driver import BaseDriver
    from rodski.vision.perception_interface import PerceptionUnavailableError
except ImportError:  # pragma: no cover - 以 rodski/ 为根运行
    from core import auto_wait as aw
    from core.auto_wait import (
        AutoWaitConfigError, Deadline, ElementWaitTimeoutError, resolve_auto_wait_ms, run_element,
    )
    from core.exceptions import (
        DriverError, DriverStoppedError, ElementNotFoundError, ElementNotInteractableError,
        InvalidParameterError, StaleElementError,
    )
    from core.session_mode import validate_default_values
    from drivers.base_driver import BaseDriver
    from vision.perception_interface import PerceptionUnavailableError


class FakeClock:
    """可控时钟：sleep 推进时间，不真正睡眠。"""

    def __init__(self):
        self.t = 100.0
        self.sleeps = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s

    def deadline(self, ms: float) -> Deadline:
        return Deadline(ms, clock=self.now, sleep=self.sleep)


# ───────────────────────────── 配置解析 ─────────────────────────────

class TestResolveAutoWait:
    def test_unset_means_no_auto_wait(self):
        """v11.7.1: 没有隐含默认时长——不设置 AutoWait 就不自动等待"""
        assert resolve_auto_wait_ms(None) == 0
        assert resolve_auto_wait_ms({}) == 0
        assert resolve_auto_wait_ms({"DefaultValue": {}}) == 0
        assert resolve_auto_wait_ms({"DefaultValue": {"AutoWait": "  "}}) == 0

    def test_values(self):
        assert resolve_auto_wait_ms({"DefaultValue": {"AutoWait": "0"}}) == 0
        assert resolve_auto_wait_ms({"DefaultValue": {"AutoWait": "12000"}}) == 12000
        assert resolve_auto_wait_ms({"DefaultValue": {"AutoWait": 2500}}) == 2500

    @pytest.mark.parametrize("raw", ["-1", "abc", "nan"])
    def test_illegal_values_raise(self, raw):
        with pytest.raises(AutoWaitConfigError, match="非负数") as ei:
            resolve_auto_wait_ms({"DefaultValue": {"AutoWait": raw}})
        assert ei.value.param_name == "AutoWait"
        assert isinstance(ei.value, ValueError)

    def test_legacy_verify_timeout_renamed(self):
        with pytest.raises(AutoWaitConfigError, match="已更名为 DefaultValue.AutoWait") as ei:
            resolve_auto_wait_ms({"DefaultValue": {"VerifyTimeout": "5"}})
        assert ei.value.param_name == "VerifyTimeout"
        assert "5000" in str(ei.value)

    def test_session_mode_shares_resolution(self):
        with pytest.raises(ValueError, match="已更名为 DefaultValue.AutoWait"):
            validate_default_values({"DefaultValue": {"VerifyTimeout": "5"}})
        with pytest.raises(ValueError, match="AutoWait"):
            validate_default_values({"DefaultValue": {"AutoWait": "-5"}})
        validate_default_values({"DefaultValue": {"AutoWait": "0", "WaitTime": "0"}})

    def test_keyword_engine_shares_resolution(self):
        try:
            from rodski.core.keyword_engine import KeywordEngine
        except ImportError:  # pragma: no cover
            from core.keyword_engine import KeywordEngine
        from unittest.mock import MagicMock
        engine = KeywordEngine(MagicMock(), global_vars={"DefaultValue": {"AutoWait": "-1"}})
        with pytest.raises(InvalidParameterError, match="AutoWait"):
            engine._auto_wait_ms()
        engine._global_vars = {"DefaultValue": {"AutoWait": "1500"}}
        assert engine._auto_wait_ms() == 1500
        assert engine._resolve_verify_timeout() == 1.5


# ───────────────────────────── Deadline ─────────────────────────────

class TestDeadline:
    def test_remaining_and_expired(self):
        c = FakeClock()
        d = c.deadline(1000)
        assert d.remaining_ms() == pytest.approx(1000)
        c.t += 0.4
        assert d.remaining_ms() == pytest.approx(600)
        assert not d.expired()
        c.t += 0.6
        assert d.expired()

    def test_action_timeout_never_zero(self):
        c = FakeClock()
        assert c.deadline(0).action_timeout_ms() == 500
        d = c.deadline(500)
        c.t += 5
        assert d.action_timeout_ms() == 500
        assert c.deadline(2500).action_timeout_ms() == 2500

    def test_sleep_round_capped_by_deadline(self):
        c = FakeClock()
        d = c.deadline(300)
        start = c.now()
        c.t += 0.05
        d.sleep_round(start, 1.0)
        assert c.sleeps == [pytest.approx(0.25)]

    def test_poll_interval(self):
        assert aw.poll_interval_for(["id", "css"]) == aw.DOM_POLL_INTERVAL_S == 0.2
        assert aw.poll_interval_for(["id", "vision_image"]) == aw.VISION_POLL_INTERVAL_S == 1.0
        assert aw.poll_interval_for(["ocr"]) == 1.0


# ───────────────────────────── run_element ─────────────────────────────

def _act_ok(cand, hit, dl):
    return ("done", cand, dl.action_timeout_ms())


class TestRunElement:
    def test_hit_on_nth_probe(self):
        c = FakeClock()
        calls = []

        def probe(cand):
            calls.append(c.now())
            return len(calls) >= 4

        cand, (_, _, tmo) = run_element("M.btn", ["id=btn"], probe, _act_ok, c.deadline(5000))
        assert cand == "id=btn"
        assert len(calls) == 4
        # 每轮间隔 0.2s，第 4 次探测时已用 0.6s，剩余 4400ms 交给动作
        assert calls[-1] - calls[0] == pytest.approx(0.6)
        assert tmo == 4400

    def test_ready_element_no_wait(self):
        c = FakeClock()
        run_element("M.btn", ["id=btn"], lambda _c: True, _act_ok, c.deadline(5000))
        assert c.sleeps == []

    def test_multi_locator_shares_one_budget_on_hit(self):
        c = FakeClock()
        start = c.now()

        def probe(cand):
            if cand == "id=never":
                return False
            return c.now() - start >= 2.0

        cand, _ = run_element("M.btn", ["id=never", "css=.late"], probe, _act_ok, c.deadline(5000))
        assert cand == "css=.late"
        assert c.now() - start == pytest.approx(2.0)  # ≈ d，不是 AutoWait + d

    def test_multi_locator_all_miss_costs_one_budget(self):
        c = FakeClock()
        start = c.now()
        probes = {"a": 0, "b": 0, "c": 0}

        def probe(cand):
            probes[cand] += 1
            return False

        with pytest.raises(ElementWaitTimeoutError) as ei:
            run_element("M.ghost", ["a", "b", "c"], probe, _act_ok, c.deadline(5000))
        assert c.now() - start == pytest.approx(5.0)  # 1 × AutoWait，不是 3 ×
        assert len(set(probes.values())) == 1 and probes["a"] > 1
        assert "a, b, c" in str(ei.value)

    def test_auto_wait_zero_probes_each_locator_exactly_once(self):
        c = FakeClock()
        probes = []
        with pytest.raises(ElementWaitTimeoutError, match="AutoWait=0ms"):
            run_element("M.btn", ["a", "b"], lambda cand: probes.append(cand) or False,
                        _act_ok, c.deadline(0))
        assert probes == ["a", "b"]
        assert c.sleeps == []

    def test_auto_wait_zero_ready_element_gets_min_action_timeout(self):
        c = FakeClock()
        _, (_, _, tmo) = run_element("M.btn", ["a"], lambda _c: True, _act_ok, c.deadline(0))
        assert tmo == aw.MIN_ACTION_TIMEOUT_MS == 500

    def test_error_message_format(self):
        c = FakeClock()

        def probe(cand):
            raise ElementNotFoundError("selector boom")

        with pytest.raises(ElementWaitTimeoutError) as ei:
            run_element("Login.submitBtn", ["id=submit", "text=提交"], probe, _act_ok,
                        c.deadline(5000), describe=str)
        msg = ei.value.message
        assert msg.startswith("元素 Login.submitBtn 在 AutoWait=5000ms 内未找到")
        assert "尝试定位器: id=submit, text=提交" in msg
        assert "最后错误: selector boom" in msg
        assert isinstance(ei.value, DriverError)
        assert isinstance(ei.value, ElementNotFoundError)

    def test_found_but_not_operable_message(self):
        c = FakeClock()

        def act(cand, hit, dl):
            raise ElementNotInteractableError("element is covered by overlay")

        with pytest.raises(ElementWaitTimeoutError, match="不可操作") as ei:
            run_element("M.coveredBtn", ["id=covered"], lambda _c: True, act, c.deadline(1000))
        assert "element is covered by overlay" in ei.value.message

    def test_action_failure_tries_next_locator(self):
        c = FakeClock()
        acted = []

        def act(cand, hit, dl):
            acted.append(cand)
            if cand == "first":
                raise StaleElementError("stale")
            return "ok"

        cand, result = run_element("M.x", ["first", "second"], lambda _c: True, act, c.deadline(5000))
        assert (cand, result) == ("second", "ok")
        assert acted == ["first", "second"] and c.sleeps == []

    def test_action_returning_false_is_contract_error(self):
        """驱动必须以异常表示失败；返回 False 直接报契约错误，不进入等待。"""
        c = FakeClock()
        with pytest.raises(DriverError, match="返回 False") as ei:
            run_element("M.x", ["a"], lambda _c: True, lambda *a: False, c.deadline(600))
        assert not isinstance(ei.value, ElementWaitTimeoutError)
        assert c.sleeps == []

    @pytest.mark.parametrize("exc", [RuntimeError("boom"), DriverError("generic"), ValueError("bad")])
    def test_non_whitelisted_error_propagates_immediately(self, exc):
        """白名单之外的异常不捕获、不等待，原样抛出。"""
        c = FakeClock()
        calls = []

        def act(cand, hit, dl):
            calls.append(cand)
            raise exc

        with pytest.raises(type(exc)):
            run_element("M.x", ["a", "b"], lambda _c: True, act, c.deadline(5000))
        assert calls == ["a"] and c.sleeps == []

    def test_retry_until_success_then_break(self):
        """try 执行 → 捕获未找到 → 等待 → 再执行，成功即跳出。"""
        c = FakeClock()
        calls = []

        def act(cand, hit, dl):
            calls.append(c.now())
            if len(calls) < 4:
                raise ElementNotFoundError("not yet")
            return "done"

        assert run_element("M.x", ["a"], lambda _c: True, act, c.deadline(5000)) == ("a", "done")
        assert len(calls) == 4 and len(c.sleeps) == 3

    def test_vision_interval_is_one_second(self):
        c = FakeClock()
        shots = []

        def probe(cand):
            shots.append(c.now())
            return (1, 2, 3, 4) if len(shots) >= 3 else None

        _, _ = run_element("M.logo", ["vision_image=logo.png"], probe, _act_ok, c.deadline(5000),
                           interval_s=aw.poll_interval_for(["vision_image"]))
        gaps = [b - a for a, b in zip(shots, shots[1:])]
        assert gaps == [pytest.approx(1.0), pytest.approx(1.0)]

    def test_perception_unavailable_fails_immediately(self):
        c = FakeClock()
        calls = []

        def probe(cand):
            calls.append(cand)
            raise PerceptionUnavailableError()

        with pytest.raises(PerceptionUnavailableError):
            run_element("M.btn", ["vision=登录按钮", "id=login"], probe, _act_ok, c.deadline(5000))
        assert calls == ["vision=登录按钮"] and c.sleeps == []

    @pytest.mark.parametrize("err", [
        InvalidParameterError(keyword="type", param_name="x", reason="bad"),
        DriverStoppedError("stopped"),
        FileNotFoundError("tpl.png"),
    ])
    def test_fatal_errors_not_retried(self, err):
        c = FakeClock()

        def probe(cand):
            raise err

        with pytest.raises(type(err)):
            run_element("M.btn", ["a"], probe, _act_ok, c.deadline(5000))
        assert c.sleeps == []

    def test_unsupported_locator_skipped(self):
        c = FakeClock()
        calls = []

        def probe(cand):
            calls.append(cand)
            if cand == "vision_bbox=1,2,3,4":
                raise NotImplementedError
            return len(calls) >= 3

        cand, _ = run_element("M.x", ["vision_bbox=1,2,3,4", "id=x"], probe, _act_ok, c.deadline(5000))
        assert cand == "id=x"
        assert calls.count("vision_bbox=1,2,3,4") == 1

    def test_all_unsupported_fails_fast(self):
        c = FakeClock()

        def probe(cand):
            raise NotImplementedError("no ocr")

        with pytest.raises(DriverError, match="均不支持"):
            run_element("M.x", ["ocr=a"], probe, _act_ok, c.deadline(5000))
        assert c.sleeps == []

    def test_wait_until(self):
        c = FakeClock()
        n = []
        assert aw.wait_until("M.t", lambda: n.append(1) or len(n) >= 2, c.deadline(1000)) is True
        with pytest.raises(ElementWaitTimeoutError, match="id=t"):
            aw.wait_until("M.t", lambda: False, c.deadline(400), locators=["id=t"])


# ───────────────────────────── BaseDriver 默认实现 ─────────────────────────────

class _CoordDriver(BaseDriver):
    """只实现坐标 API 的最小驱动：模拟尚未覆盖 probe 的驱动。"""

    def __init__(self, bbox=None, error=None):
        self._bbox = bbox
        self._error = error
        self.located = []

    def launch(self, **kw): pass
    def close(self): pass

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        self.located.append((locator_type, locator_value))
        if self._error is not None:
            raise self._error
        return self._bbox

    def click(self, x, y): pass
    def type_text(self, x, y, text): pass
    def get_text(self, x1, y1, x2, y2): return f"text@{x1},{y1},{x2},{y2}"
    def take_screenshot(self): return "/tmp/x.png"
    def double_click(self, x, y): pass
    def right_click(self, x, y): pass
    def hover(self, x, y): pass
    def scroll(self, x, y): pass


class TestBaseDriverDefaults:
    def test_probe_falls_back_to_locate_element(self):
        assert _CoordDriver(bbox=(1, 2, 3, 4)).probe("id=a") is True
        d = _CoordDriver(bbox=None)
        assert d.probe("ocr=登录") is False
        assert d.located == [("ocr", "登录")]

    def test_probe_splits_bare_locators(self):
        d = _CoordDriver(bbox=None)
        d.probe("#submit")
        d.probe("//div[@id='a']")
        assert d.located == [("css", "#submit"), ("xpath", "//div[@id='a']")]

    def test_probe_with_frame_defers_to_action(self):
        d = _CoordDriver(bbox=None)
        assert d.probe("id=a", frame="#f") is True
        assert d.located == []

    def test_probe_does_not_swallow_errors(self):
        """probe 不吞异常：由 run_element 按白名单决定是否等待重试。"""
        with pytest.raises(RuntimeError):
            _CoordDriver(error=RuntimeError("x")).probe("id=a")
        with pytest.raises(NotImplementedError):
            _CoordDriver(error=NotImplementedError()).probe("id=a")
        with pytest.raises(DriverStoppedError):
            _CoordDriver(error=DriverStoppedError("gone")).probe("id=a")
        with pytest.raises(PerceptionUnavailableError):
            _CoordDriver(error=PerceptionUnavailableError()).probe("vision=a")

    def test_set_auto_wait_and_action_timeout_floor(self):
        d = _CoordDriver()
        assert d.get_auto_wait() == 0  # 未下发 = 不自动等待
        d.set_auto_wait(0)
        assert d.get_auto_wait() == 0
        assert d._action_timeout_ms() == 500  # 永不为 0，且保底一次动作的执行时间
        assert d._action_timeout_ms(2500.7) == 2500
        d.set_auto_wait(12000)
        assert d._action_timeout_ms() == 12000

    def test_default_get_text_locator(self):
        assert _CoordDriver(bbox=(1, 2, 3, 4)).get_text_locator("ocr=总计") == "text@1,2,3,4"
        assert _CoordDriver(bbox=None).get_text_locator("ocr=总计") is None


class TestNoImplicitDefault:
    """v11.7.1: AutoWait 没有默认时长；不设置 / 0 = 不自动等待，default 等非数字写法报错"""

    def test_zero_and_unset_are_equivalent(self):
        assert resolve_auto_wait_ms({"DefaultValue": {"AutoWait": "0"}}) == 0
        assert resolve_auto_wait_ms({"DefaultValue": {}}) == 0

    @pytest.mark.parametrize("raw", ["default", "fast"])
    def test_non_numeric_rejected_with_example(self, raw):
        with pytest.raises(AutoWaitConfigError, match='value="5000"'):
            resolve_auto_wait_ms({"DefaultValue": {"AutoWait": raw}})
