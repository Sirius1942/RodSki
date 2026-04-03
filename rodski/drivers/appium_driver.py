"""Appium 移动端自动化驱动基类"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional, Tuple
from .base_driver import BaseDriver
import time
import logging

logger = logging.getLogger("rodski")


class AppiumDriver(BaseDriver):
    """Appium 驱动基类，支持 Android 和 iOS"""

    def __init__(self, capabilities: dict, server_url: str = "http://localhost:4723"):
        logger.info(f"初始化 Appium 驱动: server={server_url}")
        self.driver = webdriver.Remote(server_url, capabilities)
        self.wait = WebDriverWait(self.driver, 10)
        logger.info("Appium 驱动初始化成功")

    def launch(self, **kwargs) -> None:
        """启动应用"""
        pass

    def close(self) -> None:
        if self.driver:
            logger.info("关闭 Appium 驱动")
            self.driver.quit()

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素"""
        try:
            by, value = self._parse_locator(f"{locator_type}={locator_value}")
            element = self.driver.find_element(by, value)
            rect = element.rect
            bbox = (rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height'])
            logger.debug(f"元素定位成功: {locator_type}={locator_value}, bbox={bbox}")
            return bbox
        except Exception as e:
            logger.warning(f"元素定位失败: {locator_type}={locator_value}, error={e}")
            return None

    # ── BaseDriver 坐标接口（两阶段 API）───────────────────────────

    def click(self, locator_or_x, y=None) -> bool:
        """点击元素

        支持两种调用方式：
        - click(locator_str)     → 旧 API，定位器点击
        - click(x, y)            → BaseDriver 坐标 API
        """
        if y is None and isinstance(locator_or_x, str):
            # 旧 API: click("id=test") → 定位器点击
            try:
                by, value = self._parse_locator(locator_or_x)
                element = self.wait.until(EC.presence_of_element_located((by, value)))
                element.click()
                logger.debug(f"点击成功: {locator_or_x}")
                return True
            except Exception as e:
                logger.error(f"点击失败: {locator_or_x}, error={e}")
                return False
        else:
            # BaseDriver API: click(x, y) → 坐标点击
            x = locator_or_x
            logger.debug(f"点击坐标: ({x}, {y})")
            self.driver.tap([(x, y)])

    def type_text(self, x: int, y: int, text: str) -> None:
        """输入文字"""
        logger.debug(f"输入文字: ({x}, {y}), text={text}")
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

    def hover(self, locator_or_x, y=None) -> bool:
        """悬停

        支持两种调用方式：
        - hover(locator_str)  → 旧 API，定位器悬停
        - hover(x, y)         → BaseDriver 坐标 API（移动端不支持，直接 pass）
        """
        if y is None and isinstance(locator_or_x, str):
            try:
                by, value = self._parse_locator(locator_or_x)
                element = self.wait.until(EC.presence_of_element_located((by, value)))
                self.driver.execute_script("mobile: longClick", {"element": element.id})
                return True
            except Exception:
                return False
        # 移动端悬停不支持，直接 pass

    def scroll(self, x: int, y: int) -> bool:
        """滚动（BaseDriver API）"""
        try:
            size = self.driver.get_window_size()
            start_x = size['width'] // 2
            start_y = size['height'] // 2
            self.driver.swipe(start_x, start_y, start_x + x, start_y + y, 500)
            return True
        except Exception:
            return False

    # ── 旧 API（定位器接口，保留用于兼容性和测试）───────────────────

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

    def hover_locator(self, locator: str) -> bool:
        """通过定位器悬停（旧 API）"""
        try:
            by, value = self._parse_locator(locator)
            element = self.wait.until(EC.presence_of_element_located((by, value)))
            # 移动端用 longPress 模拟悬停
            self.driver.execute_script("mobile: longClick", {"element": element.id})
            return True
        except Exception:
            return False

    def drag(self, from_locator: str, to_locator: str) -> bool:
        """拖拽操作（旧 API）"""
        try:
            by1, val1 = self._parse_locator(from_locator)
            by2, val2 = self._parse_locator(to_locator)
            el1 = self.driver.find_element(by1, val1)
            el2 = self.driver.find_element(by2, val2)
            self.driver.drag_and_drop(el1, el2)
            return True
        except Exception:
            return False

    def assert_element(self, locator: str, expected: str) -> bool:
        """断言元素文本（旧 API）"""
        try:
            by, value = self._parse_locator(locator)
            element = self.driver.find_element(by, value)
            return expected in (element.text or "")
        except Exception:
            return False

    def click_element(self, locator: str) -> bool:
        """通过定位器点击元素（旧 API）"""
        try:
            by, value = self._parse_locator(locator)
            element = self.wait.until(EC.presence_of_element_located((by, value)))
            element.click()
            return True
        except Exception:
            return False

    def type(self, locator: str, text: str) -> bool:
        """通过定位器输入文字（旧 API）"""
        try:
            by, value = self._parse_locator(locator)
            element = self.wait.until(EC.presence_of_element_located((by, value)))
            element.clear()
            element.send_keys(text)
            return True
        except Exception:
            return False

    def check(self, locator: str) -> bool:
        """检查元素是否可见（旧 API）"""
        try:
            by, value = self._parse_locator(locator)
            element = self.wait.until(EC.visibility_of_element_located((by, value)))
            return element.is_displayed()
        except Exception:
            return False

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500) -> bool:
        """滑动操作（旧 API）"""
        try:
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            return True
        except Exception:
            return False

    def tap(self, x: int, y: int) -> bool:
        """点击坐标（旧 API）"""
        try:
            self.driver.tap([(x, y)])
            return True
        except Exception:
            return False

    def screenshot(self, path: str = None) -> bool:
        """截图（旧 API）"""
        try:
            if path is None:
                self.take_screenshot()
            else:
                self.driver.save_screenshot(path)
            return True
        except Exception:
            return False

    def navigate(self, url: str) -> bool:
        """导航到 URL（旧 API）"""
        try:
            self.driver.get(url)
            return True
        except Exception:
            return False

    def select(self, locator: str, value: str) -> bool:
        """下拉选择（旧 API）"""
        try:
            from selenium.webdriver.support.ui import Select
            by, val = self._parse_locator(locator)
            element = self.wait.until(EC.presence_of_element_located((by, val)))
            Select(element).select_by_value(value)
            return True
        except Exception:
            return False

    def long_press(self, locator: str) -> bool:
        """长按元素（旧 API）"""
        try:
            by, value = self._parse_locator(locator)
            element = self.wait.until(EC.presence_of_element_located((by, value)))
            self.driver.execute_script("mobile: longClick", {"element": element.id})
            return True
        except Exception:
            return False

    def hide_keyboard(self) -> bool:
        """隐藏键盘（旧 API）"""
        try:
            self.driver.hide_keyboard()
            return True
        except Exception:
            return False

    def get_supported_keywords(self) -> list:
        """返回支持的关键字列表（旧 API）"""
        return ["click", "type", "check", "swipe", "tap", "screenshot",
                "navigate", "select", "long_press", "hide_keyboard",
                "launch", "close", "locate_element"]
