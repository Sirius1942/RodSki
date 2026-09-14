<!-- 自动生成 from rodski/docs/TEST_CASE_WRITING_GUIDE.md  请勿手工编辑 -->

## 15. iOS 自动化（v7.3.0）

### 15.1 概述

v7.3.0 补全了 iOS 原生自动化支持。核心原则：

- **关键字层平台无关**：`type / verify / navigate / wait / close` 在 iOS 上与 Android 语义完全一致
- **平台差异只在 model.xml 中**：通过 `driver_type="mobile"` + 定位器 `platform` 属性区分
- **数据层完全复用**：`data.sqlite` 与平台无关，Android/iOS 共用同一份数据

### 15.2 driver_type="mobile"

新增 `driver_type="mobile"` 表示平台无关的移动端模型，运行时由 `--platform` 参数或 `Mobile.Platform` 决定实际平台。

`driver_type` 完整枚举：`web` / `interface` / `database` / `windows` / `macos` / `android` / `ios` / **`mobile`**（v7.3.0 新增）

### 15.3 定位器 platform 属性

`<location>` 元素新增可选 `platform` 属性（`android` / `ios`，缺省 = 通用）：

```xml
<element name="username" type="mobile">
  <type>input</type>
  <location type="id" platform="android" priority="1">com.rodski.demo:id/username</location>
  <location type="id" platform="ios"     priority="1">username_field</location>
  <location type="ocr"                   priority="2">用户名</location>
</element>
```

**解析规则**：运行时过滤 `platform` 不匹配的 location，再按 `priority` 排序；同 priority 下平台匹配优先于通用。

### 15.4 定位器跨平台能力

| 定位器 | 跨平台 | 说明 |
|--------|--------|------|
| `ocr` / `text` / `vision` / `vision_image` | ✅ | 无需 platform 标记 |
| `vision_bbox` | ⚠️ | 坐标因分辨率不同，建议标 platform |
| `id` / `xpath` / `class` | ❌ | 平台专属，必须标 platform |

### 15.5 iOS 专属定位器

v7.3.0 新增两个 iOS 高性能定位器（必须标 `platform="ios"`）：

| 定位器 | 说明 |
|--------|------|
| `predicate` | NSPredicate 字符串，如 `label == '登录' AND type == 'XCUIElementTypeButton'` |
| `class_chain` | XCUITest 路径，如 `` **/XCUIElementTypeButton[`label == '登录'`] `` |

```xml
<location type="predicate"   platform="ios" priority="1">label == '登录'</location>
<location type="class_chain" platform="ios" priority="2">**/XCUIElementTypeButton[`label == '登录'`]</location>
```

### 15.6 推荐 model 写法（模式 B：平台标记 + 跨平台兜底）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<models>
  <model name="LoginScreen" type="ui" driver_type="mobile">
    <element name="username" type="mobile">
      <type>input</type>
      <location type="id" platform="android" priority="1">com.rodski.demo:id/username</location>
      <location type="id" platform="ios"     priority="1">username_field</location>
      <location type="ocr"                   priority="2">用户名</location>
    </element>
    <element name="loginBtn" type="mobile">
      <type>button</type>
      <location type="id"          platform="android" priority="1">com.rodski.demo:id/loginBtn</location>
      <location type="predicate"   platform="ios"     priority="1">label == '登录'</location>
      <location type="text"                           priority="2">登录</location>
    </element>
  </model>
</models>
```

### 15.7 iOS GlobalValue 配置

```xml
<globalvalue>
  <group name="Mobile">
    <var name="Platform"          value="ios"/>
    <var name="AppiumServer"      value="http://127.0.0.1:4723"/>
    <var name="DeviceName"        value="iPhone 16"/>
    <var name="UDID"              value="AC199BB6-54B6-424A-9D3C-B8CEA8DF89BC"/>
    <var name="BundleId"          value="com.rodski.demo"/>
    <var name="AppTarget"         value="app://ios/com.rodski.demo"/>
    <var name="NoReset"           value="true"/>
    <var name="NewCommandTimeout" value="120"/>
  </group>
</globalvalue>
```

### 15.8 平台切换

```bash
# CLI 参数（临时切换）
rodski run case/login.xml --platform ios
rodski run case/login.xml --platform android

# 通过计划（持久配置）
rodski run @ios_smoke     # plan 指向 globalvalue_ios.xml
```

### 15.9 环境要求

| | Simulator | 真机 |
|--|-----------|------|
| 连接 | 无需 | USB + WebDriverAgent（需 Apple 开发者账号签名） |
| SDK | 随 Xcode | 需对应 iOS 版本 SDK |

**Simulator 快速启动**：

```bash
xcrun simctl boot "iPhone 16"
xcrun simctl install booted RodskiDemo.app
rodski run case/login.xml --platform ios
```

---
