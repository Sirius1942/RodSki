"""Android 自动化测试示例"""
from drivers import AndroidDriver

# 初始化驱动
driver = AndroidDriver(
    device_name="Android Emulator",
    app_package="com.android.settings",
    app_activity=".Settings"
)

# 基础操作
driver.click("id=search_button")
driver.type("id=search_src_text", "Wi-Fi")
driver.wait(2)

# 移动端特有操作
driver.swipe(500, 1500, 500, 500)  # 向上滑动
driver.tap(300, 400)  # 点击坐标
driver.hide_keyboard()

# 截图
driver.screenshot("android_test.png")

# 关闭
driver.close()
