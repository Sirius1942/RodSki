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

# 定位器类型到 AppiumBy 的映射
_LOCATOR_MAP = {
    "id":    AppiumBy.ID,
    "name":  AppiumBy.ACCESSIBILITY_ID,
    "class": AppiumBy.CLASS_NAME,
    "xpath": AppiumBy.XPATH,
    "text":  None,  # 特殊处理：构造 XPath
    "css":   AppiumBy.CSS_SELECTOR,  # 仅 WebView 上下文
}

# Android keycode 映射
_ANDROID_KEYCODES = {
    "BACK": 4, "HOME": 3, "ENTER": 66, "DELETE": 67,
    "MENU": 82, "SEARCH": 84, "VOLUME_UP": 24, "VOLUME_DOWN": 25,
    "TAB": 61, "ESCAPE": 111,
}


class AppiumDriver(BaseDriver):
    """Appium 驱动基类，支持 Android 和 iOS"""

    def __init__(self, capabilities: dict = None, server_url: str = "http://localhost:4723", options=None):
        logger.info(f"初始化 Appium 驱动: server={server_url}")
        if options is not None:
            self.driver = webdriver.Remote(server_url, options=options)
        else:
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
        """定位元素，按 locator_type 映射到正确的 AppiumBy"""
        try:
            by, value = self._resolve_locator(locator_type, locator_value)
            element = self.driver.find_element(by, value)
            rect = element.rect
            bbox = (rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height'])
            logger.debug(f"元素定位成功: {locator_type}={locator_value}, bbox={bbox}")
            return bbox
        except Exception as e:
            logger.warning(f"元素定位失败: {locator_type}={locator_value}, error={e}")
            return None

    def _resolve_locator(self, locator_type: str, locator_value: str) -> tuple:
        """将 locator_type/locator_value 解析为 (AppiumBy, value) 元组"""
        lt = locator_type.lower()
        if lt == "text":
            # Android: //*[@text='值']
            xpath = f"//*[@text='{locator_value}']"
            return AppiumBy.XPATH, xpath
        by = _LOCATOR_MAP.get(lt)
        if by is None:
            # 未知类型回退到 ID
            logger.debug(f"未知定位器类型 '{locator_type}'，回退到 AppiumBy.ID")
            return AppiumBy.ID, locator_value
        return by, locator_value

    def get_element_text_by_locator(self, locator_type: str, locator_value: str) -> str:
        """通过定位器找到元素，按优先级读取文本属性（移动端 verify 专用）"""
        from core.exceptions import ElementNotFoundError
        try:
            by, value = self._resolve_locator(locator_type, locator_value)
            element = self.driver.find_element(by, value)
        except Exception as e:
            raise ElementNotFoundError(
                f"元素未找到: {locator_type}={locator_value}",
                locator=locator_value
            ) from e

        # 按优先级读取文本属性（Android: text/content-desc，iOS: label/value/name）
        for attr in ["text", "value", "label", "name", "content-desc"]:
            val = element.text if attr == "text" else element.get_attribute(attr)
            if val:
                return val

        raise ElementNotFoundError(
            f"元素文本为空: {locator_type}={locator_value}",
            locator=locator_value
        )

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
        """输入文字（先 tap 获取焦点，再通过 active_element.send_keys 输入）"""
        logger.debug(f"输入文字: ({x}, {y}), text={text}")
        self.driver.tap([(x, y)])
        time.sleep(0.1)
        active = self.driver.switch_to.active_element
        if active is not None:
            active.clear()
            active.send_keys(text)
        else:
            # 回退：直接用 mobile: type 脚本
            self.driver.execute_script("mobile: type", {"text": text})

    def key_press(self, key: str) -> bool:
        """按下按键，支持 Android keycode 名称（大小写不敏感）"""
        keycode = _ANDROID_KEYCODES.get(key.upper())
        if keycode is not None:
            self.driver.press_keycode(keycode)
            return True
        logger.warning(f"未知按键: {key}，跳过")
        return False

    def start_app(self, package_or_bundle: str, activity: str = None) -> bool:
        """启动 App（Appium 2.x）

        Android: activate_app(package) + mobile: startActivity（如有 activity）
        iOS:     activate_app(bundle_id)
        """
        try:
            self.driver.activate_app(package_or_bundle)
            if activity:
                self.driver.execute_script("mobile: startActivity", {
                    "appPackage": package_or_bundle,
                    "appActivity": activity
                })
            return True
        except Exception as e:
            logger.error(f"启动 App 失败: {package_or_bundle}/{activity}, {e}")
            return False

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
        """滚动（Appium 2.x W3C Actions — mobile: scrollGesture）"""
        try:
            size = self.driver.get_window_size()
            w, h = size['width'], size['height']
            cx, cy = w // 2, h // 2

            if abs(y) >= abs(x):
                direction = "down" if y > 0 else "up"
                percent = min(abs(y) / h, 0.9)
            else:
                direction = "right" if x > 0 else "left"
                percent = min(abs(x) / w, 0.9)

            self.driver.execute_script("mobile: scrollGesture", {
                "left": cx - 100, "top": cy - 200,
                "width": 200, "height": 400,
                "direction": direction,
                "percent": max(percent, 0.1)
            })
            return True
        except Exception as e:
            logger.warning(f"scroll 失败: {e}")
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
        """拖拽（Appium 2.x W3C Actions — mobile: dragGesture）"""
        try:
            from_type, from_val = from_locator.split("=", 1)
            to_type, to_val = to_locator.split("=", 1)

            from_bbox = self.locate_element(from_type, from_val)
            to_bbox = self.locate_element(to_type, to_val)

            if not from_bbox or not to_bbox:
                return False

            fx = (from_bbox[0] + from_bbox[2]) // 2
            fy = (from_bbox[1] + from_bbox[3]) // 2
            tx = (to_bbox[0] + to_bbox[2]) // 2
            ty = (to_bbox[1] + to_bbox[3]) // 2

            self.driver.execute_script("mobile: dragGesture", {
                "startX": fx, "startY": fy,
                "endX": tx, "endY": ty
            })
            return True
        except Exception as e:
            logger.warning(f"drag 失败: {e}")
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
