"""Android 专用驱动 — Appium 2.x W3C capabilities"""
try:
    from appium.options import UiAutomator2Options
    _HAS_APPIUM_OPTIONS = True
except ImportError:
    _HAS_APPIUM_OPTIONS = False

from .appium_driver import AppiumDriver


class AndroidDriver(AppiumDriver):
    """Android 设备驱动（Appium 2.x）"""

    def __init__(self, device_name: str = "Android", app_package: str = None,
                 app_activity: str = None, server_url: str = "http://localhost:4723", **kwargs):
        if _HAS_APPIUM_OPTIONS:
            options = UiAutomator2Options()
            options.platform_name = "Android"
            options.device_name = device_name
            options.automation_name = "UiAutomator2"
            if app_package:
                options.app_package = app_package
            if app_activity:
                options.app_activity = app_activity
            if kwargs.get("udid"):
                options.udid = kwargs["udid"]
            super().__init__(options=options, server_url=server_url)
        else:
            # 回退：旧格式（Appium 1.x 兼容）
            capabilities = {
                "platformName": "Android",
                "deviceName": device_name,
                "automationName": "UiAutomator2"
            }
            if app_package:
                capabilities["appPackage"] = app_package
            if app_activity:
                capabilities["appActivity"] = app_activity
            super().__init__(capabilities, server_url)

    def start_activity(self, package: str, activity: str) -> bool:
        try:
            self.driver.start_activity(package, activity)
            return True
        except Exception:
            return False

    def press_keycode(self, keycode: int) -> bool:
        try:
            self.driver.press_keycode(keycode)
            return True
        except Exception:
            return False
