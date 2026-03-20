"""iOS 自动化测试示例"""
from drivers import IOSDriver

# 初始化驱动
driver = IOSDriver(
    device_name="iPhone 14",
    bundle_id="com.apple.Preferences"
)

# 基础操作
driver.click("accessibility_id=Wi-Fi")
driver.wait(2)

# 移动端特有操作
driver.swipe(200, 800, 200, 200)  # 向上滑动
driver.tap(200, 300)  # 点击坐标

# 截图
driver.screenshot("ios_test.png")

# 关闭
driver.close()
