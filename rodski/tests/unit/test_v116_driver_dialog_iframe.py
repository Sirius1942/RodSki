"""v11.6.0 WI-64-03 驱动能力单元测试

覆盖：
- 原生弹窗：DialogPolicy（accept/dismiss/fail）、type 中 page=dialog 一次性处理、最近弹窗文本、
  未预期弹窗使步骤失败且不重试
- iframe：location@frame 传递到驱动动作，">>" 串联多层 frame_locator
- evaluate file:：模块内路径读取、拒绝绝对路径/越界/缺失
- XML 非良构报错附带 &amp; / file: 修复提示
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    from rodski.core.keyword_engine import KeywordEngine
    from rodski.core.model_parser import ModelParser
    from rodski.core.exceptions import (
        InvalidParameterError, RetryExhaustedError, UnexpectedDialogError, XmlSyntaxError, DriverError,
    )
    from rodski.core.xml_schema_validator import RodskiXmlValidator
    from rodski.drivers.playwright_driver import PlaywrightDriver
except ImportError:  # pragma: no cover - 以 rodski/ 为根运行
    from core.keyword_engine import KeywordEngine
    from core.model_parser import ModelParser
    from core.exceptions import (
        InvalidParameterError, RetryExhaustedError, UnexpectedDialogError, XmlSyntaxError, DriverError,
    )
    from core.xml_schema_validator import RodskiXmlValidator
    from drivers.playwright_driver import PlaywrightDriver


MODEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="DialogPage" type="ui">
    <element name="dialog" type="web"><location type="page">dialog</location></element>
    <element name="deleteBtn" type="web"><location type="id">deleteBtn</location></element>
  </model>
  <model name="PathPage" type="ui">
    <element name="currentPath" type="web"><location type="page">path</location></element>
  </model>
  <model name="Pay" type="ui">
    <element name="cardNo" type="web"><location type="css" frame="#outer &gt;&gt; #payFrame">#cardNo</location></element>
    <element name="payBtn" type="web"><location type="id" frame="#payFrame">payBtn</location></element>
  </model>
</models>
"""


@pytest.fixture
def parser(tmp_path):
    p = tmp_path / "model.xml"
    p.write_text(MODEL_XML, encoding="utf-8")
    return ModelParser(str(p))


def _engine(parser, row, driver=None, gv=None):
    data_manager = MagicMock()
    data_manager.get_data.return_value = row
    return KeywordEngine(driver or MagicMock(), model_parser=parser,
                         data_manager=data_manager, global_vars=gv or {})


def _driver_with_page():
    """未启动真实浏览器的 PlaywrightDriver：page/browser 用 Mock 代替。"""
    drv = PlaywrightDriver(headless=True)
    drv.browser = MagicMock()
    drv.page = MagicMock()
    return drv


def _dialog(message="确认删除?", dtype="confirm"):
    d = MagicMock()
    d.message = message
    d.type = dtype
    return d


# ───────────────────────────── 驱动：弹窗 ─────────────────────────────

class TestDriverDialog:
    def test_handler_hooked_once_per_page(self):
        drv = _driver_with_page()
        drv._ensure_browser()
        drv._ensure_browser()
        drv.page.on.assert_called_once_with("dialog", drv._on_dialog)
        # page 重建（如录像）后重新挂接
        drv.page = MagicMock()
        drv._ensure_browser()
        drv.page.on.assert_called_once_with("dialog", drv._on_dialog)

    def test_default_policy_fail_dismisses_and_records(self):
        drv = _driver_with_page()
        d = _dialog()
        drv._on_dialog(d)
        d.dismiss.assert_called_once()
        d.accept.assert_not_called()
        assert drv.get_last_dialog_text() == "确认删除?"
        assert drv.consume_unexpected_dialog() == "[confirm] 确认删除?"
        assert drv.consume_unexpected_dialog() is None

    def test_policy_accept_and_dismiss(self):
        drv = _driver_with_page()
        drv.set_dialog_policy("accept")
        d = _dialog()
        drv._on_dialog(d)
        d.accept.assert_called_once_with()
        assert drv.consume_unexpected_dialog() is None
        drv.set_dialog_policy("DISMISS")
        d2 = _dialog()
        drv._on_dialog(d2)
        d2.dismiss.assert_called_once()
        assert drv.consume_unexpected_dialog() is None

    def test_invalid_policy_rejected(self):
        with pytest.raises(DriverError):
            _driver_with_page().set_dialog_policy("ignore")

    def test_one_shot_handler_overrides_policy_once(self):
        drv = _driver_with_page()
        drv.register_dialog_handler("accept", "加急")
        p = _dialog("请输入备注", "prompt")
        drv._on_dialog(p)
        p.accept.assert_called_once_with("加急")
        assert drv.get_last_dialog_text() == "请输入备注"
        # 一次性：下一次弹窗回落到 fail 策略
        d = _dialog("再来一次")
        drv._on_dialog(d)
        d.dismiss.assert_called_once()
        assert drv.consume_unexpected_dialog() == "[confirm] 再来一次"

    def test_one_shot_dismiss(self):
        drv = _driver_with_page()
        drv.register_dialog_handler("dismiss")
        d = _dialog()
        drv._on_dialog(d)
        d.dismiss.assert_called_once()
        assert drv.consume_unexpected_dialog() is None

    def test_register_invalid_action(self):
        with pytest.raises(DriverError):
            _driver_with_page().register_dialog_handler("maybe")

    def test_accept_failure_still_closes_dialog(self):
        drv = _driver_with_page()
        drv.set_dialog_policy("accept")
        d = _dialog()
        d.accept.side_effect = RuntimeError("boom")
        drv._on_dialog(d)  # 回调内不抛出
        d.dismiss.assert_called_once()

    def test_page_property_dialog_reads_last_text(self):
        drv = _driver_with_page()
        assert drv.get_page_property("dialog") is None
        drv._on_dialog(_dialog("hello", "alert"))
        assert drv.get_page_property("dialog") == "hello"


# ───────────────────────────── 驱动：iframe ─────────────────────────────

class TestDriverFrame:
    def test_nested_frames_chain_frame_locator(self):
        drv = _driver_with_page()
        drv.type_locator("css=#cardNo", "6222", frame="#outer >> #payFrame")
        drv.page.frame_locator.assert_called_once_with("#outer")
        inner = drv.page.frame_locator.return_value.frame_locator
        inner.assert_called_once_with("#payFrame")
        target = inner.return_value.locator
        target.assert_called_once_with("#cardNo")
        target.return_value.first.fill.assert_called_once()
        assert target.return_value.first.fill.call_args[0][0] == "6222"
        drv.page.fill.assert_not_called()

    def test_click_in_frame(self):
        drv = _driver_with_page()
        assert drv.click_locator("id=payBtn", frame="#payFrame") is True
        loc = drv.page.frame_locator.return_value.locator
        loc.assert_called_once_with("#payBtn")
        loc.return_value.first.click.assert_called_once()
        drv.page.click.assert_not_called()

    def test_frame_failure_has_hint(self):
        drv = _driver_with_page()
        drv.page.frame_locator.return_value.locator.return_value.first.click.side_effect = RuntimeError("Timeout 10000ms exceeded")
        drv.page.frame_locator.return_value.locator.return_value.count.return_value = 0
        with pytest.raises(DriverError) as ei:
            drv.click_locator("id=payBtn", frame="#payFrame")
        assert "frame=#payFrame" in str(ei.value) and ">>" in str(ei.value)


# ───────────────────────────── 关键字：type 批量 ─────────────────────────────

class TestBatchTypeDialogAndFrame:
    def test_dialog_field_registered_before_click(self, parser):
        drv = MagicMock()
        calls = []
        drv.register_dialog_handler.side_effect = lambda *a: calls.append(("dialog", a))
        drv.click_locator.side_effect = lambda *a, **k: calls.append(("click", a)) or True
        engine = _engine(parser, {"dialog": "accept", "deleteBtn": "click"}, driver=drv)
        assert engine._batch_type("DialogPage", "D1") is True
        assert calls == [("dialog", ("accept", None)), ("click", ("id=deleteBtn",))]

    def test_prompt_text_and_dismiss(self, parser):
        drv = MagicMock()
        _engine(parser, {"dialog": "accept:加急:A", "deleteBtn": "BLANK"}, driver=drv)._batch_type("DialogPage", "D1")
        drv.register_dialog_handler.assert_called_with("accept", "加急:A")
        _engine(parser, {"dialog": "accept:", "deleteBtn": "BLANK"}, driver=drv)._batch_type("DialogPage", "D1")
        drv.register_dialog_handler.assert_called_with("accept", "")
        _engine(parser, {"dialog": "Dismiss", "deleteBtn": "BLANK"}, driver=drv)._batch_type("DialogPage", "D1")
        drv.register_dialog_handler.assert_called_with("dismiss", None)

    def test_blank_dialog_field_registers_nothing(self, parser):
        drv = MagicMock()
        _engine(parser, {"dialog": "BLANK", "deleteBtn": "click"}, driver=drv)._batch_type("DialogPage", "D1")
        drv.register_dialog_handler.assert_not_called()

    @pytest.mark.parametrize("bad", ["click", "dismiss:x", "yes", "accept_all"])
    def test_invalid_dialog_value(self, parser, bad):
        drv = MagicMock()
        with pytest.raises(InvalidParameterError) as ei:
            _engine(parser, {"dialog": bad, "deleteBtn": "click"}, driver=drv)._batch_type("DialogPage", "D1")
        assert "accept" in str(ei.value) and "dismiss" in str(ei.value)
        drv.click_locator.assert_not_called()

    def test_readonly_page_field_rejected(self, parser):
        with pytest.raises(InvalidParameterError) as ei:
            _engine(parser, {"currentPath": "/login"})._batch_type("PathPage", "P1")
        assert "BLANK" in str(ei.value) and "verify" in str(ei.value)

    def test_frame_passed_to_driver(self, parser):
        drv = MagicMock()
        _engine(parser, {"cardNo": "6222", "payBtn": "click"}, driver=drv)._batch_type("Pay", "P1")
        drv.type_locator.assert_called_once_with("css=#cardNo", "6222", frame="#outer >> #payFrame")
        drv.click_locator.assert_called_once_with("id=payBtn", frame="#payFrame")

    def test_unsupported_action_in_frame(self, parser):
        with pytest.raises(InvalidParameterError) as ei:
            _engine(parser, {"cardNo": "drag【#x】", "payBtn": "BLANK"})._batch_type("Pay", "P1")
        assert "iframe" in str(ei.value)


# ───────────────────────────── 关键字：执行期弹窗检查 ─────────────────────────────

class TestExecuteUnexpectedDialog:
    def test_unexpected_dialog_fails_step_without_retry(self, parser):
        drv = MagicMock()
        drv.consume_unexpected_dialog.return_value = "[confirm] 确认删除订单 ORD1?"
        engine = _engine(parser, {"dialog": "BLANK", "deleteBtn": "click"}, driver=drv)
        engine._retry_config["max_retries"] = 2
        with pytest.raises(UnexpectedDialogError) as ei:
            engine.execute("type", {"model": "DialogPage", "data": "D1"})
        assert "确认删除订单 ORD1?" in str(ei.value)
        assert "DialogPolicy" in str(ei.value)
        assert drv.click_locator.call_count == 1

    def test_mock_driver_without_dialog_does_not_fail(self, parser):
        # MagicMock 的 consume_unexpected_dialog 返回 Mock（非字符串），不能误判
        engine = _engine(parser, {"dialog": "BLANK", "deleteBtn": "click"})
        assert engine.execute("type", {"model": "DialogPage", "data": "D1"}) is True

    def test_policy_synced_to_driver(self, parser):
        drv = MagicMock()
        engine = _engine(parser, {"dialog": "BLANK", "deleteBtn": "click"}, driver=drv,
                         gv={"DefaultValue": {"DialogPolicy": "Accept"}})
        engine.execute("type", {"model": "DialogPage", "data": "D1"})
        drv.set_dialog_policy.assert_called_with("accept")

    def test_default_policy_is_fail(self, parser):
        drv = _driver_with_page()
        engine = _engine(parser, {}, driver=drv)
        drv._dialog_policy = "accept"
        engine._sync_dialog_policy()
        assert drv._dialog_policy == "fail"

    def test_invalid_policy_rejected(self, parser):
        engine = _engine(parser, {}, gv={"DefaultValue": {"DialogPolicy": "ignore"}})
        with pytest.raises(InvalidParameterError) as ei:
            engine.execute("type", {"model": "DialogPage", "data": "D1"})
        assert "DialogPolicy" in str(ei.value)


# ───────────────────────────── evaluate file: ─────────────────────────────

@pytest.fixture
def module_dir(tmp_path):
    mod = tmp_path / "product" / "proj" / "mod"
    (mod / "fun" / "js").mkdir(parents=True)
    (mod / "case").mkdir()
    (mod / "fun" / "js" / "check.js").write_text(
        "(() => { const a = 1; return a > 0 && `${a}` === '1'; })()", encoding="utf-8")
    (tmp_path / "secret.js").write_text("1", encoding="utf-8")
    return mod


class TestEvaluateFile:
    def _engine(self, module_dir, driver=None):
        resolver = MagicMock()
        resolver.resolve_with_return.side_effect = AssertionError("file: 脚本不应做 ${} 替换")
        return KeywordEngine(driver or MagicMock(), module_dir=str(module_dir), data_resolver=resolver)

    def test_reads_script_from_module(self, module_dir):
        drv = _driver_with_page()
        drv.page.evaluate.return_value = True
        engine = self._engine(module_dir, drv)
        assert engine._kw_evaluate({"data": "file:fun/js/check.js"}) is True
        script = drv.page.evaluate.call_args[0][0]
        assert "&&" in script and "${a}" in script
        assert engine.get_return(-1) is True

    @pytest.mark.parametrize("rel", ["../../../secret.js", "fun/../../../../secret.js"])
    def test_rejects_escape(self, module_dir, rel):
        with pytest.raises(InvalidParameterError) as ei:
            self._engine(module_dir)._kw_evaluate({"data": f"file:{rel}"})
        assert "越出模块目录" in str(ei.value)

    def test_rejects_absolute(self, module_dir, tmp_path):
        with pytest.raises(InvalidParameterError) as ei:
            self._engine(module_dir)._kw_evaluate({"data": f"file:{tmp_path / 'secret.js'}"})
        assert "绝对路径" in str(ei.value)

    def test_missing_and_empty(self, module_dir):
        with pytest.raises(InvalidParameterError, match="不存在"):
            self._engine(module_dir)._kw_evaluate({"data": "file:fun/js/nope.js"})
        with pytest.raises(InvalidParameterError, match="缺少脚本路径"):
            self._engine(module_dir)._kw_evaluate({"data": "file:"})

    def test_module_dir_from_case_file(self, module_dir):
        engine = KeywordEngine(MagicMock(), case_file=str(module_dir / "case" / "a.xml"))
        assert engine._resolve_evaluate_file("fun/js/check.js") == (module_dir / "fun/js/check.js").resolve()


# ───────────────────────────── XML 非良构提示 ─────────────────────────────

class TestXmlSyntaxHint:
    def test_ampersand_in_attribute(self, tmp_path):
        p = tmp_path / "c.xml"
        p.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<cases>\n  <case execute="是" id="TC001" title="x">\n'
            '    <test_case>\n      <test_step action="evaluate" model="" data="a && b"/>\n'
            '    </test_case>\n  </case>\n</cases>\n', encoding="utf-8")
        with pytest.raises(XmlSyntaxError) as ei:
            RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_CASE)
        msg = str(ei.value)
        assert "&amp;&amp;" in msg and "file:fun/js/" in msg and "第 5 行" in msg
        # 兼容存量 except ET.ParseError
        import xml.etree.ElementTree as ET
        assert isinstance(ei.value, ET.ParseError)

    def test_other_syntax_error_no_attr_hint(self, tmp_path):
        p = tmp_path / "m.xml"
        p.write_text('<?xml version="1.0"?>\n<models>\n  <model name="A" type="ui">\n</models>\n', encoding="utf-8")
        with pytest.raises(XmlSyntaxError) as ei:
            RodskiXmlValidator.validate_file(p, RodskiXmlValidator.KIND_MODEL)
        assert ei.value.hint is None
