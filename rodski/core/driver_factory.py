"""驱动工厂 - 统一管理驱动实例的创建和缓存

支持的驱动类型:
- web: Web 自动化驱动 (Playwright)
- interface: 接口自动化驱动 (requests)
- windows: Windows 桌面自动化驱动 (Pywinauto)
- macos: macOS 桌面自动化驱动 (PyXA/Appium)

特性:
- 单例缓存: 同一类型的驱动只创建一次
- 懒加载: 按需创建驱动
- 资源管理: 统一释放驱动资源
"""
from __future__ import annotations

import logging
import platform
from typing import Dict, Optional, Any, Type, Callable

from drivers.base_driver import BaseDriver

logger = logging.getLogger("rodski")


class DriverFactory:
    """驱动工厂 - 管理驱动实例的创建和缓存

    使用方式:
        # 获取驱动
        driver = DriverFactory.get_driver("web", headless=True)

        # 释放单个驱动
        DriverFactory.release_driver("web")

        # 释放所有驱动
        DriverFactory.release_all()
    """

    # 驱动缓存: {driver_type: driver_instance}
    _drivers: Dict[str, BaseDriver] = {}

    # 驱动配置缓存: {driver_type: kwargs}
    _driver_configs: Dict[str, Dict[str, Any]] = {}

    # 支持的驱动类型
    SUPPORTED_DRIVER_TYPES = ["web", "interface", "windows", "macos"]

    @classmethod
    def get_driver(cls, driver_type: str, **kwargs) -> BaseDriver:
        """获取驱动实例

        如果缓存中已存在该类型的驱动，直接返回缓存的实例。
        否则创建新驱动并缓存。

        Args:
            driver_type: 驱动类型，支持:
                - "web": Web 自动化 (Playwright)
                - "interface": 接口自动化 (requests)
                - "windows": Windows 桌面自动化 (Pywinauto)
                - "macos": macOS 桌面自动化 (PyXA)
            **kwargs: 传递给驱动构造函数的参数

        Returns:
            对应的驱动实例

        Raises:
            ValueError: 不支持的驱动类型
            ImportError: 缺少必要的依赖库
            RuntimeError: 驱动创建失败
        """
        driver_type = driver_type.lower()

        if driver_type not in cls.SUPPORTED_DRIVER_TYPES:
            raise ValueError(
                f"不支持的驱动类型: {driver_type}。"
                f"支持的类型: {cls.SUPPORTED_DRIVER_TYPES}"
            )

        # 检查缓存
        if driver_type in cls._drivers:
            cached_config = cls._driver_configs.get(driver_type, {})
            if cached_config != kwargs:
                logger.warning(
                    f"驱动 '{driver_type}' 配置冲突: "
                    f"缓存配置={cached_config}, 请求配置={kwargs}。"
                    f"返回缓存实例（配置={cached_config}）"
                )
            logger.debug(f"从缓存获取驱动: {driver_type}")
            return cls._drivers[driver_type]

        # 创建新驱动
        logger.info(f"创建新驱动: {driver_type}")
        driver = cls._create_driver(driver_type, **kwargs)

        # 缓存驱动和配置
        cls._drivers[driver_type] = driver
        cls._driver_configs[driver_type] = kwargs

        return driver

    @classmethod
    def _create_driver(cls, driver_type: str, **kwargs) -> BaseDriver:
        """创建驱动实例

        Args:
            driver_type: 驱动类型
            **kwargs: 驱动参数

        Returns:
            驱动实例
        """
        if driver_type == "web":
            return cls._create_web_driver(**kwargs)
        elif driver_type == "interface":
            return cls._create_interface_driver(**kwargs)
        elif driver_type == "windows":
            return cls._create_desktop_driver("windows", **kwargs)
        elif driver_type == "macos":
            return cls._create_desktop_driver("macos", **kwargs)
        else:
            raise ValueError(f"不支持的驱动类型: {driver_type}")

    @classmethod
    def _create_web_driver(cls, **kwargs) -> BaseDriver:
        """创建 Web 驱动 (Playwright)

        Args:
            headless: 是否无头模式，默认 False
            browser: 浏览器类型，默认 "chromium"

        Returns:
            PlaywrightDriver 实例
        """
        try:
            from drivers.playwright_driver import PlaywrightDriver
            headless = kwargs.get("headless", False)
            browser = kwargs.get("browser", "chromium")
            return PlaywrightDriver(headless=headless, browser=browser)
        except ImportError as e:
            raise ImportError(
                "无法导入 PlaywrightDriver，请确保已安装 playwright: "
                "pip install playwright && playwright install"
            ) from e

    @classmethod
    def _create_interface_driver(cls, **kwargs) -> BaseDriver:
        """创建接口驱动 (requests)

        Args:
            base_url: 基础 URL (可选)
            headers: 默认请求头 (可选)
            timeout: 请求超时时间 (可选)

        Returns:
            InterfaceDriver 实例
        """
        try:
            from drivers.interface_driver import InterfaceDriver
            return InterfaceDriver(**kwargs)
        except ImportError:
            # InterfaceDriver 尚未实现，返回一个占位实现
            logger.warning(
                "InterfaceDriver 尚未实现，使用 MockInterfaceDriver。"
                "请创建 drivers/interface_driver.py 实现 BaseDriver 接口。"
            )
            return MockInterfaceDriver(**kwargs)

    @classmethod
    def _create_desktop_driver(cls, platform_type: str, **kwargs) -> BaseDriver:
        """创建桌面驱动

        Args:
            platform_type: 平台类型 ("windows" 或 "macos")
            app_path: 应用路径 (可选)

        Returns:
            桌面驱动实例
        """
        current_platform = platform.system().lower()

        # 验证平台兼容性
        if platform_type == "windows" and current_platform != "windows":
            raise RuntimeError(
                f"Windows 驱动只能在 Windows 系统上运行，当前系统: {current_platform}"
            )
        if platform_type == "macos" and current_platform != "darwin":
            raise RuntimeError(
                f"macOS 驱动只能在 macOS 系统上运行，当前系统: {current_platform}"
            )

        if platform_type == "windows":
            return cls._create_windows_driver(**kwargs)
        else:
            return cls._create_macos_driver(**kwargs)

    @classmethod
    def _create_windows_driver(cls, **kwargs) -> BaseDriver:
        """创建 Windows 桌面驱动 (Pywinauto)

        Args:
            app_path: 应用路径 (可选)

        Returns:
            PywinautoDriver 实例
        """
        try:
            from drivers.pywinauto_driver import PywinautoDriver
            app_path = kwargs.get("app_path")
            return PywinautoDriver(app_path=app_path)
        except ImportError as e:
            raise ImportError(
                "无法导入 PywinautoDriver，请确保已安装 pywinauto: "
                "pip install pywinauto"
            ) from e

    @classmethod
    def _create_macos_driver(cls, **kwargs) -> BaseDriver:
        """创建 macOS 桌面驱动

        目前支持两种方案:
        1. PyXA (原生 Apple 事件)
        2. AppiumForMac

        Args:
            backend: 驱动后端，默认 "pyxa"
            app_path: 应用路径 (可选)

        Returns:
            macOS 桌面驱动实例
        """
        backend = kwargs.get("backend", "pyxa")

        if backend == "appium":
            try:
                from drivers.appium_driver import AppiumDriver
                return AppiumDriver(**kwargs)
            except ImportError:
                logger.warning("AppiumDriver 导入失败，尝试使用 PyXA")

        # 使用 PyXA 或返回 Mock
        try:
            from drivers.pyxa_driver import PyXADriver
            return PyXADriver(**kwargs)
        except ImportError:
            logger.warning(
                "PyXADriver 尚未实现，使用 MockMacOSDriver。"
                "请创建 drivers/pyxa_driver.py 实现 BaseDriver 接口。"
            )
            return MockMacOSDriver(**kwargs)

    @classmethod
    def release_driver(cls, driver_type: str) -> None:
        """释放指定类型的驱动

        关闭驱动并从缓存中移除。

        Args:
            driver_type: 驱动类型
        """
        driver_type = driver_type.lower()

        if driver_type in cls._drivers:
            driver = cls._drivers[driver_type]
            try:
                driver.close()
                logger.info(f"驱动已关闭: {driver_type}")
            except Exception as e:
                logger.warning(f"关闭驱动 {driver_type} 时出错: {e}")

            del cls._drivers[driver_type]
            if driver_type in cls._driver_configs:
                del cls._driver_configs[driver_type]

    @classmethod
    def release_all(cls) -> None:
        """释放所有缓存的驱动"""
        driver_types = list(cls._drivers.keys())
        for driver_type in driver_types:
            cls.release_driver(driver_type)
        logger.info("所有驱动已释放")

    @classmethod
    def has_driver(cls, driver_type: str) -> bool:
        """检查指定类型的驱动是否已缓存

        Args:
            driver_type: 驱动类型

        Returns:
            是否已缓存
        """
        return driver_type.lower() in cls._drivers

    @classmethod
    def get_cached_types(cls) -> list:
        """获取已缓存的驱动类型列表

        Returns:
            已缓存的驱动类型列表
        """
        return list(cls._drivers.keys())

    @classmethod
    def get_driver_config(cls, driver_type: str) -> Optional[Dict[str, Any]]:
        """获取指定类型驱动的创建配置

        Args:
            driver_type: 驱动类型

        Returns:
            配置字典，不存在返回 None
        """
        return cls._driver_configs.get(driver_type.lower())

    @classmethod
    def create_factory_function(
        cls,
        driver_type: str,
        **kwargs
    ) -> Callable[[], BaseDriver]:
        """创建驱动工厂函数

        用于传递给 SKIExecutor 的 driver_factory 参数。

        Args:
            driver_type: 驱动类型
            **kwargs: 驱动参数

        Returns:
            无参数的工厂函数
        """
        def factory() -> BaseDriver:
            # 先释放旧的驱动（如果存在）
            if cls.has_driver(driver_type):
                cls.release_driver(driver_type)
            return cls.get_driver(driver_type, **kwargs)

        return factory


class MockInterfaceDriver(BaseDriver):
    """Mock 接口驱动 - 用于开发测试

    在 InterfaceDriver 实现之前作为占位符使用。
    """

    def __init__(self, base_url: str = "", **kwargs):
        self.base_url = base_url
        self.headers = kwargs.get("headers", {})
        self.timeout = kwargs.get("timeout", 30)
        self._session = None
        self._is_closed = False
        self._responses: Dict[str, Any] = {}

    def launch(self, **kwargs) -> None:
        """初始化 session"""
        import requests
        self._session = requests.Session()
        if self.base_url:
            self._session.base_url = self.base_url
        self._is_closed = False

    def close(self) -> None:
        """关闭 session"""
        if self._session:
            self._session.close()
        self._is_closed = True

    def locate_element(
        self,
        locator_type: str,
        locator_value: str
    ) -> Optional[tuple]:
        """接口驱动不支持元素定位"""
        logger.warning("InterfaceDriver 不支持 locate_element")
        return None

    def click(self, x: int, y: int) -> None:
        """接口驱动不支持点击"""
        logger.warning("InterfaceDriver 不支持 click")

    def type_text(self, x: int, y: int, text: str) -> None:
        """接口驱动不支持输入"""
        logger.warning("InterfaceDriver 不支持 type_text")

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取响应文本"""
        return ""

    def take_screenshot(self) -> str:
        """接口驱动不支持截图"""
        logger.warning("InterfaceDriver 不支持截图")
        return ""


class MockMacOSDriver(BaseDriver):
    """Mock macOS 驱动 - 用于开发测试

    在 PyXADriver 实现之前作为占位符使用。
    """

    def __init__(self, **kwargs):
        self.app_path = kwargs.get("app_path")
        self._is_closed = False

    def launch(self, **kwargs) -> None:
        """启动应用"""
        app_path = kwargs.get("app_path", self.app_path)
        if app_path:
            logger.info(f"MockMacOSDriver: 启动应用 {app_path}")

    def close(self) -> None:
        """关闭应用"""
        self._is_closed = True

    def locate_element(
        self,
        locator_type: str,
        locator_value: str
    ) -> Optional[tuple]:
        """定位元素"""
        logger.warning("MockMacOSDriver.locate_element 尚未实现")
        return None

    def click(self, x: int, y: int) -> None:
        """点击坐标"""
        logger.warning("MockMacOSDriver.click 尚未实现")

    def type_text(self, x: int, y: int, text: str) -> None:
        """输入文字"""
        logger.warning("MockMacOSDriver.type_text 尚未实现")

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取文字"""
        return ""

    def take_screenshot(self) -> str:
        """截图"""
        logger.warning("MockMacOSDriver.take_screenshot 尚未实现")
        return ""