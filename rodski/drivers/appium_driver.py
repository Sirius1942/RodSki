"""Appium 移动端自动化驱动基类"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional, Tuple
from .base_driver import BaseDriver
import time


class AppiumDriver(BaseDriver):
    """Appium 驱动基类，支持 Android 和 iOS"""

    def __init__(self, capabilities: dict, server_url: str = "http://localhost:4723"):
        self.driver = webdriver.Remote(server_url, capabilities)
        self.wait = WebDriverWait(self.driver, 10)

    def launch(self, **kwargs) -> None:
        """启动应用"""
        pass

    def close(self) -> None:
        if self.driver:
            self.driver.quit()

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素"""
        try:
            by, value = self._parse_locator(f"{locator_type}={locator_value}")
            element = self.driver.find_element(by, value)
            rect = element.rect
            return (rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height'])
        except:
            return None

    def click(self, x: int, y: int) -> None:
        """点击坐标"""
        self.driver.tap([(x, y)])

    def type_text(self, x: int, y: int, text: str) -> None:
        """输入文字"""
        self.driver.tap([(x, y)])
        time.sleep(0.1)
        self.driver.execute_script("mobile: type", {"text": text})

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取文字"""
        return ""

    def take_screenshot(self) -> str:
        """截图"""
        import tempfile
        path = tempfile.mktemp(suffix='.png')
        self.driver.save_screenshot(path)
        return path

    def double_click(self, x: int, y: int) -> None:
        """双击"""
        self.driver.tap([(x, y)], 2)

    def right_click(self, x: int, y: int) -> None:
        """右键点击（移动端不支持）"""
        pass

    def hover(self, x: int, y: int) -> None:
        """悬停（移动端不支持）"""
        pass

    def scroll(self, x: int, y: int) -> None:
        """滚动"""
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = size['height'] // 2
        self.driver.swipe(start_x, start_y, start_x + x, start_y + y, 500)

    def _parse_locator(self, locator: str) -> tuple:
        """解析定位符"""
        if "=" not in locator:
            return AppiumBy.ID, locator

        strategy, value = locator.split("=", 1)
        mapping = {
            "id": AppiumBy.ID,
            "xpath": AppiumBy.XPATH,
            "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
            "class": AppiumBy.CLASS_NAME,
            "name": AppiumBy.NAME
        }
        return mapping.get(strategy.lower(), AppiumBy.ID), value
