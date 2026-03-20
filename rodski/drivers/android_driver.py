"""Android 专用驱动"""
from .appium_driver import AppiumDriver


class AndroidDriver(AppiumDriver):
    """Android 设备驱动"""
    
    def __init__(self, device_name: str = "Android", app_package: str = None, app_activity: str = None, server_url: str = "http://localhost:4723"):
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
        except:
            return False
    
    def press_keycode(self, keycode: int) -> bool:
        try:
            self.driver.press_keycode(keycode)
            return True
        except:
            return False
