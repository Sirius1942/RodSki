"""launch 关键字单元测试 (T41-003)

验证：
1. case.xsd ActionType 包含 launch
2. _kw_launch 在 model="" 时不抛出 NameError（Desktop 场景）
3. _kw_launch 在接口模型时抛出 InvalidParameterError
"""
import os
import pytest
from unittest.mock import MagicMock
from lxml import etree

from core.keyword_engine import KeywordEngine
from core.exceptions import InvalidParameterError
from core.model_parser import MODEL_TYPE_UI, MODEL_TYPE_INTERFACE


SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "schemas", "case.xsd"
)


class TestLaunchSchemaValidation:
    """case.xsd 应接受 action='launch'"""

    @pytest.fixture
    def schema(self):
        schema_doc = etree.parse(SCHEMA_PATH)
        return etree.XMLSchema(schema_doc)

    def test_action_launch_accepted(self, schema):
        """action='launch' 应通过 schema 验证"""
        xml_str = """<?xml version="1.0" encoding="UTF-8"?>
        <cases>
          <case execute="是" id="tc_launch" title="启动应用">
            <test_case>
              <test_step action="launch" model="" data="TextEdit.app"/>
            </test_case>
          </case>
        </cases>
        """
        doc = etree.fromstring(xml_str.encode("utf-8"))
        assert schema.validate(doc), schema.error_log

    def test_action_invalid_rejected(self, schema):
        """无效 action 应被 schema 拒绝"""
        xml_str = """<?xml version="1.0" encoding="UTF-8"?>
        <cases>
          <case execute="是" id="tc_bad" title="无效动作">
            <test_case>
              <test_step action="invalid_action" model="" data="x"/>
            </test_case>
          </case>
        </cases>
        """
        doc = etree.fromstring(xml_str.encode("utf-8"))
        assert not schema.validate(doc)


class TestLaunchKeywordRuntime:
    """_kw_launch 运行时行为"""

    def _make_engine(self, model_type=MODEL_TYPE_UI, driver_type="web"):
        """构造带 mock 的 KeywordEngine"""
        driver = MagicMock()
        driver.launch.return_value = True
        driver.navigate.return_value = True

        model_parser = MagicMock()
        model_parser.get_model_type.return_value = model_type
        model_parser.get_model_driver_type.return_value = driver_type

        engine = KeywordEngine(driver=driver)
        engine.model_parser = model_parser
        engine.data_manager = MagicMock()
        return engine, driver

    def test_launch_desktop_no_name_error(self):
        """model='' + data='TextEdit.app' 不应抛出 NameError"""
        engine, driver = self._make_engine(model_type=MODEL_TYPE_UI, driver_type="web")
        params = {"model": "", "data": "TextEdit.app"}

        # 不应抛出 NameError（修复前的 bug）
        result = engine._kw_launch(params)
        assert result is True
        driver.launch.assert_called_once_with(app_path="TextEdit.app")

    def test_launch_url_navigates(self):
        """model='' + data='https://example.com' 应调用 navigate"""
        engine, driver = self._make_engine(model_type=MODEL_TYPE_UI, driver_type="web")
        params = {"model": "", "data": "https://example.com"}

        result = engine._kw_launch(params)
        assert result is True
        driver.navigate.assert_called_once_with("https://example.com")

    def test_launch_interface_model_raises_error(self):
        """接口模型应抛出 InvalidParameterError"""
        engine, _ = self._make_engine(model_type=MODEL_TYPE_INTERFACE, driver_type="interface")
        params = {"model": "LoginAPI", "data": "test_data"}

        with pytest.raises(InvalidParameterError) as exc_info:
            engine._kw_launch(params)
        assert "launch 不支持接口模型" in str(exc_info.value)
        assert "请使用 send" in str(exc_info.value)

    def test_launch_missing_data_raises_error(self):
        """缺少 data 参数应抛出 InvalidParameterError"""
        engine, _ = self._make_engine(model_type=MODEL_TYPE_UI, driver_type="web")
        params = {"model": "", "data": ""}

        with pytest.raises(InvalidParameterError):
            engine._kw_launch(params)
