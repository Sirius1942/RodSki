# RodSki iOS Demo App（SwiftUI）

本目录是 RodSki 移动端 **iOS** 自动化测试的被测应用，与 Android Demo
（`demo_android_app/`，包名 `com.rodski.demo`）一一对齐，演示
**登录 → 主页 → 订单列表 → 订单详情** 多页面流程。

每个交互元素均通过 `.accessibilityIdentifier("xxx")` 设置可访问性标识，
供 RodSki / Appium（XCUITest）定位。

## 被测应用

`RodskiDemo`（bundle id `com.rodski.demo`，与 Android 包名对齐）是一个最小
SwiftUI 应用：

| View | accessibility-id | 说明 |
|------|------------------|------|
| `LoginView` | `username_field` / `password_field` / `login_button` / `error_msg` | 登录页（本地校验 demo/demo123） |
| `HomeView` | `welcome_text` / `order_list_button` | 主页（欢迎，{username}） |
| `OrderListView` | `order_list` / `order_item` | 订单列表 |
| `OrderDetailView` | `order_no` / `customer_name` / `amount` / `status` | 订单详情 |

**有效测试账号：`demo` / `demo123`**

> 首次验收简化：登录与订单数据为本地内置（见 `RodskiDemoApp.swift` 的 `DemoData`），
> 订单数据与 Android 端 `scripts/mock_server.py` 的 `ORDERS` 完全一致，暂不调后端。

## 目录结构

```text
demo_ios_app/
├── RodskiDemo/
│   ├── RodskiDemoApp.swift     # @main 入口 + Order 模型 + DemoData
│   ├── LoginView.swift         # 登录页
│   ├── HomeView.swift          # 主页
│   ├── OrderListView.swift     # 订单列表
│   └── OrderDetailView.swift   # 订单详情
├── project.yml                 # xcodegen 工程定义
├── build_ios_app.sh            # 构建脚本（xcodegen + xcodebuild）
└── README.md
```

> `RodskiDemo.xcodeproj/` 和 `build/` 由脚本生成，不纳入版本管理。

## 构建

依赖：Xcode（`xcodebuild`）+ `xcodegen`（`brew install xcodegen`）。

```bash
cd rodski-demo/DEMO/mobile_app/demo_ios_app

# 生成工程并编译到 iPhone 16 模拟器
bash build_ios_app.sh

# 额外安装并启动到已启动的 iPhone 16 模拟器
bash build_ios_app.sh install
```

产物路径：

```text
build/Build/Products/Debug-iphonesimulator/RodskiDemo.app
```

## 安装 / 启动到模拟器（手动）

```bash
xcrun simctl boot "iPhone 16"        # 若未启动
xcrun simctl install booted build/Build/Products/Debug-iphonesimulator/RodskiDemo.app
xcrun simctl launch booted com.rodski.demo
```

## 与 Android Demo 的对齐说明

- bundle id `com.rodski.demo` 对齐 Android 包名，便于共用 RodSki 模型语义。
- accessibility-id 命名采用 snake_case（`username_field` 等），对应 iOS 模型
  应使用 `<location type="accessibility_id">username_field</location>`。
- 4 个页面、订单字段（order_id / customer / amount / status）、有效账号
  （demo / demo123）均与 Android 端保持一致。
