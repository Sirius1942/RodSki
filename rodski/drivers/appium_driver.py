"""Appium 移动端自动化驱动基类"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_driver import BaseDriver
import time


class AppiumDriver(BaseDriver):
    """Appium 驱动基类，支持 Android 和 iOS"""
    
    def __init__(self, capabilities: dict, server_url: str = "http://localhost:4723"):
        self.driver = webdriver.Remote(server_url, capabilities)
        self.wait = WebDriverWait(self.driver, 10)
    
    def click(self, locator: str, **kwargs) -> bool:
        try:
            by, value = self._parse_locator(locator)
            element = self.wait.until(EC.element_to_be_clickable((by, value)))
            element.click()
            return True
        except Exception as e:
            print(f"Click failed: {e}")
            return False
    
    def type(self, locator: str, text: str, **kwargs) -> bool:
        try:
            by, value = self._parse_locator(locator)
            element = self.wait.until(EC.presence_of_element_located((by, value)))
            element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            print(f"Type failed: {e}")
            return False
    
    def check(self, locator: str, **kwargs) -> bool:
        try:
            by, value = self._parse_locator(locator)
            element = self.wait.until(EC.presence_of_element_located((by, value)))
            return element.is_displayed()
        except:
            return False
    
    def wait(self, seconds: float) -> None:
        time.sleep(seconds)
    
    def navigate(self, url: str) -> bool:
        try:
            self.driver.get(url)
            return True
        except:
            return False
    
    def screenshot(self, path: str) -> bool:
        try:
            self.driver.save_screenshot(path)
            return True
        except:
            return False
    
    def select(self, locator: str, value: str) -> bool:
        return self.click(locator)
    
    def hover(self, locator: str) -> bool:
        return self.click(locator)
    
    def drag(self, from_loc: str, to_loc: str) -> bool:
        try:
            by1, val1 = self._parse_locator(from_loc)
            by2, val2 = self._parse_locator(to_loc)
            el1 = self.driver.find_element(by1, val1)
            el2 = self.driver.find_element(by2, val2)
            self.driver.drag_and_drop(el1, el2)
            return True
        except:
            return False
    
    def scroll(self, x: int = 0, y: int = 300) -> bool:
        try:
            size = self.driver.get_window_size()
            start_x = size['width'] // 2
            start_y = size['height'] * 0.8
            end_y = size['height'] * 0.2
            self.driver.swipe(start_x, start_y, start_x, end_y, 500)
            return True
        except:
            return False
    
    def assert_element(self, locator: str, expected: str) -> bool:
        try:
            by, value = self._parse_locator(locator)
            element = self.driver.find_element(by, value)
            return expected in element.text
        except:
            return False
    
    def close(self) -> None:
        if self.driver:
            self.driver.quit()
    
    # 移动端特有方法
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500) -> bool:
        try:
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            return True
        except:
            return False
    
    def tap(self, x: int, y: int) -> bool:
        try:
            self.driver.tap([(x, y)])
            return True
        except:
            return False
    
    def long_press(self, locator: str, duration: int = 1000) -> bool:
        try:
            by, value = self._parse_locator(locator)
            element = self.driver.find_element(by, value)
            self.driver.execute_script("mobile: longClickGesture", {"elementId": element.id, "duration": duration})
            return True
        except:
            return False
    
    def hide_keyboard(self) -> bool:
        try:
            self.driver.hide_keyboard()
            return True
        except:
            return False
    
    def _parse_locator(self, locator: str) -> tuple:
        """解析定位符，格式: id=xxx, xpath=xxx, accessibility_id=xxx"""
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
    
    def get_supported_keywords(self) -> list:
        return ["swipe", "tap", "long_press", "hide_keyboard"]
