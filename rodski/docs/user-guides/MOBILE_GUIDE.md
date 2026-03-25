# 移动端自动化测试指南

## 概述

RodSki v1.1.0 新增移动端自动化支持，基于 Appium 实现 Android 和 iOS 设备测试。

## 环境准备

### 1. 安装依赖

```bash
pip install Appium-Python-Client>=3.0.0
```

### 2. 安装 Appium Server

```bash
npm install -g appium
appium driver install uiautomator2  # Android
appium driver install xcuitest      # iOS
```

### 3. 启动 Appium Server

```bash
appium
```

## 驱动使用

### Android

```python
from drivers import AndroidDriver

driver = AndroidDriver(
    device_name="Android Emulator",
    app_package="com.example.app",
    app_activity=".MainActivity"
)

driver.click("id=button")
driver.type("id=input", "text")
driver.swipe(500, 1500, 500, 500)
driver.screenshot("test.png")
driver.close()
```

### iOS

```python
from drivers import IOSDriver

driver = IOSDriver(
    device_name="iPhone 14",
    bundle_id="com.example.app"
)

driver.click("accessibility_id=button")
driver.type("accessibility_id=input", "text")
driver.swipe(200, 800, 200, 200)
driver.screenshot("test.png")
driver.close()
```

## 支持的关键字

### 基础操作
- `click` - 点击元素
- `type` - 输入文本
- `check` - 检查元素存在
- `wait` - 等待
- `screenshot` - 截图

### 移动端特有
- `swipe` - 滑动屏幕
- `tap` - 点击坐标
- `long_press` - 长按元素
- `scroll` - 滚动
- `hide_keyboard` - 隐藏键盘

## 定位符格式

- `id=resource_id` - 资源 ID
- `xpath=//path` - XPath
- `accessibility_id=label` - 无障碍标签
- `class=ClassName` - 类名

## 配置文件

参考 `config/android_config.json` 和 `config/ios_config.json`
