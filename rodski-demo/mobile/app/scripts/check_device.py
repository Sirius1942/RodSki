"""Android 真机联通性验证脚本
运行前确保：
1. appium server 已启动：appium --port 4723
2. Android 真机已通过 USB 连接并开启 USB 调试
3. 已安装 Appium-Python-Client>=3.0.0
"""
from appium import webdriver
from appium.options.common.base import AppiumOptions
import sys

def check_device(device_udid: str = None, server_url: str = "http://127.0.0.1:4723"):
    options = AppiumOptions()
    options.set_capability("platformName", "Android")
    options.set_capability("appium:automationName", "UiAutomator2")
    options.set_capability("appium:noReset", True)
    options.set_capability("appium:newCommandTimeout", 30)
    if device_udid:
        options.set_capability("appium:udid", device_udid)

    print(f"连接 Appium Server: {server_url}")
    try:
        driver = webdriver.Remote(server_url, options=options)
        caps = driver.capabilities
        print(f"连接成功!")
        print(f"   设备名称: {caps.get('deviceName', 'unknown')}")
        print(f"   平台版本: {caps.get('platformVersion', 'unknown')}")
        print(f"   UDID: {caps.get('udid', 'unknown')}")
        driver.quit()
        return True
    except Exception as e:
        print(f"连接失败: {e}")
        return False

if __name__ == "__main__":
    udid = sys.argv[1] if len(sys.argv) > 1 else None
    success = check_device(udid)
    sys.exit(0 if success else 1)
