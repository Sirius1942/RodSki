"""v11.6.0 WI-64-04 执行器：WaitTime 毫秒、SessionMode、auth state、EvidenceMode。

设计文档: .pb/specs/v11.6.0-ai-authoring-and-performance-design.md §5 P1/P2/P3/P5
"""
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from builtin_ops import get_builtin
from core.config_manager import ConfigManager
from core.session_mode import (
    SharedBrowser,
    resolve_evidence_mode,
    resolve_session_mode,
    resolve_wait_time,
)
from core.ski_executor import SKIExecutor
from drivers.base_driver import BaseDriver
from drivers.playwright_driver import PlaywrightDriver


# ---------------------------------------------------------------- 工具
def _build_module(tmp_path: Path, default_values: dict, case_xml: str = "") -> Path:
    module_dir = tmp_path / "mod"
    for sub in ("case", "model", "data", "result"):
        (module_dir / sub).mkdir(parents=True)
    (module_dir / "model" / "model.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<models>\n'
        '  <model name="m"><element name="input"><location type="id">u</location></element></model>\n'
        '</models>', encoding="utf-8")
    vars_xml = "".join(f'    <var name="{k}" value="{v}"/>\n' for k, v in default_values.items())
    (module_dir / "data" / "globalvalue.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<globalvalue>\n'
        f'  <group name="DefaultValue">\n{vars_xml}  </group>\n</globalvalue>', encoding="utf-8")
    (module_dir / "case" / "c.xml").write_text(case_xml or (
        '<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n'
        '  <case execute="是" id="TC001" title="t" component_type="界面">\n'
        '    <test_case><test_step action="wait" model="" data="0"/></test_case>\n'
        '  </case>\n</cases>'), encoding="utf-8")
    return module_dir


def _config(tmp_path: Path, **overrides) -> ConfigManager:
    cfg = ConfigManager(str(tmp_path / "no_such_config.json"))
    cfg.config["recording"] = {"enabled": False}
    cfg.config.update(overrides)
    return cfg


def _mock_driver() -> Mock:
    d = Mock(spec=BaseDriver)
    d.screenshot = Mock(return_value=True)
    d.close = Mock(return_value=True)
    return d


def _executor(tmp_path, default_values=None, driver=None, factory=None, **cfg):
    module_dir = _build_module(tmp_path, default_values or {"WaitTime": "0"})
    return SKIExecutor(str(module_dir / "case" / "c.xml"), driver or _mock_driver(),
                       _config(tmp_path, **cfg), driver_factory=factory)


class _FakeContext:
    def __init__(self, browser):
        self.browser = browser
        self.closed = False
        self.cookies_added = []
        self.init_scripts = []
        self.pages = []

    def new_page(self):
        page = _FakePage(self)
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True

    def add_cookies(self, cookies):
        self.cookies_added.extend(cookies)

    def add_init_script(self, script):
        self.init_scripts.append(script)

    def storage_state(self):
        return {"cookies": [{"name": "sid", "value": "s3cret", "domain": "127.0.0.1", "path": "/"}],
                "origins": [{"origin": "http://127.0.0.1:8766",
                             "localStorage": [{"name": "token", "value": "t0k"}]}]}


class _FakePage:
    def __init__(self, context):
        self.context = context
        self.url = "about:blank"

    def evaluate(self, *_a, **_k):
        return None

    def add_init_script(self, *_a, **_k):
        return None

    def on(self, *_a, **_k):
        return None

    def close(self):
        pass


class _FakeBrowser:
    def __init__(self):
        self.contexts = []
        self.closed = False
        self.connected = True

    def new_context(self, **_kw):
        ctx = _FakeContext(self)
        self.contexts.append(ctx)
        return ctx

    def is_connected(self):
        return self.connected

    def close(self):
        self.closed = True
        self.connected = False


def _shared_driver(shared: SharedBrowser, launches: list) -> PlaywrightDriver:
    drv = PlaywrightDriver(headless=True)

    def _launch():
        launches.append(1)
        return MagicMock(), _FakeBrowser()

    drv._launch_browser = _launch
    drv.inject_monitor = lambda: None
    drv.attach_shared_browser(shared)
    return drv


# ---------------------------------------------------------------- WaitTime 单位
class TestWaitTimeUnits:
    @pytest.mark.parametrize("raw", [None, "", "0", "-5"])
    def test_zero_or_empty_means_no_wait(self, raw):
        assert resolve_wait_time(raw) == (0.0, None)

    @pytest.mark.parametrize("raw,seconds", [("1", 1.0), ("2", 2.0), ("30", 30.0), ("0.5", 0.5)])
    def test_legacy_small_values_are_seconds_with_warning(self, raw, seconds):
        value, warning = resolve_wait_time(raw)
        assert value == seconds
        assert warning and "WaitTime" in warning and "毫秒" in warning

    @pytest.mark.parametrize("raw,seconds", [("31", 0.031), ("300", 0.3), ("500", 0.5), ("2000", 2.0)])
    def test_values_above_threshold_are_milliseconds(self, raw, seconds):
        value, warning = resolve_wait_time(raw)
        assert value == pytest.approx(seconds)
        assert warning is None

    def test_non_numeric_falls_back_to_zero_with_hint(self):
        value, warning = resolve_wait_time("abc")
        assert value == 0.0 and "毫秒" in warning

    def test_executor_converts_and_warns_once_per_run(self, tmp_path, caplog):
        ex = _executor(tmp_path, {"WaitTime": "1"})
        assert ex.default_wait_time == 1.0
        with caplog.at_level(logging.WARNING, logger="rodski"):
            ex.execute_all_cases()
        hits = [r for r in caplog.records if "WaitTime" in r.getMessage() and "毫秒" in r.getMessage()]
        assert len(hits) == 1
        ex.close()

    def test_executor_ms_value_no_warning(self, tmp_path, caplog):
        ex = _executor(tmp_path, {"WaitTime": "500"})
        assert ex.default_wait_time == pytest.approx(0.5)
        assert ex._wait_time_warning is None
        ex.close()


# ---------------------------------------------------------------- 模式解析
class TestModeResolution:
    def test_defaults(self):
        assert resolve_session_mode(None, {}) == "isolated"
        assert resolve_evidence_mode(None, {}) == "full"

    def test_globalvalue_value(self):
        gv = {"DefaultValue": {"SessionMode": "Shared_Browser", "EvidenceMode": "concise"}}
        assert resolve_session_mode(None, gv) == "shared_browser"
        assert resolve_evidence_mode(None, gv) == "concise"

    def test_cli_overrides_globalvalue(self):
        gv = {"DefaultValue": {"SessionMode": "shared_browser", "EvidenceMode": "concise"}}
        assert resolve_session_mode("isolated", gv) == "isolated"
        assert resolve_evidence_mode("full", gv) == "full"

    def test_invalid_value_has_fix_hint(self):
        with pytest.raises(ValueError) as e:
            resolve_session_mode(None, {"DefaultValue": {"SessionMode": "shared"}})
        msg = str(e.value)
        assert "SessionMode" in msg and "shared_browser" in msg and "--session-mode" in msg
        with pytest.raises(ValueError):
            resolve_evidence_mode("minimal", {})

    def test_invalid_globalvalue_fails_executor_before_side_effects(self, tmp_path):
        driver = _mock_driver()
        with pytest.raises(ValueError):
            _executor(tmp_path, {"WaitTime": "0", "EvidenceMode": "none"}, driver=driver)
        driver.close.assert_not_called()

    def test_cli_args_pass_through_config(self, tmp_path):
        from rodski_cli.run import _apply_session_evidence_args, setup_parser
        import argparse
        parser = argparse.ArgumentParser()
        setup_parser(parser.add_subparsers())
        args = parser.parse_args(["run", "@plan_x", "--session-mode", "shared_browser", "--evidence", "concise"])
        cfg = _apply_session_evidence_args(_config(tmp_path), args)
        assert cfg.get("session_mode") == "shared_browser"
        assert cfg.get("evidence_mode") == "concise"
        # 不指定时不覆盖 globalvalue
        args2 = parser.parse_args(["run", "case/"])
        cfg2 = _apply_session_evidence_args(_config(tmp_path), args2)
        assert cfg2.get("session_mode") is None and cfg2.get("evidence_mode") is None


# ---------------------------------------------------------------- SessionMode 生命周期
class TestSharedBrowserLifecycle:
    def test_shared_browser_launches_once_and_relaunches_when_disconnected(self):
        shared = SharedBrowser()
        calls = []

        def launcher():
            calls.append(1)
            return MagicMock(), _FakeBrowser()

        b1 = shared.acquire(launcher)
        assert shared.acquire(launcher) is b1 and len(calls) == 1
        b1.connected = False
        assert shared.acquire(launcher) is not b1 and len(calls) == 2
        shared.close()
        assert shared.browser is None

    def test_driver_close_only_closes_context(self):
        shared, launches = SharedBrowser(), []
        d1 = _shared_driver(shared, launches)
        d1._ensure_browser()
        browser, ctx1 = d1.browser, d1.context
        d1.close()
        assert ctx1.closed and not browser.closed
        d2 = _shared_driver(shared, launches)
        d2._ensure_browser()
        assert d2.browser is browser and d2.context is not ctx1
        assert len(launches) == 1
        shared.close()
        assert browser.closed

    def test_attach_ignored_for_cdp_or_started_driver(self):
        cdp = PlaywrightDriver(cdp_endpoint="http://127.0.0.1:9222")
        cdp.attach_shared_browser(SharedBrowser())
        assert cdp._shared_browser is None

    def test_executor_wraps_factory_and_closes_shared_browser(self, tmp_path):
        created = []

        def factory(driver_type="web", **_kw):
            d = PlaywrightDriver(headless=True)
            created.append(d)
            return d

        first = factory()
        ex = _executor(tmp_path, driver=first, factory=factory, session_mode="shared_browser")
        assert ex.session_mode == "shared_browser"
        assert first._shared_browser is ex._shared_browser
        second = ex.driver_factory()
        assert second._shared_browser is ex._shared_browser
        ex._shared_browser.close = Mock()
        ex.close()
        ex._shared_browser.close.assert_called_once()

    def test_isolated_does_not_wrap(self, tmp_path):
        factory = Mock()
        ex = _executor(tmp_path, factory=factory)
        assert ex.session_mode == "isolated" and ex._shared_browser is None
        assert ex.driver_factory is factory
        ex.close()

    def test_new_context_per_case_when_case_has_no_close(self, tmp_path):
        ex = _executor(tmp_path, session_mode="shared_browser")
        drv = Mock()
        drv._shared_browser = ex._shared_browser
        drv.browser = object()
        ex.driver = drv
        ex._driver_closed = False
        ex._start_new_shared_browser_context()
        drv.close.assert_called_once()
        assert ex._driver_closed is True
        ex.close()

    def test_shared_session_close_is_noop(self, tmp_path):
        driver = _mock_driver()
        ex = _executor(tmp_path, driver=driver, session_mode="shared_session")
        ex.result_writer._init_run_dir()
        ex._current_case_steps_log = []
        ex.execute_step({"action": "close", "model": "", "data": ""}, "后处理")
        driver.close.assert_not_called()
        assert ex._driver_closed is False
        ex.close()
        driver.close.assert_called_once()  # run 结束时统一关闭

    def test_isolated_close_still_closes(self, tmp_path):
        driver = _mock_driver()
        ex = _executor(tmp_path, driver=driver)
        ex.result_writer._init_run_dir()
        ex._current_case_steps_log = []
        ex.execute_step({"action": "close", "model": "", "data": ""}, "后处理")
        driver.close.assert_called_once()
        assert ex._driver_closed is True
        ex.close()


# ---------------------------------------------------------------- auth state
class TestAuthState:
    def setup_method(self):
        get_builtin("save_auth_state")  # 触发导入
        self.mod = __import__(get_builtin("save_auth_state").__module__, fromlist=["x"])
        self.mod.clear_auth_states()

    def _ctx(self, driver):
        return {"driver": driver, "context": None, "global_vars": {}}

    def test_registered_as_builtins(self):
        assert get_builtin("save_auth_state") and get_builtin("use_auth_state")

    def test_save_then_use_in_new_context(self):
        shared, launches = SharedBrowser(), []
        d1 = _shared_driver(shared, launches)
        d1._ensure_browser()
        ret = get_builtin("save_auth_state")(name="admin", _context=self._ctx(d1))
        assert ret == {"success": True, "name": "admin", "cookies": 1, "origins": 1}
        assert "s3cret" not in str(ret)  # 返回值不含凭据，避免写入结果 XML
        d1.close()
        d2 = _shared_driver(shared, launches)
        get_builtin("use_auth_state")(name="admin", _context=self._ctx(d2))
        assert d2.context.cookies_added[0]["value"] == "s3cret"
        script = d2.context.init_scripts[0]
        assert "http://127.0.0.1:8766" in script and "t0k" in script and "sessionStorage" in script

    def test_use_missing_state_explains_order(self):
        with pytest.raises(RuntimeError) as e:
            get_builtin("use_auth_state")(name="nobody", _context=self._ctx(Mock()))
        assert "save_auth_state(name='nobody')" in str(e.value) and "顺序" in str(e.value)

    def test_save_after_close_fails_with_hint(self):
        drv = PlaywrightDriver(headless=True)
        drv._is_closed = True
        with pytest.raises(RuntimeError) as e:
            get_builtin("save_auth_state")(name="admin", _context=self._ctx(drv))
        assert "close 之前" in str(e.value)

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            get_builtin("save_auth_state")(name="  ", _context=self._ctx(Mock()))

    def test_non_web_driver_rejected(self):
        self.mod._AUTH_STATES["admin"] = {"cookies": [], "origins": []}
        with pytest.raises(RuntimeError) as e:
            get_builtin("use_auth_state")(name="admin", _context=self._ctx(object()))
        assert "Playwright" in str(e.value)

    def test_use_after_navigate_rejected(self):
        shared, launches = SharedBrowser(), []
        drv = _shared_driver(shared, launches)
        drv._ensure_browser()
        drv.page.url = "http://127.0.0.1:8766/home.html"
        self.mod._AUTH_STATES["admin"] = {"cookies": [], "origins": []}
        with pytest.raises(Exception) as e:
            get_builtin("use_auth_state")(name="admin", _context=self._ctx(drv))
        assert "navigate 之前" in str(e.value)

    def test_states_cleared_at_run_start(self, tmp_path):
        self.mod._AUTH_STATES["stale"] = {}
        ex = _executor(tmp_path)
        ex.execute_all_cases()
        assert "stale" not in self.mod._AUTH_STATES
        ex.close()

    def test_run_use_auth_state_recreates_closed_driver(self, tmp_path):
        new_driver = _mock_driver()
        ex = _executor(tmp_path, factory=lambda *a, **k: new_driver)
        ex._driver_closed = True
        ex._current_case_steps_log = []
        seen = {}

        def fake_execute(action, params):
            seen["driver"] = ex.keyword_engine.driver
            ex.keyword_engine.store_return({"success": True})
            return True

        ex._ensure_driver_alive()  # 先重建一次以便挂 fake
        ex._driver_closed = True
        ex.keyword_engine.execute = fake_execute
        orig = ex._ensure_driver_alive

        def ensure():
            orig()
            ex.keyword_engine.execute = fake_execute

        ex._ensure_driver_alive = ensure
        ex.execute_step({"action": "run", "model": "", "data": "use_auth_state(name='admin')"}, "预处理")
        assert seen["driver"] is new_driver and ex._driver_closed is False
        ex.close()


# ---------------------------------------------------------------- EvidenceMode
class TestEvidenceMode:
    def test_full_keeps_step_screenshots(self, tmp_path):
        ex = _executor(tmp_path)
        assert ex.evidence_mode == "full" and ex.auto_screenshot_on_step is True
        ex.close()

    def test_concise_disables_step_screenshots_keeps_failure(self, tmp_path):
        ex = _executor(tmp_path, evidence_mode="concise")
        assert ex.evidence_mode == "concise"
        assert ex.auto_screenshot_on_step is False
        assert ex.auto_screenshot is True  # 失败截图不受影响
        ex.close()

    def test_concise_from_globalvalue(self, tmp_path):
        ex = _executor(tmp_path, {"WaitTime": "0", "EvidenceMode": "concise"})
        assert ex.auto_screenshot_on_step is False
        ex.close()

    def test_concise_step_run_takes_no_screenshot(self, tmp_path):
        driver = _mock_driver()
        ex = _executor(tmp_path, driver=driver, evidence_mode="concise")
        ex.execute_all_cases()
        driver.screenshot.assert_not_called()
        ex.close()

    def test_result_xml_marks_modes(self, tmp_path):
        ex = _executor(tmp_path, evidence_mode="concise", session_mode="shared_browser")
        ex.execute_all_cases()
        summary = ET.parse(ex.result_writer.current_run_dir / "result.xml").getroot().find("summary")
        assert summary.get("evidence_mode") == "concise"
        assert summary.get("session_mode") == "shared_browser"
        ex.close()

    def test_concise_scenario_failure_screenshot_named_failure(self, tmp_path):
        driver = _mock_driver()
        driver.page = object()
        ex = _executor(tmp_path, driver=driver, evidence_mode="concise")
        ex.result_writer._init_run_dir()
        ex._current_case_id = "TC001"
        ex._current_scenario_id = "S1"
        ex._current_scenario_title = "场景"
        ex._current_case_steps_log = []
        ex._capture_concise_failure_screenshot("用例")
        path = driver.screenshot.call_args[0][0]
        assert "TC001_S1" in path and path.endswith("_failure.png")
        ex.close()

    def test_full_mode_no_extra_failure_step_screenshot(self, tmp_path):
        driver = _mock_driver()
        ex = _executor(tmp_path, driver=driver)
        ex._current_scenario_id = "S1"
        ex._capture_concise_failure_screenshot("用例")
        driver.screenshot.assert_not_called()
        ex.close()
