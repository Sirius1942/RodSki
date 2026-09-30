"""v11.7.0 WI-65-05 KeywordEngine 接入自动等待（AutoWait）单元测试

用可控的 FakeDriver（元素在指定时刻"出现"）验证 spec §3.3：
- type 批量：逐字段独立 deadline；同一元素多个 location 共享一个预算；命中即走
- AutoWait=0：每个定位器恰好探测一次；动作 timeout 下限 1ms（永不为 0）
- 错误消息：元素 Model.field、AutoWait=<N>ms、尝试定位器
- 单字段 type / get（模型 / 选择器）/ clear / upload_file / type 后自动取值
- drag 两端在同一 deadline 内等待
- 视觉：PerceptionUnavailableError 立即失败；截图用 target_driver；verify 含视觉字段也轮询
- ElementWaitTimeoutError 不做步骤级重试；AutoWait 下发到驱动（execute 前 / 新建驱动时）
- 驱动方法未声明 timeout_ms 时不传（兼容尚未改造的驱动）
"""
import time
from unittest.mock import MagicMock

import pytest

try:
    from rodski.core.keyword_engine import KeywordEngine
    from rodski.core.model_parser import ModelParser
    from rodski.core.auto_wait import ElementWaitTimeoutError
    from rodski.core.exceptions import AutoCaptureError, DriverError, RetryExhaustedError
    from rodski.vision.perception_interface import PerceptionUnavailableError
except ImportError:  # pragma: no cover - 以 rodski/ 为根运行
    from core.keyword_engine import KeywordEngine
    from core.model_parser import ModelParser
    from core.auto_wait import ElementWaitTimeoutError
    from core.exceptions import AutoCaptureError, DriverError, RetryExhaustedError
    from vision.perception_interface import PerceptionUnavailableError


MODEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="Chain" type="ui">
    <element name="a" type="web"><location type="id">a</location></element>
    <element name="b" type="web"><location type="id">b</location></element>
    <element name="c" type="web"><location type="id">c</location></element>
  </model>
  <model name="Multi" type="ui">
    <element name="btn" type="web">
      <location type="id" priority="1">never</location>
      <location type="css" priority="2">.late</location>
    </element>
  </model>
  <model name="Ghost" type="ui">
    <element name="ghostBtn" type="web">
      <location type="id" priority="1">g1</location>
      <location type="css" priority="2">.g2</location>
      <location type="xpath" priority="3">//button[@id='g3']</location>
    </element>
  </model>
  <model name="Login" type="ui">
    <element name="submitBtn" type="web"><location type="id">submit</location></element>
  </model>
  <model name="Drag" type="ui">
    <element name="src" type="web"><location type="id">src</location></element>
  </model>
  <model name="Logo" type="ui">
    <element name="logo" type="web"><location type="vision_image">img/logo.png</location></element>
  </model>
  <model name="Smart" type="ui">
    <element name="okBtn" type="web">
      <location type="vision" priority="1">确定按钮</location>
      <location type="id" priority="2">ok</location>
    </element>
  </model>
  <model name="LateGet" type="ui">
    <element name="lateValue" type="web"><location type="id">lateValue</location></element>
  </model>
</models>
"""


class FakeDriver:
    """元素在 appear[locator] 秒（相对 start）后出现；动作记录 timeout_ms。

    click / type / select / drag / clear / upload / get_text 均声明 timeout_ms（v11.7.0 驱动契约）。
    """

    def __init__(self, appear=None, chain=None):
        self.start = time.monotonic()
        self.appear = dict(appear or {})  # locator -> 秒；缺省=立即存在；None=永不出现
        self.chain = dict(chain or {})    # 动作后令另一个元素在 N 秒后出现: locator -> (next_locator, 秒)
        self.probes = []
        self.actions = []
        self.auto_wait = None
        self.texts = {}

    # 契约
    def set_auto_wait(self, ms):
        self.auto_wait = ms
        self._auto_wait_ms = ms

    def _present(self, locator):
        at = self.appear.get(locator, 0)
        return at is not None and time.monotonic() - self.start >= at

    def probe(self, locator, frame=None):
        self.probes.append(locator)
        return self._present(locator)

    def _act(self, name, locator, timeout_ms, *extra):
        assert timeout_ms is not None and timeout_ms >= 1, "timeout_ms 必须 ≥1ms"
        if not self._present(locator):
            raise DriverError(f"{name}: not found {locator}")
        self.actions.append((name, locator, timeout_ms) + extra)
        if locator in self.chain:
            nxt, delay = self.chain[locator]
            self.appear[nxt] = time.monotonic() - self.start + delay
        return True

    def click_locator(self, locator, frame=None, timeout_ms=None):
        return self._act("click", locator, timeout_ms)

    def type_locator(self, locator, text, frame=None, timeout_ms=None):
        return self._act("type", locator, timeout_ms, text)

    def select(self, locator, value, frame=None, timeout_ms=None):
        return self._act("select", locator, timeout_ms, value)

    def drag(self, from_loc, to_loc, timeout_ms=None):
        return self._act("drag", from_loc, timeout_ms, to_loc)

    def clear(self, locator, frame=None, timeout_ms=None):
        return self._act("clear", locator, timeout_ms)

    def upload_file(self, locator, file_path, timeout_ms=None):
        return self._act("upload", locator, timeout_ms, file_path)

    def get_text_locator(self, locator, frame=None, timeout_ms=None):
        self.actions.append(("get_text", locator, timeout_ms))
        return self.texts.get(locator, "txt")

    def take_screenshot(self):
        return "/tmp/fake.png"


@pytest.fixture
def parser(tmp_path):
    p = tmp_path / "model.xml"
    p.write_text(MODEL_XML, encoding="utf-8")
    return ModelParser(str(p))


def _engine(parser, driver, rows=None, auto_wait_ms=None, **kw):
    dm = MagicMock()
    dm.get_data.side_effect = lambda table, data_id: (rows or {}).get(table)
    gv = {"DefaultValue": {"AutoWait": str(auto_wait_ms)}} if auto_wait_ms is not None else {}
    return KeywordEngine(driver, model_parser=parser, data_manager=dm, global_vars=gv, **kw)


def _timed(fn):
    t0 = time.monotonic()
    try:
        return fn(), time.monotonic() - t0
    except Exception as e:  # noqa: BLE001
        e.elapsed = time.monotonic() - t0
        raise


# ───────────────────────────── type 批量 ─────────────────────────────

class TestBatchTypeAutoWait:
    def test_each_field_has_its_own_budget(self, parser):
        """A 立即可用；输入 A 后 0.4s 出现 B；点 B 后 0.4s 出现 C。AutoWait=600ms：
        总耗时 >0.8s（> AutoWait）仍通过，证明逐字段独立计时。"""
        d = FakeDriver(appear={"id=b": None, "id=c": None},
                       chain={"id=a": ("id=b", 0.4), "id=b": ("id=c", 0.4)})
        rows = {"Chain": {"a": "hello", "b": "click", "c": "click"}}
        engine = _engine(parser, d, rows, auto_wait_ms=600)
        ok, elapsed = _timed(lambda: engine.execute("type", {"model": "Chain", "data": "T1"}))
        assert ok is True
        assert elapsed > 0.75
        assert [a[:2] for a in d.actions] == [("type", "id=a"), ("click", "id=b"), ("click", "id=c")]
        # 每个字段的动作 timeout 都来自自己的预算（≤600ms，≥1ms）
        assert all(1 <= a[2] <= 600 for a in d.actions)

    def test_multi_locator_shares_budget_hit_cost_is_d(self, parser):
        """第 1 个 location 永不命中、第 2 个 0.3s 后命中：耗时 ≈0.3s，不是 AutoWait + 0.3s。"""
        d = FakeDriver(appear={"id=never": None, "css=.late": 0.3})
        engine = _engine(parser, d, {"Multi": {"btn": "click"}}, auto_wait_ms=2000)
        ok, elapsed = _timed(lambda: engine.execute("type", {"model": "Multi", "data": "T1"}))
        assert ok and 0.25 <= elapsed < 0.9
        assert d.actions[0][:2] == ("click", "css=.late")
        # 定位阶段两个 location 轮流探测
        assert d.probes.count("id=never") >= 2 and d.probes.count("css=.late") >= 2

    def test_multi_locator_all_miss_costs_one_budget(self, parser):
        d = FakeDriver(appear={"id=g1": None, "css=.g2": None, "xpath=//button[@id='g3']": None})
        engine = _engine(parser, d, {"Ghost": {"ghostBtn": "click"}}, auto_wait_ms=500)
        with pytest.raises(ElementWaitTimeoutError) as ei:
            _timed(lambda: engine.execute("type", {"model": "Ghost", "data": "T1"}))
        assert 0.45 <= ei.value.elapsed < 1.0  # 1 × AutoWait，不是 3 ×
        msg = ei.value.message
        assert "Ghost.ghostBtn" in msg and "AutoWait=500ms" in msg
        assert "id=g1, css=.g2, xpath=//button[@id='g3']" in msg

    def test_ready_elements_no_extra_wait(self, parser):
        d = FakeDriver()
        rows = {"Chain": {"a": "x", "b": "y", "c": "click"}}
        engine = _engine(parser, d, rows, auto_wait_ms=5000)
        ok, elapsed = _timed(lambda: engine.execute("type", {"model": "Chain", "data": "T1"}))
        assert ok and elapsed < 0.2
        assert d.probes == ["id=a", "id=b", "id=c"]
        assert all(4000 < a[2] <= 5000 for a in d.actions)

    def test_auto_wait_zero_probes_once_and_passes_min_timeout(self, parser):
        d = FakeDriver(appear={"id=submit": 1.5})
        engine = _engine(parser, d, {"Login": {"submitBtn": "click"}}, auto_wait_ms=0)
        with pytest.raises(ElementWaitTimeoutError, match="AutoWait=0ms") as ei:
            _timed(lambda: engine.execute("type", {"model": "Login", "data": "T1"}))
        assert ei.value.elapsed < 0.3
        assert d.probes == ["id=submit"]
        assert "Login.submitBtn" in ei.value.message

        ready = FakeDriver()
        engine = _engine(parser, ready, {"Login": {"submitBtn": "click"}}, auto_wait_ms=0)
        assert engine.execute("type", {"model": "Login", "data": "T1"})
        assert ready.actions == [("click", "id=submit", 500)]

    def test_timeout_not_retried_at_step_level(self, parser):
        d = FakeDriver(appear={"id=submit": None})
        engine = _engine(parser, d, {"Login": {"submitBtn": "click"}}, auto_wait_ms=300,
                         retry_config={"max_retries": 2, "retry_delay": 0.01})
        with pytest.raises(ElementWaitTimeoutError) as ei:
            _timed(lambda: engine.execute("type", {"model": "Login", "data": "T1"}))
        assert not isinstance(ei.value, RetryExhaustedError)
        assert ei.value.elapsed < 0.7  # 没有 3 × AutoWait

    def test_drag_waits_for_both_ends(self, parser):
        d = FakeDriver(appear={"id=src": 0.2, "#dst": 0.4})
        engine = _engine(parser, d, {"Drag": {"src": "drag【#dst】"}}, auto_wait_ms=2000)
        ok, elapsed = _timed(lambda: engine.execute("type", {"model": "Drag", "data": "T1"}))
        assert ok and 0.35 <= elapsed < 1.2
        assert d.actions[0][0] == "drag" and d.actions[0][3] == "#dst"
        assert "#dst" in d.probes

    def test_drag_target_never_appears(self, parser):
        d = FakeDriver(appear={"#dst": None})
        engine = _engine(parser, d, {"Drag": {"src": "drag【#dst】"}}, auto_wait_ms=300)
        with pytest.raises(ElementWaitTimeoutError, match="#dst"):
            engine.execute("type", {"model": "Drag", "data": "T1"})

    def test_driver_without_timeout_param_not_given_timeout(self, parser):
        """尚未改造的驱动（方法无 timeout_ms 参数）不会收到 timeout_ms。"""
        driver = MagicMock()
        driver.click_locator.return_value = True
        engine = _engine(parser, driver, {"Login": {"submitBtn": "click"}}, auto_wait_ms=1000)
        assert engine.execute("type", {"model": "Login", "data": "T1"})
        driver.click_locator.assert_called_once_with("id=submit")
        driver.probe.assert_called_with("id=submit")

    def test_perception_unavailable_fails_immediately(self, parser):
        d = FakeDriver()
        engine = _engine(parser, d, {"Smart": {"okBtn": "click"}})  # 默认 5000

        def boom(*a, **k):
            raise PerceptionUnavailableError()

        engine._locate_by_perception = boom
        with pytest.raises((PerceptionUnavailableError, RetryExhaustedError)) as ei:
            _timed(lambda: engine.execute("type", {"model": "Smart", "data": "T1"}))
        assert ei.value.elapsed < 0.3
        assert d.actions == []

    def test_vision_image_polls_with_fresh_screenshot_on_target_driver(self, parser, monkeypatch):
        d = FakeDriver()
        engine = _engine(parser, d, {"Logo": {"logo": "click"}}, auto_wait_ms=3000)
        calls = []

        def fake_locate(value, driver=None):
            calls.append((time.monotonic(), driver))
            return (10, 10, 30, 30) if len(calls) >= 2 else None

        engine._locate_by_vision_image = fake_locate
        d.click = MagicMock()
        assert engine.execute("type", {"model": "Logo", "data": "T1"})
        assert len(calls) == 2 and all(drv is d for _, drv in calls)
        assert calls[1][0] - calls[0][0] >= 0.95  # 视觉最小间隔 1s
        d.click.assert_called_once_with(20, 20)


# ───────────────────────────── 单字段 / 读取 / clear / upload ─────────────────────────────

class TestOtherKeywordsAutoWait:
    def test_single_field_type_waits(self, parser):
        d = FakeDriver(appear={"#name": 0.3})
        engine = _engine(parser, d, auto_wait_ms=2000)
        ok, elapsed = _timed(lambda: engine.execute("type", {"locator": "#name", "text": "Tom"}))
        assert ok and 0.25 <= elapsed < 0.9
        assert d.actions[0][:2] == ("type", "#name") and d.actions[0][3] == "Tom"

    def test_get_model_mode_reads_when_present(self, parser):
        d = FakeDriver(appear={"id=lateValue": 0.3})
        d.texts["#lateValue"] = "42"
        engine = _engine(parser, d, auto_wait_ms=2000)
        ok, elapsed = _timed(lambda: engine.execute("get", {"model": "LateGet", "data": "G001"}))
        assert ok and 0.25 <= elapsed < 0.9
        assert engine.get_return(-1) == {"lateValue": "42"}

    def test_get_model_mode_fails_after_auto_wait(self, parser):
        d = FakeDriver(appear={"id=lateValue": None})
        engine = _engine(parser, d, auto_wait_ms=300)
        with pytest.raises(ElementWaitTimeoutError) as ei:
            _timed(lambda: engine.execute("get", {"model": "LateGet", "data": "G001"}))
        assert "LateGet.lateValue" in ei.value.message and "AutoWait=300ms" in ei.value.message
        assert 0.25 <= ei.value.elapsed < 0.8

    def test_get_selector_mode(self, parser):
        d = FakeDriver(appear={"css=#formResult": 0.2})
        d.texts["#formResult"] = "ok"
        engine = _engine(parser, d, auto_wait_ms=2000)
        assert engine.execute("get", {"model": "", "data": "#formResult"})
        assert engine.get_return(-1) == "ok"

    def test_clear_waits_and_fails_with_locator_name(self, parser):
        d = FakeDriver(appear={"#prefilled": 0.2})
        engine = _engine(parser, d, auto_wait_ms=2000)
        assert engine.execute("clear", {"model": "", "data": "#prefilled"})
        assert d.actions[0][0] == "clear" and d.actions[0][2] >= 1

        never = FakeDriver(appear={"#prefilled": None})
        engine = _engine(parser, never, auto_wait_ms=200)
        with pytest.raises(ElementWaitTimeoutError, match="元素 #prefilled 在 AutoWait=200ms"):
            engine.execute("clear", {"model": "", "data": "#prefilled"})

    def test_upload_file_waits(self, parser):
        d = FakeDriver(appear={"#fileInput": 0.2})
        engine = _engine(parser, d, auto_wait_ms=2000)
        assert engine.execute("upload_file", {"model": "#fileInput", "data": "fun/a.txt"})
        assert d.actions[0][0] == "upload" and d.actions[0][3] == "fun/a.txt"

    def test_auto_capture_times_out_as_failure(self, parser):
        d = FakeDriver(appear={"id=orderNo": None})
        engine = _engine(parser, d, auto_wait_ms=200)
        with pytest.raises(AutoCaptureError, match="AutoWait=200ms"):
            engine._run_auto_capture_ui("Login", [{"name": "orderNo", "type": "id", "value": "orderNo"}])

    def test_auto_capture_reads_late_element(self, parser):
        d = FakeDriver(appear={"id=orderNo": 0.2})
        d.texts["#orderNo"] = "NO-1"
        engine = _engine(parser, d, auto_wait_ms=2000)
        got = engine._run_auto_capture_ui("Login", [{"name": "orderNo", "type": "id", "value": "orderNo"}])
        assert got == {"orderNo": "NO-1"}


# ───────────────────────────── verify / 下发 ─────────────────────────────

class TestVerifyAndSync:
    def test_verify_with_vision_field_now_polls(self, parser):
        d = FakeDriver()
        rows = {"Logo_verify": {"logo": "存在"}}
        engine = _engine(parser, d, rows, auto_wait_ms=3000)
        calls = []

        def fake_locate(value, driver=None):
            calls.append((time.monotonic(), driver))
            return (1, 1, 2, 2) if len(calls) >= 2 else None

        engine._locate_by_vision_image = fake_locate
        assert engine.execute("verify", {"model": "Logo", "data": "V1"})
        assert len(calls) == 2 and calls[0][1] is d
        assert calls[1][0] - calls[0][0] >= 0.95  # 视觉字段每轮最小间隔 1s

    def test_verify_vision_perception_unavailable_immediate(self, parser):
        d = FakeDriver()
        rows = {"Smart_verify": {"okBtn": "x"}}
        engine = _engine(parser, d, rows)

        def boom(*a, **k):
            raise PerceptionUnavailableError()

        engine._locate_by_perception = boom
        t0 = time.monotonic()
        with pytest.raises((PerceptionUnavailableError, RetryExhaustedError)):
            engine.execute("verify", {"model": "Smart", "data": "V1"})
        assert time.monotonic() - t0 < 0.3

    def test_auto_wait_pushed_before_execute(self, parser):
        d = FakeDriver()
        engine = _engine(parser, d, {"Login": {"submitBtn": "click"}}, auto_wait_ms=1234)
        engine.execute("type", {"model": "Login", "data": "T1"})
        assert d.auto_wait == 1234

    def test_auto_wait_pushed_to_lazily_created_driver(self, parser):
        created = FakeDriver()
        engine = _engine(parser, FakeDriver(), auto_wait_ms=777,
                         driver_factory=lambda **kw: created)
        drv = engine._get_driver_for_type("macos")
        assert drv is created and created.auto_wait == 777
        # 再次获取不重复创建；后续 execute 同样同步
        engine._global_vars = {"DefaultValue": {"AutoWait": "888"}}
        engine._sync_auto_wait()
        assert created.auto_wait == 888

    def test_invalid_auto_wait_fails_before_side_effects(self, parser):
        d = FakeDriver()
        engine = _engine(parser, d, {"Login": {"submitBtn": "click"}}, auto_wait_ms=-1)
        with pytest.raises(Exception, match="AutoWait"):
            engine.execute("type", {"model": "Login", "data": "T1"})
        assert d.actions == [] and d.probes == []

    def test_screenshot_for_vision_uses_target_driver(self, parser, tmp_path, monkeypatch):
        """_locate_by_vision_image 截图用传入的目标驱动，而不是 self.driver。"""
        web = MagicMock()
        mobile = MagicMock()
        mobile.take_screenshot.return_value = str(tmp_path / "shot.png")
        engine = _engine(parser, web)
        try:
            import rodski.vision.image_matcher as im
        except ImportError:  # pragma: no cover
            import vision.image_matcher as im
        monkeypatch.setattr(im, "resolve_template_path", lambda v, **k: v)
        monkeypatch.setattr(im.ImageTemplateMatcher, "locate", lambda self, s, t: None)
        assert engine._locate_by_vision_image("img/logo.png", driver=mobile) is None
        mobile.take_screenshot.assert_called_once()
        web.take_screenshot.assert_not_called()
