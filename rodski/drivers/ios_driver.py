"""iOS 专用驱动"""
from .appium_driver import AppiumDriver


class IOSDriver(AppiumDriver):
    """iOS 设备驱动"""
    
    def __init__(self, device_name: str = "iPhone", bundle_id: str = None, server_url: str = "http://localhost:4723"):
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
        except:
            return False
