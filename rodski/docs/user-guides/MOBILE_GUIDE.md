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

## 用例示例

### Android 登录测试

```xml
<case name="android_login" driver="android">
  <step name="点击登录按钮">
    <field name="loginBtn">click</field>
  </step>
  <step name="输入用户名">
    <field name="username">type</field>
    <data>testuser</data>
  </step>
  <step name="向上滑动">
    <field name="screen">swipe</field>
    <data>500,1500,500,500</data>
  </step>
  <step name="截图">
    <field name="result">screenshot</field>
    <data>login.png</data>
  </step>
</case>
```

### iOS 表单测试

```xml
<case name="ios_form" driver="ios">
  <step name="长按提交按钮">
    <field name="submitBtn">long_press</field>
  </step>
  <step name="点击坐标">
    <field name="screen">tap</field>
    <data>200,400</data>
  </step>
  <step name="滚动列表">
    <field name="list">scroll</field>
    <data>down</data>
  </step>
</case>
```

## 数据表字段值

在 XML 用例中，`<field>` 标签的文本内容描述对该字段的操作类型：

### 基础操作
- `click` - 点击元素
- `type` - 输入文本（需配合 `<data>` 提供内容）
- `check` - 检查元素存在
- `screenshot` - 截图（可选 `<data>` 指定文件名）

### 移动端特有操作
- `swipe` - 滑动屏幕（需 `<data>` 提供坐标：`x1,y1,x2,y2`）
- `tap` - 点击坐标（需 `<data>` 提供坐标：`x,y`）
- `long_press` - 长按元素
- `scroll` - 滚动（需 `<data>` 提供方向：`up`/`down`/`left`/`right`）
- `hide_keyboard` - 隐藏键盘

## 定位符格式

- `id=resource_id` - 资源 ID
- `xpath=//path` - XPath
- `accessibility_id=label` - 无障碍标签
- `class=ClassName` - 类名

## 配置文件

参考 `config/android_config.json` 和 `config/ios_config.json`
