"""v11.6.0 评审问题修复的回归单测。

- verify 轮询：驱动无等待读取（set_instant_reads）、瞬时 DriverError 视为本轮未匹配继续重试
- page 元素禁止元素级操作符；ModelParser 拦截 page 混用与视觉定位器 frame
- 用例开始时清除驱动遗留的弹窗状态
- --workers：单引号用例 id 发现、按已选用例补行、进程内 hook 回落顺序执行
"""
from __future__ import annotations

import argparse
import time
from unittest.mock import MagicMock

import pytest

from rodski.core import parallel_runner as pr
from rodski.core.exceptions import (
    AssertionFailedError, DriverError, DriverStoppedError, InvalidParameterError, ModelParseError,
    RetryExhaustedError,
)
from rodski.core.keyword_engine import KeywordEngine
from rodski.core.model_parser import ModelParser
from rodski.drivers.playwright_driver import PlaywrightDriver
from rodski.rodski_cli import run as run_cli


MODEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="Table" type="ui">
    <element name="rows" type="web"><location type="css">#body tr.row</location></element>
    <element name="total" type="web"><location type="id">total</location></element>
  </model>
  <model name="PageInfo" type="ui">
    <element name="currentUrl" type="web"><location type="page">url</location></element>
  </model>
</models>
"""


@pytest.fixture
def parser(tmp_path):
    p = tmp_path / "model.xml"
    p.write_text(MODEL_XML, encoding="utf-8")
    return ModelParser(str(p))


def _auto_wait_ms(seconds):
    """测试沿用"秒"表达超时，写入 globalvalue 时换算为 DefaultValue.AutoWait（毫秒）；非数值原样透传以测非法配置。"""
    try:
        return f"{float(seconds) * 1000:g}"
    except (TypeError, ValueError):
        return seconds


def _engine(parser, row, driver, verify_timeout):
    dm = MagicMock()
    dm.get_data.return_value = row
    return KeywordEngine(driver, model_parser=parser, data_manager=dm,
                         global_vars={"DefaultValue": {"AutoWait": _auto_wait_ms(verify_timeout)}})


# ───────────────────────── verify 轮询 ─────────────────────────

class TestVerifyTransientErrors:
    def test_transient_driver_error_is_retried(self, parser):
        driver = MagicMock()
        driver.count_elements.side_effect = [DriverError("Execution context was destroyed"), 10]
        driver.get_text_locator.return_value = "共 10 条"
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "共 10 条"}, driver, "5")
        assert engine.execute("verify", {"model": "Table", "data": "V1"})
        assert driver.count_elements.call_count == 2

    def test_raw_playwright_error_is_retried(self, parser):
        err_cls = type("Error", (Exception,), {"__module__": "playwright._impl._errors"})
        driver = MagicMock()
        driver.get_page_property.side_effect = [err_cls("navigating"), "http://x/home.html"]
        engine = _engine(parser, {"currentUrl": "http://x/home.html"}, driver, "5")
        assert engine.execute("verify", {"model": "PageInfo", "data": "V1"})

    def test_persistent_error_raised_after_timeout(self, parser):
        driver = MagicMock()
        driver.count_elements.side_effect = DriverError("boom")
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "BLANK"}, driver, "0.5")
        t0 = time.monotonic()
        # 执行层把驱动错误包装为 RetryExhaustedError，原因仍是最后一次的读取错误
        with pytest.raises((DriverError, RetryExhaustedError), match="boom"):
            engine.execute("verify", {"model": "Table", "data": "V1"})
        assert 0.4 <= time.monotonic() - t0 < 2
        assert driver.count_elements.call_count >= 2

    def test_timeout_zero_raises_immediately(self, parser):
        driver = MagicMock()
        driver.count_elements.side_effect = DriverError("boom")
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "BLANK"}, driver, "0")
        with pytest.raises((DriverError, RetryExhaustedError), match="boom"):
            engine.execute("verify", {"model": "Table", "data": "V1"})
        assert driver.count_elements.call_count == 1

    def test_driver_stopped_not_retried(self, parser):
        driver = MagicMock()
        driver.count_elements.side_effect = DriverStoppedError("stopped")
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "BLANK"}, driver, "5")
        t0 = time.monotonic()
        with pytest.raises(DriverStoppedError):
            engine.execute("verify", {"model": "Table", "data": "V1"})
        assert time.monotonic() - t0 < 1
        assert driver.count_elements.call_count == 1

    def test_instant_reads_toggled_around_polling(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = 0
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "BLANK"}, driver, "0")
        with pytest.raises(AssertionFailedError):
            engine.execute("verify", {"model": "Table", "data": "V1"})
        assert [c.args for c in driver.set_instant_reads.call_args_list] == [(True,), (False,)]

    def test_page_element_rejects_element_operator(self, parser):
        driver = MagicMock()
        driver.get_page_property.return_value = "http://x"
        engine = _engine(parser, {"currentUrl": '{"$count": 1}'}, driver, "5")
        with pytest.raises(InvalidParameterError, match="page 元素"):
            engine.execute("verify", {"model": "PageInfo", "data": "V1"})


class TestPlaywrightInstantRead:
    def _driver(self):
        d = PlaywrightDriver(headless=True)
        d.browser = object()  # 跳过懒启动
        d.page = MagicMock()
        return d

    def test_missing_element_returns_none_without_waiting(self):
        d = self._driver()
        d.set_instant_reads(True)
        d.page.locator.return_value.count.return_value = 0
        assert d.get_text_locator("#nope") is None
        d.page.text_content.assert_not_called()
        d.page.locator.return_value.first.text_content.assert_not_called()

    def test_present_element_read_with_short_timeout(self):
        d = self._driver()
        d.set_instant_reads(True)
        loc = d.page.locator.return_value
        loc.count.return_value = 2
        loc.first.text_content.return_value = "ok"
        assert d.get_text_locator("#a") == "ok"
        loc.first.text_content.assert_called_once_with(timeout=PlaywrightDriver.INSTANT_READ_TIMEOUT_MS)

    def test_default_mode_waits_up_to_auto_wait(self):
        """v11.7.0: 非 verify 轮询读取等待元素出现，上限为 AutoWait（不再是 Playwright 默认 30s）"""
        d = self._driver()
        d.set_auto_wait(2500)
        d.page.locator.return_value.first.text_content.return_value = "t"
        assert d.get_text_locator("#a") == "t"
        d.page.locator.return_value.first.text_content.assert_called_once_with(timeout=2500)


# ───────────────────────── ModelParser ─────────────────────────

def _parse(tmp_path, element_body):
    p = tmp_path / "m.xml"
    p.write_text(
        f'<models><model name="M" type="ui"><element name="e" type="web">{element_body}</element>'
        f'</model></models>', encoding="utf-8")
    return ModelParser(str(p))


class TestModelParserConstraints:
    def test_page_mixed_with_other_locator_rejected(self, tmp_path):
        with pytest.raises(ModelParseError, match="不能与其他"):
            _parse(tmp_path, '<location type="page">url</location><location type="id">x</location>')

    @pytest.mark.parametrize("vtype", ["vision", "ocr", "vision_bbox", "vision_image"])
    def test_vision_locator_with_frame_rejected(self, tmp_path, vtype):
        with pytest.raises(ModelParseError, match="frame"):
            _parse(tmp_path, f'<location type="{vtype}" frame="#f">登录按钮</location>')

    def test_single_page_locator_ok(self, tmp_path):
        _parse(tmp_path, '<location type="page">title</location>')


# ───────────────────────── 弹窗状态按用例清除 ─────────────────────────

class TestDialogStateReset:
    def test_driver_reset_clears_all_fields(self):
        d = PlaywrightDriver(headless=True)
        d._dialog_once = ("accept", None)
        d._last_dialog_text = "旧弹窗"
        d._unexpected_dialog = "[alert] x"
        d.reset_case_dialog_state()
        assert d._dialog_once is None and d._last_dialog_text is None and d._unexpected_dialog is None
        assert d.get_page_property("dialog") is None

    def test_executor_resets_driver_before_each_case(self):
        from rodski.core.ski_executor import SKIExecutor
        d = PlaywrightDriver(headless=True)
        d._dialog_once = ("accept", None)
        d._last_dialog_text = "上一个用例的弹窗"
        fake = MagicMock(spec=[])
        fake.driver = d
        fake.keyword_engine = MagicMock(driver=d)
        SKIExecutor._reset_driver_case_state(fake)
        assert d._dialog_once is None and d._last_dialog_text is None

    def test_executor_reset_ignores_drivers_without_support(self):
        from rodski.core.ski_executor import SKIExecutor
        fake = MagicMock(spec=[])
        fake.driver = MagicMock()
        fake.keyword_engine = None
        SKIExecutor._reset_driver_case_state(fake)  # 不抛异常
        fake.driver.reset_case_dialog_state.assert_not_called()


# ───────────────────────── --workers ─────────────────────────

def test_discover_single_quoted_case_ids(tmp_path):
    mod = tmp_path / "product" / "P" / "M"
    (mod / "case").mkdir(parents=True)
    (mod / "case" / "q.xml").write_text(
        "<?xml version='1.0' encoding='UTF-8'?><cases>"
        "<case execute='是' id='TC001' title='单引号'><test_case>"
        "<test_step action='wait' model='' data='1'/></test_case></case></cases>", encoding="utf-8")
    tasks = pr.discover_case_file_tasks(mod / "case", mod)
    assert tasks[0]["cases"] == [{"case_id": "TC001", "title": "单引号"}]


def test_discover_falls_back_to_regex_on_broken_xml(tmp_path):
    mod = tmp_path / "product" / "P" / "M"
    (mod / "case").mkdir(parents=True)
    (mod / "case" / "b.xml").write_text("<cases><case id='TC1' title=\"t\"><test_case>", encoding="utf-8")
    tasks = pr.discover_case_file_tasks(mod / "case", mod)
    assert [c["case_id"] for c in tasks[0]["cases"]] == ["TC1"]


def _task(cf, cases):
    return pr.CaseFileTask(case_file=cf, path=cf, weight=1,
                           cases=[{"case_id": c, "title": ""} for c in cases])


def test_merge_uses_selected_cases_and_keeps_partial_results():
    tasks = [_task("a.xml", ["TC1", "TC2", "TC3", "TC4"])]
    outputs = [{
        "worker_id": 1, "case_files": ["a.xml"], "error": "RuntimeError: boom",
        "results": [{"case_file": "a.xml", "case_id": "TC1", "status": "PASS"}],
        # TC4 未被 selector 选中；TC3 由 plan 判定为 SKIP
        "selected": [
            {"case_file": "a.xml", "case_id": "TC1", "title": "", "skip_reason": ""},
            {"case_file": "a.xml", "case_id": "TC2", "title": "", "skip_reason": ""},
            {"case_file": "a.xml", "case_id": "TC3", "title": "", "skip_reason": "plan 未选中"},
        ],
    }]
    merged = pr.merge_worker_results(tasks, outputs)
    assert [(r["case_id"], r["status"]) for r in merged] == [("TC1", "PASS"), ("TC2", "FAIL"), ("TC3", "SKIP")]


def test_run_parallel_reads_selected_file_when_worker_crashes(tmp_path):
    import json
    from concurrent.futures import ThreadPoolExecutor

    tasks = [_task("a.xml", ["TC1", "TC2"]), _task("b.xml", ["TC9"])]

    seen_files = []

    def crashing_worker(spec):
        seen_files.append(spec["selected_file"])
        if "a.xml" in spec["case_files"]:
            from pathlib import Path
            Path(spec["selected_file"]).write_text(json.dumps(
                [{"case_file": "a.xml", "case_id": "TC2", "title": "", "skip_reason": ""}]), encoding="utf-8")
            raise RuntimeError("process died")
        return {"worker_id": spec["worker_id"], "case_files": spec["case_files"],
                "results": [{"case_file": "b.xml", "case_id": "TC9", "status": "PASS"}]}

    merged, outputs = pr.run_parallel(
        tmp_path, tmp_path, 2, tmp_path / "run", {}, tasks=tasks,
        worker_fn=crashing_worker, pool_factory=lambda n: ThreadPoolExecutor(max_workers=n),
    )
    assert [(r["case_id"], r["status"]) for r in merged] == [("TC2", "FAIL"), ("TC9", "PASS")]
    from pathlib import Path
    assert seen_files and not any(Path(f).parent.exists() for f in seen_files)  # 临时清单目录已清理


def test_plan_parallel_falls_back_for_in_process_hooks(tmp_path):
    mod = tmp_path / "product" / "P" / "M"
    for d in ("case", "model"):
        (mod / d).mkdir(parents=True)
    (mod / "model" / "model.xml").write_text("<models></models>", encoding="utf-8")
    for name in ("a.xml", "b.xml"):
        (mod / "case" / name).write_text(
            '<cases><case execute="是" id="TC1" title="t"><test_case>'
            '<test_step action="wait" model="" data="1"/></test_case></case></cases>', encoding="utf-8")
    ns = argparse.Namespace(model=None, cdp_endpoint=None, insert_steps=None, debug=False, roam=False,
                            trace=False, coverage=False,
                            _executor_hooks={"on_case_failure": [lambda *a: None],
                                             "before_keyword": [lambda *a: None]})
    _, reason = run_cli._plan_parallel(mod / "case", mod, ns)
    assert reason and "before_keyword" in reason

    ns._executor_hooks = {"on_case_failure": [lambda *a: None]}
    _, reason = run_cli._plan_parallel(mod / "case", mod, ns)
    assert reason is None
