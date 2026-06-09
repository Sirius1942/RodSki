# Iteration 58 — v7.3.0 iOS 自动化测试（Simulator 优先）

**版本**: v7.3.0
**日期**: 2026-06-08
**分支**: `feature/v7.3.0-ios-automation`
**设计文档**: `.pb/specs/v7.3.0-ios-automation-design.md`
**目标**: iOS Simulator 上跑通完整移动端自动化链路，与 Android 用例兼容，定位器最大化复用

---

## 环境前提（已确认就绪）

| 组件 | 版本 | 状态 |
|------|------|------|
| Xcode | 16.4 | ✅ |
| iOS Simulator | iPhone 16 系列 | ✅ 已启动 |
| Appium | 3.4.2 | ✅ |
| XCUITest driver | 11.9.1 | ✅ 已安装 |
| appium-python-client | — | ✅ |

**Simulator 优先**：跳过 WDA 真机签名，直接用模拟器跑通核心链路。真机验收作为后续阶段。

---

## 范围

| 在范围内 | 不在范围内（后续） |
|---------|-----------------|
| iOS Simulator 自动化 | iOS 真机（需 Apple 开发者账号 + WDA 签名）|
| 定位器跨平台复用机制 | iOS 专属高级手势（3D Touch 等）|
| 同一 case 跑 Android + iOS | iPad 适配 |
| 最小 iOS Demo App（SwiftUI）| App Store 分发流程 |

---

## Part A — Schema 与解析层（WI-47, WI-48）

### WI-47: model.xsd 扩展

**改动文件**: `rodski/schemas/model.xsd`

1. `DriverType` 枚举新增 `mobile`（平台无关移动端标记）
2. `LocationType` 新增可选 `platform` 属性（`android` | `ios`，缺省=通用）
3. `LocatorType` 新增 iOS 专属类型 `predicate`、`class_chain`

```xml
<!-- LocationType 新增 -->
<xs:attribute name="platform" use="optional">
  <xs:simpleType>
    <xs:restriction base="xs:string">
      <xs:enumeration value="android"/>
      <xs:enumeration value="ios"/>
    </xs:restriction>
  </xs:simpleType>
</xs:attribute>

<!-- DriverType 新增 -->
<xs:enumeration value="mobile"/>

<!-- LocatorType 新增 -->
<xs:enumeration value="predicate"/>
<xs:enumeration value="class_chain"/>
```

**验证**: 现有 model.xml 仍通过校验（向后兼容）；新写法通过校验。

### WI-48: ModelParser 平台感知过滤

**改动文件**: `rodski/core/model_parser.py`

- 解析 `<location>` 时读取 `platform` 属性
- 新增 `select_locations(element, current_platform)`：按平台过滤 + priority 排序
- 规则：platform 匹配当前平台 OR platform 缺省（通用）→ 保留

**验证**: `pytest rodski/tests/unit/test_model_parser.py`（新增平台过滤用例）

---

## Part B — 驱动层（WI-49, WI-50, WI-51, WI-52）

### WI-49: AppiumDriver `_resolve_locator` 平台钩子重构

**改动文件**: `rodski/drivers/appium_driver.py`

- 将 text → XPath 的构造抽为 `_text_xpath(value)` 钩子方法
- 基类提供 Android 默认实现，子类可重写
- `_LOCATOR_MAP` 改为可被子类覆盖

**验证**: Android 现有测试不回归 `pytest rodski/tests/unit/test_appium_driver.py`

### WI-50: IOSDriver 能力补全

**改动文件**: `rodski/drivers/ios_driver.py`

| 方法 | iOS 实现 |
|------|---------|
| `_text_xpath` | `//*[@label='值' or @name='值' or @value='值']` |
| `_resolve_locator` (id) | `AppiumBy.ACCESSIBILITY_ID` |
| `scroll` | `mobile: scroll` {direction} |
| `swipe` | `mobile: swipe` |
| `key_press` | `mobile: pressButton`（home/volumeup/volumedown）|
| `long_press` | `mobile: touchAndHold` |
| `start_app` | `activate_app(bundleId)`（覆盖 Android 的 adb 逻辑）|
| `hide_keyboard` | iOS 点 return/done |

**验证**: `pytest rodski/tests/unit/test_ios_driver.py`（mock Appium webdriver）

### WI-51: iOS 专属定位器 predicate / class_chain

**改动文件**: `rodski/drivers/ios_driver.py`

- `predicate` → `AppiumBy.IOS_PREDICATE`
- `class_chain` → `AppiumBy.IOS_CLASS_CHAIN`
- 这两个仅 iOS 可用，model 中需标 `platform="ios"`

**验证**: 单元测试覆盖两种定位器解析

### WI-52: navigate `app://ios/` 端到端验证

**改动文件**: 验证 `rodski/rodski_cli/run.py` + `driver_factory.py` 的 iOS 路径

- `navigate app://ios/{bundleId}` → 创建 IOSDriver → activate_app
- 确认 driver_factory 正确传递 bundle_id

**验证**: 集成测试（mock 或 Simulator）

---

## Part C — iOS Demo App（WI-53）

### WI-53: 最小 SwiftUI iOS Demo App

**新增目录**: `rodski-demo/DEMO/mobile_app/demo_ios_app/`

最小 SwiftUI 应用，4 个页面与 Android Demo 一一对齐：

| 页面 | accessibility-id | 对应 Android |
|------|-----------------|-------------|
| LoginView | `username_field` / `password_field` / `login_button` / `error_msg` | LoginActivity |
| HomeView | `welcome_text` / `order_list_button` | HomeActivity |
| OrderListView | `order_list` / `order_item` | OrderListActivity |
| OrderDetailView | `order_no` / `customer_name` / `amount` / `status` | OrderDetailActivity |

**要求**:
- 登录账号 `demo` / `demo123`（与 Android 一致）
- 调 `BuildConfig` 等价的 API base URL（复用 mock_server.py，端口 8000）
- 每个交互元素设置 `.accessibilityIdentifier(...)`
- 提供 `build_ios_app.sh`：xcodebuild 编译为 .app，安装到 Simulator

**验证**: `xcrun simctl install booted demo_ios_app.app` 成功，手动点击可登录

---

## Part D — Demo 集成与验收（WI-54, WI-55）

### WI-54: mobile_app model 改造 + iOS 配置

**改动文件**:
- `rodski-demo/DEMO/mobile_app/model/model.xml` — `driver_type=mobile` + `platform` 标记
- 新增 `rodski-demo/DEMO/mobile_app/data/globalvalue_ios.xml`

model 改造示例：
```xml
<model name="LoginScreen" type="ui" driver_type="mobile">
  <element name="username" type="mobile">
    <type>input</type>
    <location type="id" platform="android" priority="1">com.rodski.demo:id/username</location>
    <location type="id" platform="ios"     priority="1">username_field</location>
    <location type="ocr"                   priority="2">用户名</location>
  </element>
</model>
```

**关键**: case/login.xml 和 data.sqlite **完全不改**，验证用例跨平台兼容。

### WI-55: iOS plan + 环境脚本 + Simulator 验收

**新增文件**:
- `rodski-demo/DEMO/mobile_app/plan/ios_app_smoke.xml`
- `rodski-demo/DEMO/mobile_app/scripts/setup_ios.sh`

`setup_ios.sh` 流程：
1. 检查 Xcode / Appium / XCUITest driver
2. 启动 iPhone 16 Simulator
3. 编译并安装 demo_ios_app
4. 启动 Appium server
5. 启动 mock_server.py（端口 8000）

**验收标准**:
| 检查项 | 必须通过 |
|--------|---------|
| Simulator 跑通 APP001 登录成功 | ✅ |
| 同一条 login.xml 在 Android + iOS 都通过 | ✅ |
| 跨平台定位器（ocr/text）两端复用生效 | ✅ |
| iOS 专属 id（accessibility-id）定位生效 | ✅ |
| result XML 通过 XSD 校验 | ✅ |

---

## Part E — 文档（WI-56）

### WI-56: 文档更新

- `rodski/docs/MOBILE_APP_MODE_DESIGN.md` — 新增 iOS 章节
- `rodski/docs/CORE_DESIGN_CONSTRAINTS.md` — driver_type 枚举 + iOS 定位器 + platform 属性
- `rodski/docs/TEST_CASE_WRITING_GUIDE.md` — 跨平台 model 写法说明

---

## 依赖关系图

```
WI-47 (model.xsd)
  └── WI-48 (ModelParser 平台过滤)
        └── WI-54 (model 改造)

WI-49 (AppiumDriver 钩子)
  └── WI-50 (IOSDriver 补全)
        ├── WI-51 (predicate/class_chain)
        └── WI-52 (navigate app://ios)
              └── WI-55 (Simulator 验收)

WI-53 (iOS Demo App) ──────────────┘ (WI-55 需要)

WI-54 + WI-55 → WI-56 (文档)
```

**关键路径**: WI-49 → WI-50 → WI-52 → WI-55（驱动链路）
**并行**: WI-47/48（schema）、WI-53（Demo App）可与驱动层并行

---

## 完成判定

1. WI-47 ~ WI-56 代码实现完成
2. 单元测试全部通过（含 iOS driver / model parser 平台过滤新测试）
3. iOS Demo App 编译安装到 Simulator 成功
4. 同一条 case 在 Android + iOS Simulator 都验收通过
5. 文档同步更新
6. 版本号更新到 7.3.0（MINOR+1，新功能）

---

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| SwiftUI Demo App 编译环境问题 | 高 | 提供完整 xcodebuild 脚本，先用最简单页面验证 |
| Appium XCUITest 首次启动慢（编译 WDA）| 中 | 文档说明首次启动需等待，后续缓存 |
| iOS accessibility-id 设置遗漏 | 中 | Demo App 每个元素显式设置 + 检查清单 |
| 模拟器分辨率与坐标定位 | 低 | 优先 id/ocr/text，vision_bbox 慎用 |
| 跨平台 model 解析回归 Android | 高 | platform 缺省=通用，确保旧 model 不受影响 |
