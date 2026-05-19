"""移动端协议接入测试 — Iteration 46"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# 测试辅助：创建临时 model.xml
def _write_model_xml(content: str, tmp_path) -> str:
    p = tmp_path / "model.xml"
    p.write_text(content, encoding="utf-8")
    return str(p)


class TestModelXsdAndroidIos:
    """T46-001: model.xsd 支持 android/ios driver_type"""

    def test_model_xsd_android_driver_type_valid(self, tmp_path):
        """model.xml 含 driver_type="android" 应通过 XSD 校验"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from core.xml_schema_validator import RodskiXmlValidator

        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginScreen" type="ui" driver_type="android">
    <element name="username">
      <type>input</type>
      <location type="id">com.rodski.demo:id/username</location>
    </element>
  </model>
</models>'''
        path = _write_model_xml(xml, tmp_path)
        # 不应抛出异常
        RodskiXmlValidator.validate_file(path, RodskiXmlValidator.KIND_MODEL)

    def test_model_xsd_ios_driver_type_valid(self, tmp_path):
        """model.xml 含 driver_type="ios" 应通过 XSD 校验"""
        from core.xml_schema_validator import RodskiXmlValidator
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginScreen" type="ui" driver_type="ios">
    <element name="username">
      <type>input</type>
      <location type="id">username</location>
    </element>
  </model>
</models>'''
        path = _write_model_xml(xml, tmp_path)
        RodskiXmlValidator.validate_file(path, RodskiXmlValidator.KIND_MODEL)

    def test_model_xsd_unknown_driver_type_invalid(self, tmp_path):
        """driver_type="unknown_platform" 应校验失败"""
        from core.xml_schema_validator import RodskiXmlValidator
        from core.exceptions import XmlSchemaValidationError
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginScreen" type="ui" driver_type="unknown_platform">
    <element name="username">
      <type>input</type>
      <location type="id">username</location>
    </element>
  </model>
</models>'''
        path = _write_model_xml(xml, tmp_path)
        with pytest.raises(Exception):  # XSD 校验失败
            RodskiXmlValidator.validate_file(path, RodskiXmlValidator.KIND_MODEL)


class TestModelParserAndroidIos:
    """T46-002: ModelParser 接受 android/ios driver_type"""

    def test_model_parser_android_driver_type(self, tmp_path):
        """ModelParser 解析 driver_type="android" 返回正确 driver_type"""
        from core.model_parser import ModelParser
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginScreen" type="ui" driver_type="android">
    <element name="username">
      <type>input</type>
      <location type="id">com.rodski.demo:id/username</location>
    </element>
  </model>
</models>'''
        path = _write_model_xml(xml, tmp_path)
        parser = ModelParser(path)
        assert parser.get_model_driver_type("LoginScreen") == "android"

    def test_model_parser_ios_driver_type(self, tmp_path):
        """ModelParser 解析 driver_type="ios" 返回正确 driver_type"""
        from core.model_parser import ModelParser
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginScreen" type="ui" driver_type="ios">
    <element name="username">
      <type>input</type>
      <location type="id">username</location>
    </element>
  </model>
</models>'''
        path = _write_model_xml(xml, tmp_path)
        parser = ModelParser(path)
        assert parser.get_model_driver_type("LoginScreen") == "ios"

    def test_model_parser_android_model_type_is_ui(self, tmp_path):
        """android driver_type 的模型类型应为 ui"""
        from core.model_parser import ModelParser, MODEL_TYPE_UI
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginScreen" type="ui" driver_type="android">
    <element name="username">
      <type>input</type>
      <location type="id">com.rodski.demo:id/username</location>
    </element>
  </model>
</models>'''
        path = _write_model_xml(xml, tmp_path)
        parser = ModelParser(path)
        assert parser.get_model_type("LoginScreen") == MODEL_TYPE_UI


class TestDriverFactoryAndroidIos:
    """T46-003: DriverFactory 创建 Android/iOS 驱动"""

    def setup_method(self):
        from core.driver_factory import DriverFactory
        DriverFactory.release_all()

    def teardown_method(self):
        from core.driver_factory import DriverFactory
        DriverFactory.release_all()

    def test_android_in_supported_types(self):
        from core.driver_factory import DriverFactory
        assert "android" in DriverFactory.SUPPORTED_DRIVER_TYPES

    def test_ios_in_supported_types(self):
        from core.driver_factory import DriverFactory
        assert "ios" in DriverFactory.SUPPORTED_DRIVER_TYPES

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_driver_factory_creates_android_driver(self, mock_remote):
        """DriverFactory.get_driver("android") 返回 AndroidDriver 实例"""
        from core.driver_factory import DriverFactory
        from drivers.android_driver import AndroidDriver
        mock_remote.return_value = MagicMock()
        driver = DriverFactory.get_driver("android",
            device_name="test_device",
            server_url="http://127.0.0.1:4723"
        )
        assert isinstance(driver, AndroidDriver)

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_driver_factory_creates_ios_driver(self, mock_remote):
        """DriverFactory.get_driver("ios") 返回 IOSDriver 实例"""
        from core.driver_factory import DriverFactory
        from drivers.ios_driver import IOSDriver
        mock_remote.return_value = MagicMock()
        driver = DriverFactory.get_driver("ios",
            device_name="iPhone",
            server_url="http://127.0.0.1:4723"
        )
        assert isinstance(driver, IOSDriver)

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_android_driver_uses_w3c_options(self, mock_remote):
        """AndroidDriver 使用 Appium 2.x W3C capabilities（UiAutomator2Options）"""
        from core.driver_factory import DriverFactory
        mock_remote.return_value = MagicMock()
        DriverFactory.get_driver("android",
            device_name="pixel",
            server_url="http://127.0.0.1:4723"
        )
        # W3C 方式：通过 options 关键字参数传入
        call_kwargs = mock_remote.call_args[1] if mock_remote.call_args[1] else {}
        call_args = mock_remote.call_args[0] if mock_remote.call_args[0] else ()
        # options 应该是 UiAutomator2Options 对象，不是裸 dict
        options = call_kwargs.get('options') or (call_args[1] if len(call_args) > 1 else None)
        assert options is not None
        # 验证 platform_name 属性
        assert hasattr(options, 'platform_name') or \
               (isinstance(options, dict) and options.get('platformName') == 'Android')


class TestKeywordEngineMobileRouting:
    """T46-004: KeywordEngine 移动端驱动路由"""

    def test_android_in_non_web_driver_types(self):
        """android 在 NON_WEB_DRIVER_TYPES 中"""
        from core.keyword_engine import KeywordEngine
        assert "android" in KeywordEngine.NON_WEB_DRIVER_TYPES

    def test_ios_in_non_web_driver_types(self):
        """ios 在 NON_WEB_DRIVER_TYPES 中"""
        from core.keyword_engine import KeywordEngine
        assert "ios" in KeywordEngine.NON_WEB_DRIVER_TYPES

    def test_desktop_driver_types_alias_exists(self):
        """DESKTOP_DRIVER_TYPES 作为向后兼容别名仍然存在"""
        from core.keyword_engine import KeywordEngine
        assert hasattr(KeywordEngine, 'DESKTOP_DRIVER_TYPES')

    def test_get_mobile_driver_method_exists(self):
        """_get_mobile_driver 方法存在"""
        from core.keyword_engine import KeywordEngine
        assert hasattr(KeywordEngine, '_get_mobile_driver')
