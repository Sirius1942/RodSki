"""移动端 verify 断言测试 — Iteration 48"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile


def _write_model_xml(content: str, tmp_path) -> str:
    p = tmp_path / "model.xml"
    p.write_text(content, encoding="utf-8")
    return str(p)


def _make_android_model_xml(tmp_path) -> str:
    return _write_model_xml('''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginScreen" type="ui" driver_type="android">
    <element name="welcomeText">
      <type>text</type>
      <location type="id">com.rodski.demo:id/welcomeText</location>
    </element>
    <element name="errorMsg">
      <type>text</type>
      <location type="id">com.rodski.demo:id/errorMsg</location>
    </element>
  </model>
</models>''', tmp_path)


class TestMobileVerify:
    """T48-003: verify 在 android 模型下调用 get_element_text_by_locator"""

    def _make_engine_with_mock_appium(self, model_path, verify_data, mock_appium):
        """创建注入了 mock AppiumDriver 的 KeywordEngine"""
        from core.keyword_engine import KeywordEngine
        from core.model_parser import ModelParser
        engine = KeywordEngine.__new__(KeywordEngine)
        engine.driver = MagicMock()
        engine._desktop_drivers = {"android": mock_appium}
        engine._global_vars = {"Mobile": {"Platform": "android"}}
        engine._driver_factory = None
        engine._return_values = []
        engine.store_return = Mock()
        engine.data_resolver = None
        engine.model_parser = ModelParser(model_path)

        # mock data_manager
        dm = MagicMock()
        dm.get_data.return_value = verify_data
        engine.data_manager = dm
        return engine

    def test_verify_android_reads_element_text(self, tmp_path):
        """verify 在 android 模型下，调用 get_element_text_by_locator 读取实际值"""
        model_path = _make_android_model_xml(tmp_path)
        mock_appium = MagicMock()
        mock_appium.get_element_text_by_locator = Mock(return_value="欢迎，admin")

        verify_data = {"welcomeText": "欢迎，admin", "errorMsg": "NONE"}
        engine = self._make_engine_with_mock_appium(model_path, verify_data, mock_appium)

        # 执行 verify（不应抛出异常）
        engine._kw_verify({"model": "LoginScreen", "data": "V001"})

        # 验证调用了 get_element_text_by_locator
        mock_appium.get_element_text_by_locator.assert_called()

    def test_verify_android_mismatch_fails(self, tmp_path):
        """实际值与期望值不一致时，verify 步骤失败"""
        from core.exceptions import AssertionFailedError
        model_path = _make_android_model_xml(tmp_path)
        mock_appium = MagicMock()
        mock_appium.get_element_text_by_locator = Mock(return_value="欢迎，guest")

        verify_data = {"welcomeText": "欢迎，admin", "errorMsg": "NONE"}
        engine = self._make_engine_with_mock_appium(model_path, verify_data, mock_appium)

        with pytest.raises((AssertionFailedError, Exception)):
            engine._kw_verify({"model": "LoginScreen", "data": "V001"})

    def test_verify_android_none_field_skips(self, tmp_path):
        """_verify 表中字段值为 NONE 时，跳过该字段验证"""
        model_path = _make_android_model_xml(tmp_path)
        mock_appium = MagicMock()
        # welcomeText 返回正确值，errorMsg 为 NONE 应跳过
        mock_appium.get_element_text_by_locator = Mock(return_value="欢迎，admin")

        verify_data = {"welcomeText": "欢迎，admin", "errorMsg": "NONE"}
        engine = self._make_engine_with_mock_appium(model_path, verify_data, mock_appium)

        # 不应抛出异常
        engine._kw_verify({"model": "LoginScreen", "data": "V001"})
        # get_element_text_by_locator 只被调用一次（errorMsg 被跳过）
        assert mock_appium.get_element_text_by_locator.call_count == 1
