"""iOS 专用驱动 — Appium 2.x W3C capabilities"""
try:
    from appium.options import XCUITestOptions
    _HAS_APPIUM_OPTIONS = True
except ImportError:
    _HAS_APPIUM_OPTIONS = False

from .appium_driver import AppiumDriver


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
