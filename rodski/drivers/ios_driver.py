"""iOS 专用驱动 — Appium 2.x W3C capabilities"""
import logging

# appium-python-client 5.x 将 XCUITestOptions 移到了子模块；
# 同时保留对旧版 appium-python-client（<5）的 fallback。
try:
    from appium.options.ios.xcuitest.base import XCUITestOptions  # appium-python-client >= 5.x
    _HAS_APPIUM_OPTIONS = True
except ImportError:
    try:
        from appium.options import XCUITestOptions  # appium-python-client < 5.x
        _HAS_APPIUM_OPTIONS = True
    except ImportError:
        _HAS_APPIUM_OPTIONS = False

try:
    from appium.webdriver.common.appiumby import AppiumBy
    _HAS_APPIUM_BY = True
except ImportError:
    AppiumBy = None
    _HAS_APPIUM_BY = False

from .appium_driver import AppiumDriver

logger = logging.getLogger("rodski")

# iOS 支持的硬件按键（mobile: pressButton）
_IOS_BUTTONS = {"HOME", "VOLUMEUP", "VOLUMEDOWN"}


class IOSDriver(AppiumDriver):
    """iOS 设备驱动（Appium 2.x）"""

    def __init__(self, device_name: str = "iPhone", bundle_id: str = None,
                 server_url: str = "http://localhost:4723", **kwargs):
        if _HAS_APPIUM_OPTIONS:
            options = XCUITestOptions()
            options.platform_name = "iOS"
            options.device_name = device_name
            options.automation_name = "XCUITest"
            if bundle_id:
                options.bundle_id = bundle_id
            if kwargs.get("udid"):
                options.udid = kwargs["udid"]
            super().__init__(options=options, server_url=server_url)
        else:
            # 回退：旧格式（Appium 1.x 兼容）
            capabilities = {
                "platformName": "iOS",
                "deviceName": device_name,
                "automationName": "XCUITest"
            }
            if bundle_id:
                capabilities["bundleId"] = bundle_id
            super().__init__(capabilities, server_url)

    def shake(self) -> bool:
        try:
            self.driver.shake()
            return True
        except Exception:
            return False

    # ── 定位器钩子（重写 AppiumDriver）─────────────────────────────

    def _text_xpath(self, value):
        """text 定位器转 XPath（iOS: 匹配 label/name/value）"""
        return f"//*[@label='{value}' or @name='{value}' or @value='{value}']"

    def _get_locator_map(self):
        """iOS 专属定位器类型映射"""
        return {
            "id":          AppiumBy.ACCESSIBILITY_ID,
            "name":        AppiumBy.NAME,
            "class":       AppiumBy.CLASS_NAME,
            "xpath":       AppiumBy.XPATH,
            "predicate":   AppiumBy.IOS_PREDICATE,
            "class_chain": AppiumBy.IOS_CLASS_CHAIN,
        }

    # ── iOS 手势 / 按键（mobile: 系列命令）─────────────────────────

    def scroll(self, direction: str = "down") -> bool:
        """滚动（iOS: mobile: scroll，direction = up/down/left/right）"""
        try:
            self.driver.execute_script("mobile: scroll", {"direction": direction})
            return True
        except Exception as e:
            logger.warning(f"iOS scroll 失败: direction={direction}, error={e}")
            return False

    def swipe(self, direction: str = "up") -> bool:
        """滑动（iOS: mobile: swipe，direction = up/down/left/right）"""
        try:
            self.driver.execute_script("mobile: swipe", {"direction": direction})
            return True
        except Exception as e:
            logger.warning(f"iOS swipe 失败: direction={direction}, error={e}")
            return False

    def key_press(self, key: str) -> bool:
        """按下硬件按键（iOS: mobile: pressButton，支持 home/volumeup/volumedown）"""
        name = key.upper().replace("_", "")
        if name in _IOS_BUTTONS:
            self.driver.execute_script("mobile: pressButton", {"name": key.lower()})
            return True
        logger.warning(f"iOS 不支持的按键: {key}，跳过")
        return False

    def long_press(self, x: int, y: int, duration: float = 1.0) -> bool:
        """长按坐标（iOS: mobile: touchAndHold）"""
        try:
            self.driver.execute_script("mobile: touchAndHold", {
                "x": x, "y": y, "duration": duration
            })
            return True
        except Exception as e:
            logger.warning(f"iOS long_press 失败: ({x},{y}), error={e}")
            return False

    def start_app(self, bundle_id: str, activity: str = None) -> bool:
        """启动 App（iOS: activate_app(bundle_id)，忽略 activity）"""
        try:
            self.driver.activate_app(bundle_id)
            return True
        except Exception as e:
            logger.error(f"iOS 启动 App 失败: {bundle_id}, {e}")
            return False
