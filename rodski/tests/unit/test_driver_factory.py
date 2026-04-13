"""DriverFactory 单元测试

测试 core/driver_factory.py 中的驱动工厂。
覆盖：create_driver（web/android/ios/interface/macos 类型）、
      MockInterfaceDriver / MockMacOSDriver、
      driver_factory 闭包、未知类型错误处理。
"""
import pytest
from unittest.mock import MagicMock, patch
from core.driver_factory import DriverFactory, MockInterfaceDriver, MockMacOSDriver


class TestDriverFactory:
    """测试 DriverFactory 类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清空驱动缓存"""
        DriverFactory.release_all()
        yield
        DriverFactory.release_all()

    def test_supported_driver_types(self):
        """验证支持的驱动类型"""
        assert "web" in DriverFactory.SUPPORTED_DRIVER_TYPES
        assert "interface" in DriverFactory.SUPPORTED_DRIVER_TYPES
        assert "windows" in DriverFactory.SUPPORTED_DRIVER_TYPES
        assert "macos" in DriverFactory.SUPPORTED_DRIVER_TYPES

    def test_unsupported_driver_type(self):
        """测试不支持的驱动类型"""
        with pytest.raises(ValueError, match="不支持的驱动类型"):
            DriverFactory.get_driver("unsupported_type")

    def test_driver_caching(self):
        """测试驱动缓存机制"""
        # 使用 Mock 驱动避免真正创建浏览器
        mock_driver = MagicMock()

        with patch.object(
            DriverFactory, '_create_driver', return_value=mock_driver
        ) as mock_create:
            # 第一次获取
            driver1 = DriverFactory.get_driver("interface")
            # 第二次获取
            driver2 = DriverFactory.get_driver("interface")

            # 只创建一次
            assert mock_create.call_count == 1
            # 返回同一实例
            assert driver1 is driver2

    def test_has_driver(self):
        """测试驱动存在检查"""
        assert not DriverFactory.has_driver("interface")

        with patch.object(
            DriverFactory, '_create_driver', return_value=MagicMock()
        ):
            DriverFactory.get_driver("interface")
            assert DriverFactory.has_driver("interface")

    def test_release_driver(self):
        """测试释放单个驱动"""
        mock_driver = MagicMock()

        with patch.object(
            DriverFactory, '_create_driver', return_value=mock_driver
        ):
            DriverFactory.get_driver("interface")
            assert DriverFactory.has_driver("interface")

            DriverFactory.release_driver("interface")
            assert not DriverFactory.has_driver("interface")
            mock_driver.close.assert_called_once()

    def test_release_all(self):
        """测试释放所有驱动"""
        mock_driver1 = MagicMock()
        mock_driver2 = MagicMock()

        with patch.object(
            DriverFactory, '_create_driver', side_effect=[mock_driver1, mock_driver2]
        ):
            DriverFactory.get_driver("interface")
            DriverFactory.get_driver("web")

            assert len(DriverFactory.get_cached_types()) == 2

            DriverFactory.release_all()

            assert len(DriverFactory.get_cached_types()) == 0
            mock_driver1.close.assert_called_once()
            mock_driver2.close.assert_called_once()

    def test_get_cached_types(self):
        """测试获取已缓存的驱动类型"""
        assert DriverFactory.get_cached_types() == []

        with patch.object(
            DriverFactory, '_create_driver', return_value=MagicMock()
        ):
            DriverFactory.get_driver("interface")
            cached = DriverFactory.get_cached_types()
            assert "interface" in cached

    def test_create_factory_function(self):
        """测试创建工厂函数"""
        mock_driver = MagicMock()

        with patch.object(
            DriverFactory, '_create_driver', return_value=mock_driver
        ):
            factory = DriverFactory.create_factory_function("interface")

            driver1 = factory()
            assert driver1 is mock_driver

            # 缓存中应该存在
            assert DriverFactory.has_driver("interface")

    def test_get_driver_config(self):
        """测试获取驱动配置"""
        with patch.object(
            DriverFactory, '_create_driver', return_value=MagicMock()
        ):
            DriverFactory.get_driver("interface", base_url="http://example.com")

            config = DriverFactory.get_driver_config("interface")
            assert config == {"base_url": "http://example.com"}

    def test_case_insensitive_driver_type(self):
        """测试驱动类型大小写不敏感"""
        mock_driver = MagicMock()

        with patch.object(
            DriverFactory, '_create_driver', return_value=mock_driver
        ):
            driver1 = DriverFactory.get_driver("INTERFACE")
            driver2 = DriverFactory.get_driver("Interface")

            assert driver1 is driver2


class TestMockInterfaceDriver:
    """测试 MockInterfaceDriver"""

    def test_init(self):
        """测试初始化"""
        driver = MockInterfaceDriver(base_url="http://example.com")
        assert driver.base_url == "http://example.com"

    def test_launch(self):
        """测试启动"""
        driver = MockInterfaceDriver()
        driver.launch()
        assert not driver._is_closed

    def test_close(self):
        """测试关闭"""
        driver = MockInterfaceDriver()
        driver.launch()
        driver.close()
        assert driver._is_closed

    def test_locate_element_returns_none(self):
        """测试 locate_element 返回 None"""
        driver = MockInterfaceDriver()
        result = driver.locate_element("id", "test")
        assert result is None

    def test_get_text_returns_empty(self):
        """测试 get_text 返回空字符串"""
        driver = MockInterfaceDriver()
        result = driver.get_text(0, 0, 100, 100)
        assert result == ""


class TestMockMacOSDriver:
    """测试 MockMacOSDriver"""

    def test_init(self):
        """测试初始化"""
        driver = MockMacOSDriver(app_path="/Applications/Test.app")
        assert driver.app_path == "/Applications/Test.app"

    def test_launch(self):
        """测试启动"""
        driver = MockMacOSDriver()
        driver.launch(app_path="/Applications/Test.app")
        assert not driver._is_closed

    def test_close(self):
        """测试关闭"""
        driver = MockMacOSDriver()
        driver.launch()
        driver.close()
        assert driver._is_closed

    def test_locate_element_returns_none(self):
        """测试 locate_element 返回 None"""
        driver = MockMacOSDriver()
        result = driver.locate_element("id", "test")
        assert result is None

    def test_get_text_returns_empty(self):
        """测试 get_text 返回空字符串"""
        driver = MockMacOSDriver()
        result = driver.get_text(0, 0, 100, 100)
        assert result == ""


class TestDriverFactoryWeb:
    """测试 Web 驱动创建"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清空驱动缓存"""
        DriverFactory.release_all()
        yield
        DriverFactory.release_all()

    def test_create_web_driver_mock(self):
        """测试创建 Web 驱动 (Mock)"""
        mock_playwright_driver = MagicMock()

        with patch.dict(
            'sys.modules',
            {'drivers.playwright_driver': MagicMock(PlaywrightDriver=mock_playwright_driver)}
        ):
            with patch.object(
                DriverFactory, '_create_web_driver', return_value=mock_playwright_driver
            ):
                driver = DriverFactory.get_driver("web", headless=True)
                assert driver is mock_playwright_driver


class TestDriverFactoryDesktop:
    """测试桌面驱动创建"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清空驱动缓存"""
        DriverFactory.release_all()
        yield
        DriverFactory.release_all()

    def test_windows_driver_on_non_windows(self):
        """测试在非 Windows 系统上创建 Windows 驱动"""
        with patch('platform.system', return_value='Darwin'):
            with pytest.raises(RuntimeError, match="Windows 驱动只能在 Windows 系统上运行"):
                DriverFactory.get_driver("windows")

    def test_macos_driver_on_non_macos(self):
        """测试在非 macOS 系统上创建 macOS 驱动"""
        with patch('platform.system', return_value='Windows'):
            with pytest.raises(RuntimeError, match="macOS 驱动只能在 macOS 系统上运行"):
                DriverFactory.get_driver("macos")

    def test_macos_driver_returns_mock(self):
        """测试 macOS 驱动返回 Mock 实现"""
        with patch('platform.system', return_value='Darwin'):
            # 由于 PyXADriver 尚未实现，应返回 MockMacOSDriver
            driver = DriverFactory.get_driver("macos")
            assert isinstance(driver, MockMacOSDriver)


class TestDriverFactoryInterface:
    """测试接口驱动创建"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清空驱动缓存"""
        DriverFactory.release_all()
        yield
        DriverFactory.release_all()

    def test_interface_driver_returns_mock(self):
        """测试接口驱动返回 Mock 实现"""
        # 由于 InterfaceDriver 尚未实现，应返回 MockInterfaceDriver
        driver = DriverFactory.get_driver("interface")
        assert isinstance(driver, MockInterfaceDriver)

    def test_interface_driver_with_config(self):
        """测试带配置的接口驱动"""
        driver = DriverFactory.get_driver(
            "interface",
            base_url="http://api.example.com",
            timeout=60
        )
        assert isinstance(driver, MockInterfaceDriver)
        assert driver.base_url == "http://api.example.com"
        assert driver.timeout == 60