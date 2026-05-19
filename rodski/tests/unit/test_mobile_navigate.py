"""移动端 navigate App URI 测试 — Iteration 47"""
import pytest
from unittest.mock import Mock, MagicMock, patch


def _make_engine_with_mobile_driver(mock_mobile_driver, platform="android"):
    """创建注入了移动端驱动的 KeywordEngine"""
    from core.keyword_engine import KeywordEngine
    engine = KeywordEngine.__new__(KeywordEngine)
    engine.driver = MagicMock()  # 主驱动（PlaywrightDriver）
    engine._desktop_drivers = {platform: mock_mobile_driver}
    engine._global_vars = {
        "Mobile": {
            "Platform": platform,
            "AppiumServer": "http://127.0.0.1:4723",
            "DeviceName": "test_device",
        }
    }
    engine._driver_factory = None
    engine.model_parser = None
    engine.data_manager = None
    engine._return_values = []
    engine.store_return = Mock()
    return engine


class TestNavigateAppUri:

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_navigate_android_app_uri(self, mock_remote):
        """navigate app://android/... 调用 AppiumDriver.start_app"""
        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=True)
        engine = _make_engine_with_mobile_driver(mock_mobile, "android")

        engine._kw_navigate({"data": "app://android/com.rodski.demo/com.rodski.demo.LoginActivity"})

        mock_mobile.start_app.assert_called_once_with(
            "com.rodski.demo", "com.rodski.demo.LoginActivity"
        )

    @patch('drivers.appium_driver.webdriver.Remote')
    def test_navigate_ios_app_uri(self, mock_remote):
        """navigate app://ios/... 调用 AppiumDriver.start_app"""
        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=True)
        engine = _make_engine_with_mobile_driver(mock_mobile, "ios")

        engine._kw_navigate({"data": "app://ios/com.rodski.demo"})

        mock_mobile.start_app.assert_called_once_with("com.rodski.demo")

    def test_navigate_http_url_uses_main_driver(self):
        """navigate https://... 仍走主驱动（PlaywrightDriver），不受影响"""
        mock_mobile = MagicMock()
        engine = _make_engine_with_mobile_driver(mock_mobile, "android")
        engine.driver.navigate = Mock(return_value=True)
        engine._ensure_driver = Mock()

        engine._kw_navigate({"data": "https://example.com"})

        engine.driver.navigate.assert_called_once_with("https://example.com")
        mock_mobile.start_app.assert_not_called()

    def test_navigate_android_uri_no_activity(self):
        """app://android/{package} 不含 activity 时，start_app 只传 package"""
        mock_mobile = MagicMock()
        mock_mobile.start_app = Mock(return_value=True)
        engine = _make_engine_with_mobile_driver(mock_mobile, "android")

        engine._kw_navigate({"data": "app://android/com.rodski.demo"})

        mock_mobile.start_app.assert_called_once_with("com.rodski.demo", None)
