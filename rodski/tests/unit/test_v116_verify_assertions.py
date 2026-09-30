"""v11.6.0 WI-64-02 断言能力单元测试

覆盖：
- AssertionEngine 新操作符 $count / $count_gte / $count_lte / $exists / $visible（含 0 匹配不静默）
- verify 自动重试（成功 / 超时 / AutoWait=0 / 非法配置 / 旧键 VerifyTimeout 报改名 / 接口模型不重试）
- page 定位类型（url / title / path / dialog）读取
- ModelParser 解析 page 类型与 location@frame，model.xsd 接受新语法
"""
from unittest.mock import MagicMock

import pytest

try:
    from rodski.core.assertion_engine import AssertionEngine, AssertionError as AssertOpError
    from rodski.core.keyword_engine import KeywordEngine
    from rodski.core.model_parser import ModelParser
    from rodski.core.exceptions import (
        AssertionFailedError, InvalidParameterError, ModelParseError, XmlSchemaValidationError,
    )
    from rodski.drivers.playwright_driver import PlaywrightDriver
except ImportError:  # pragma: no cover - 以 rodski/ 为根运行
    from core.assertion_engine import AssertionEngine, AssertionError as AssertOpError
    from core.keyword_engine import KeywordEngine
    from core.model_parser import ModelParser
    from core.exceptions import (
        AssertionFailedError, InvalidParameterError, ModelParseError, XmlSchemaValidationError,
    )
    from drivers.playwright_driver import PlaywrightDriver


MODEL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="Table" type="ui">
    <element name="rows" type="web"><location type="css">#body tr.row</location></element>
    <element name="total" type="web"><location type="id">total</location></element>
  </model>
  <model name="PageInfo" type="ui">
    <element name="currentPath" type="web"><location type="page">path</location></element>
    <element name="pageTitle" type="web"><location type="page">title</location></element>
    <element name="currentUrl" type="web"><location type="page">url</location></element>
    <element name="dialog" type="web"><location type="page">dialog</location></element>
  </model>
  <model name="Pay" type="ui">
    <element name="payBtn" type="web"><location type="css" frame="#outer &gt;&gt; #payFrame">button.pay</location></element>
    <element name="result" type="web"><location type="id" frame="#payFrame">payResult</location></element>
  </model>
  <model name="Api" type="interface">
    <element name="code" type="interface"><location type="field">code</location></element>
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


def _engine(parser, row, driver=None, verify_timeout="0", table=None):
    data_manager = MagicMock()
    data_manager.get_data.return_value = row
    gv = {"DefaultValue": {"AutoWait": _auto_wait_ms(verify_timeout)}} if verify_timeout is not None else {}
    engine = KeywordEngine(driver or MagicMock(), model_parser=parser,
                           data_manager=data_manager, global_vars=gv)
    return engine


# ───────────────────────────── AssertionEngine ─────────────────────────────

class TestElementOperators:
    def test_new_operators_are_supported(self):
        for op in ("$count", "$count_gte", "$count_lte", "$exists", "$visible"):
            assert AssertionEngine.is_operator_dict({op: 1})
            assert AssertionEngine.is_element_operator({op: 1})
        assert not AssertionEngine.is_element_operator({"$gt": 1})

    def test_count_equal(self):
        assert AssertionEngine.evaluate(10, {"$count": 10})
        assert AssertionEngine.evaluate("10", {"$count": "10"})

    def test_count_zero_match_fails_with_expected_and_actual(self):
        with pytest.raises(AssertOpError) as ei:
            AssertionEngine.evaluate(0, {"$count": 10})
        assert "10" in str(ei.value) and "实际 0" in str(ei.value)

    def test_count_none_is_zero_not_skipped(self):
        with pytest.raises(AssertOpError, match="实际 0"):
            AssertionEngine.evaluate(None, {"$count": 1})
        assert AssertionEngine.evaluate(None, {"$count": 0})

    def test_count_gte_lte(self):
        assert AssertionEngine.evaluate(3, {"$count_gte": 1})
        assert AssertionEngine.evaluate(3, {"$count_lte": 3})
        with pytest.raises(AssertOpError, match="至少 1"):
            AssertionEngine.evaluate(0, {"$count_gte": 1})
        with pytest.raises(AssertOpError, match="至多 2"):
            AssertionEngine.evaluate(3, {"$count_lte": 2})

    def test_exists(self):
        assert AssertionEngine.evaluate(2, {"$exists": True})
        assert AssertionEngine.evaluate(0, {"$exists": False})
        assert AssertionEngine.evaluate(0, {"$exists": "false"})
        with pytest.raises(AssertOpError, match="期望元素存在"):
            AssertionEngine.evaluate(0, {"$exists": True})
        with pytest.raises(AssertOpError, match="期望元素不存在"):
            AssertionEngine.evaluate(1, {"$exists": False})

    def test_visible(self):
        assert AssertionEngine.evaluate(True, {"$visible": True})
        assert AssertionEngine.evaluate(False, {"$visible": False})
        with pytest.raises(AssertOpError, match="期望可见"):
            AssertionEngine.evaluate(False, {"$visible": True})

    @pytest.mark.parametrize("bad", [{"$count": -1}, {"$count": 1.5}, {"$count": "abc"},
                                     {"$count": True}, {"$exists": "maybe"}])
    def test_invalid_expected_is_value_error(self, bad):
        with pytest.raises(ValueError):
            AssertionEngine.evaluate(1, bad)


# ───────────────────────────── verify 元素断言 ─────────────────────────────

class TestVerifyElementState:
    def test_count_pass_uses_count_not_text(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = 10
        driver.get_text_locator.return_value = "共 10 条"
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "共 10 条"}, driver)
        assert engine.execute("verify", {"model": "Table", "data": "V1"})
        driver.count_elements.assert_called_once_with("#body tr.row", frame=None)
        driver.get_text_locator.assert_called_once_with("#total")

    def test_zero_match_fails_with_expected_10_actual_0(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = 0
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "BLANK"}, driver)
        with pytest.raises(AssertionFailedError) as ei:
            engine.execute("verify", {"model": "Table", "data": "V1"})
        msg = str(ei.value)
        assert "10" in msg and "实际='0'" in msg and "实际 0" in msg

    def test_count_none_from_driver_is_zero(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = None
        engine = _engine(parser, {"rows": '{"$exists": true}', "total": "BLANK"}, driver)
        with pytest.raises(AssertionFailedError, match="期望元素存在"):
            engine.execute("verify", {"model": "Table", "data": "V1"})

    def test_exists_false_passes_on_zero(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = 0
        engine = _engine(parser, {"rows": '{"$exists": false}', "total": "BLANK"}, driver)
        assert engine.execute("verify", {"model": "Table", "data": "V1"})

    def test_visible_uses_is_element_visible(self, parser):
        driver = MagicMock()
        driver.is_element_visible.return_value = False
        engine = _engine(parser, {"rows": "BLANK", "total": '{"$visible": false}'}, driver)
        assert engine.execute("verify", {"model": "Table", "data": "V1"})
        driver.is_element_visible.assert_called_once_with('[id="total"]', frame=None)

    def test_invalid_operator_value_is_contract_error(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = 1
        engine = _engine(parser, {"rows": '{"$count": "ten"}', "total": "BLANK"}, driver)
        with pytest.raises(InvalidParameterError, match=r"\$count"):
            engine.execute("verify", {"model": "Table", "data": "V1"})

    def test_driver_without_count_support_reports_clearly(self, parser):
        class TextOnlyDriver:
            def get_text_locator(self, locator):
                return ""
        engine = _engine(parser, {"rows": '{"$count": 1}', "total": "BLANK"}, TextOnlyDriver())
        with pytest.raises(InvalidParameterError, match="不支持"):
            engine.execute("verify", {"model": "Table", "data": "V1"})

    def test_element_operator_on_interface_model_rejected(self, parser):
        engine = _engine(parser, {"code": '{"$count": 1}'})
        engine.store_return({"code": 200})
        with pytest.raises(InvalidParameterError, match="只能用于 UI 模型"):
            engine.execute("verify", {"model": "Api", "data": "V1"})

    def test_frame_passed_to_driver(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = 1
        driver.get_text_locator.return_value = "支付成功"
        engine = _engine(parser, {"payBtn": '{"$count": 1}', "result": "支付成功"}, driver)
        assert engine.execute("verify", {"model": "Pay", "data": "V1"})
        driver.count_elements.assert_called_once_with("button.pay", frame="#outer >> #payFrame")
        driver.get_text_locator.assert_called_once_with('[id="payResult"]', frame="#payFrame")


# ───────────────────────────── page 定位类型 ─────────────────────────────

class TestPageLocator:
    def test_page_properties(self, parser):
        driver = MagicMock()
        driver.get_page_property.side_effect = lambda name: {
            "path": "/login.html", "title": "登录", "url": "http://x/login.html", "dialog": "确认?",
        }[name]
        row = {"currentPath": "/login.html", "pageTitle": "登录",
               "currentUrl": '{"$contains": "/login"}', "dialog": "确认?"}
        engine = _engine(parser, row, driver)
        assert engine.execute("verify", {"model": "PageInfo", "data": "V1"})
        driver.get_text_locator.assert_not_called()

    def test_page_mismatch(self, parser):
        driver = MagicMock()
        driver.get_page_property.side_effect = lambda name: "/protected.html" if name == "path" else "x"
        row = {"currentPath": "/login.html", "pageTitle": "BLANK", "currentUrl": "BLANK", "dialog": "BLANK"}
        engine = _engine(parser, row, driver)
        with pytest.raises(AssertionFailedError, match="/protected.html"):
            engine.execute("verify", {"model": "PageInfo", "data": "V1"})

    def test_element_operator_on_page_element_rejected(self, parser):
        # CORE §2.5.6 page 约束第 3 条：$count/$exists/$visible 不适用于 page 元素（校验先于执行）
        driver = MagicMock()
        driver.get_page_property.return_value = None
        row = {"currentPath": "BLANK", "pageTitle": "BLANK", "currentUrl": "BLANK",
               "dialog": '{"$exists": false}'}
        engine = _engine(parser, row, driver, verify_timeout="5")
        with pytest.raises(InvalidParameterError, match="page 元素"):
            engine.execute("verify", {"model": "PageInfo", "data": "V1"})

    def test_playwright_get_page_property(self):
        d = PlaywrightDriver(headless=True)
        d.browser = object()  # 跳过懒启动
        d.page = MagicMock()
        d.page.url = "http://127.0.0.1:8766/login.html?next=%2Fp#top"
        d.page.title.return_value = "登录"
        assert d.get_page_property("path") == "/login.html"
        assert d.get_page_property("url") == d.page.url
        assert d.get_page_property("title") == "登录"
        assert d.get_page_property("dialog") is None
        d._last_dialog_text = "确认删除?"
        assert d.get_page_property("dialog") == "确认删除?"

    def test_playwright_count_in_nested_frame(self):
        d = PlaywrightDriver(headless=True)
        d.browser = object()
        d.page = MagicMock()
        inner = d.page.frame_locator.return_value.frame_locator.return_value
        inner.locator.return_value.count.return_value = 3
        assert d.count_elements("button.pay", frame="#outer >> #payFrame") == 3
        d.page.frame_locator.assert_called_once_with("#outer")
        d.page.frame_locator.return_value.frame_locator.assert_called_once_with("#payFrame")


# ───────────────────────────── 自动重试 ─────────────────────────────

class TestVerifyAutoRetry:
    def test_retry_until_match(self, parser):
        driver = MagicMock()
        driver.count_elements.side_effect = [0, 4, 10]
        driver.get_text_locator.side_effect = ["", "", "共 10 条"]
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "共 10 条"}, driver,
                         verify_timeout="5")
        assert engine.execute("verify", {"model": "Table", "data": "V1"})
        assert driver.count_elements.call_count == 3
        assert engine.get_return(-1)["passed"] is True

    def test_timeout_reports_last_actual(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = 0
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "BLANK"}, driver,
                         verify_timeout="0.5")
        with pytest.raises(AssertionFailedError, match="已自动重试") as ei:
            engine.execute("verify", {"model": "Table", "data": "V1"})
        assert "实际='0'" in str(ei.value)
        assert driver.count_elements.call_count >= 2

    def test_timeout_zero_is_single_shot(self, parser):
        driver = MagicMock()
        driver.count_elements.return_value = 0
        engine = _engine(parser, {"rows": '{"$count": 10}', "total": "BLANK"}, driver,
                         verify_timeout="0")
        with pytest.raises(AssertionFailedError):
            engine.execute("verify", {"model": "Table", "data": "V1"})
        assert driver.count_elements.call_count == 1

    def test_unset_timeout_means_no_retry(self, parser):
        """v11.7.1: 未设置 AutoWait = 不自动等待（verify 单次比对）"""
        engine = _engine(parser, {}, verify_timeout=None)
        assert engine._resolve_verify_timeout() == 0.0

    @pytest.mark.parametrize("bad", ["-1", "abc"])
    def test_invalid_timeout(self, parser, bad):
        engine = _engine(parser, {"rows": '{"$count": 1}', "total": "BLANK"}, verify_timeout=bad)
        with pytest.raises(InvalidParameterError, match="AutoWait"):
            engine.execute("verify", {"model": "Table", "data": "V1"})

    def test_legacy_verify_timeout_key_is_rejected_with_rename_hint(self, parser):
        """v11.6.0 开发期名称 VerifyTimeout 已更名为 AutoWait（毫秒），出现时报错而不是静默忽略。"""
        dm = MagicMock()
        dm.get_data.return_value = {"rows": '{"$count": 1}', "total": "BLANK"}
        engine = KeywordEngine(MagicMock(), model_parser=parser, data_manager=dm,
                               global_vars={"DefaultValue": {"VerifyTimeout": "5"}})
        with pytest.raises(InvalidParameterError, match="已更名为 DefaultValue.AutoWait"):
            engine.execute("verify", {"model": "Table", "data": "V1"})

    def test_auto_wait_is_milliseconds(self, parser):
        engine = _engine(parser, {}, verify_timeout=None)
        engine._global_vars = {"DefaultValue": {"AutoWait": "2500"}}
        assert engine._resolve_verify_timeout() == 2.5

    def test_interface_verify_not_retried(self, parser):
        engine = _engine(parser, {"code": "201"}, verify_timeout="5")
        engine.store_return({"code": 200})
        import time
        t0 = time.monotonic()
        with pytest.raises(AssertionFailedError):
            engine.execute("verify", {"model": "Api", "data": "V1"})
        assert time.monotonic() - t0 < 1.5

    def test_contract_error_not_retried(self, parser):
        driver = MagicMock()
        engine = _engine(parser, {"rows": '{"$count": 1}'}, driver, verify_timeout="5")
        with pytest.raises(InvalidParameterError, match="match_mode"):
            engine.execute("verify", {"model": "Table", "data": "V1"})


# ───────────────────────────── ModelParser / XSD ─────────────────────────────

class TestModelParserPageAndFrame:
    def test_page_and_frame_parsed(self, parser):
        path = parser.get_model("PageInfo")["currentPath"]
        assert path["locator_type"] == "page" and path["locator_value"] == "path"
        assert path["frame"] is None
        pay = parser.get_model("Pay")["payBtn"]
        assert pay["frame"] == "#outer >> #payFrame"
        assert pay["locations"][0]["frame"] == "#outer >> #payFrame"
        assert parser.get_element("Pay.result")["frame"] == "#payFrame"

    def test_invalid_page_value_rejected(self, tmp_path):
        p = tmp_path / "model.xml"
        p.write_text("""<models><model name="P" type="ui">
          <element name="x" type="web"><location type="page">href</location></element>
        </model></models>""", encoding="utf-8")
        with pytest.raises(ModelParseError, match="url / title / path / dialog"):
            ModelParser(str(p))

    def test_page_with_frame_rejected(self, tmp_path):
        p = tmp_path / "model.xml"
        p.write_text("""<models><model name="P" type="ui">
          <element name="x" type="web"><location type="page" frame="#f">title</location></element>
        </model></models>""", encoding="utf-8")
        with pytest.raises(ModelParseError, match="frame"):
            ModelParser(str(p))

    def test_empty_frame_rejected_by_xsd(self, tmp_path):
        p = tmp_path / "model.xml"
        p.write_text("""<models><model name="P" type="ui">
          <element name="x" type="web"><location type="css" frame=" ">b</location></element>
        </model></models>""", encoding="utf-8")
        with pytest.raises(XmlSchemaValidationError):
            ModelParser(str(p))

    def test_unknown_locator_type_still_rejected_by_xsd(self, tmp_path):
        p = tmp_path / "model.xml"
        p.write_text("""<models><model name="P" type="ui">
          <element name="x" type="web"><location type="url">x</location></element>
        </model></models>""", encoding="utf-8")
        with pytest.raises(XmlSchemaValidationError):
            ModelParser(str(p))
