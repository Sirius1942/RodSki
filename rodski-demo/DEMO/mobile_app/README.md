# RodSki v7 Mobile App Demo

本模块是 v7 移动端 App 模式的准备性 demo，放在 `rodski-demo/DEMO/mobile_app/`，用于沉淀标准 RodSki 模块结构、Android demo app 源码、`model.xml`、`case`、`plan`、`globalvalue.xml` 和唯一测试数据文件 `data/data.sqlite`。

## 当前状态

- v7.0.0 已开始接入 `driver_type="android"` / `driver_type="ios"` 协议，`model/model.xml` 使用 `driver_type="android"`。
- 本模块的 case 默认 `execute="否"`，plan 也默认 `execute="否"`，因为真实执行仍依赖本机 Android SDK、Appium server、已安装 demo APK 和可见真机/模拟器。
- 在未完成真实设备执行前，本模块只能作为准备性 demo，不能作为移动端验收已通过的证据。
- 本模块不新增任何非法 `action`。移动端点击、按键、滚动等行为仍通过 `type` 数据字段值或 `run` 脚本表达。

## 目录结构

```text
mobile_app/
├── apps/
│   └── android-demo-app/          # 轻量 Android demo app 源码
├── case/
│   └── mobile_login.xml           # 默认跳过的移动端示例 case
├── data/
│   ├── data.sqlite                # 唯一测试数据文件
│   └── globalvalue.xml            # 移动端全局配置
├── fun/
│   ├── data/
│   │   └── build_mobile_data_sqlite.py
│   └── mobile/
│       └── android_keycode.py     # run 扩展示例
├── model/
│   └── model.xml
├── plan/
│   └── mobile_app_smoke.xml
└── result/
    └── README.md
```

## Android Demo App

`apps/android-demo-app` 是一个最小 Android 项目源码，包名为 `com.rodski.demoapp`。主界面包含手机号、密码、登录按钮，登录成功后展示欢迎信息和登录手机号。

控件 ID 与 `model/model.xml` 对齐：

| 模型字段 | Android resource-id |
|----------|---------------------|
| `phone` | `com.rodski.demoapp:id/phoneInput` |
| `password` | `com.rodski.demoapp:id/passwordInput` |
| `loginBtn` | `com.rodski.demoapp:id/loginButton` |
| `welcomeText` | `com.rodski.demoapp:id/welcomeText` |
| `signedInPhone` | `com.rodski.demoapp:id/signedInPhone` |

可用测试账号：

| 字段 | 值 |
|------|----|
| 手机号 | `13800000000` |
| 密码 | `demo123.Password` |

App 内会接受去掉脱敏后缀的真实密码 `demo123`。RodSki 数据中保留 `.Password` 后缀，用于遵守日志脱敏约定。

## 手工构建和安装

本次未构建 APK。具备 Android SDK、JDK 和 Gradle/Android Studio 环境后，可手工执行：

```bash
cd rodski-demo/DEMO/mobile_app/apps/android-demo-app
gradle assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

如果本地为该项目生成了 Gradle wrapper，也可以使用 `./gradlew assembleDebug`。没有命令行 Gradle 时，可用 Android Studio 打开 `apps/android-demo-app`，同步后执行 `Run` 或 `Build > Build Bundle(s) / APK(s) > Build APK(s)`。

## 设备前置条件

真实执行移动端 RodSki case 前至少需要：

- Android 模拟器或 USB 真机，且 `adb devices` 可见。
- 已安装 `com.rodski.demoapp` demo app。
- Appium server 可访问，例如 `http://127.0.0.1:4723`。
- RodSki v7 核心已支持 `driver_type="android"`、移动端 `navigate` App URI、移动端 `type` / `verify` 路由。
- 如使用视觉兜底定位，需要截图和 OCR/视觉后端可用。

## RodSki 数据和用例

重新生成唯一数据文件：

```bash
python3 rodski-demo/DEMO/mobile_app/fun/data/build_mobile_data_sqlite.py
```

查看数据文件：

```bash
sqlite3 rodski-demo/DEMO/mobile_app/data/data.sqlite \
  "select table_name, model_name, table_kind from rs_datatable order by table_name;"
```

XML 校验：

```bash
xmllint --noout --schema rodski/schemas/case.xsd rodski-demo/DEMO/mobile_app/case/mobile_login.xml
xmllint --noout --schema rodski/schemas/model.xsd rodski-demo/DEMO/mobile_app/model/model.xml
xmllint --noout --schema rodski/schemas/globalvalue.xsd rodski-demo/DEMO/mobile_app/data/globalvalue.xml
xmllint --noout --schema rodski/schemas/plan.xsd rodski-demo/DEMO/mobile_app/plan/mobile_app_smoke.xml
```

## 后续启用步骤

具备本地设备和 Appium 环境后，启用本 demo 需要做以下变更：

1. 确认 `adb devices` 能看到 Android 真机或模拟器。
2. 构建并安装 `apps/android-demo-app`。
3. 启动 Appium server，并确认 `data/globalvalue.xml` 中的 `Mobile.AppiumServer` 与本机一致。
4. 确认 `navigate` 可解析 `GlobalValue.Mobile.AppTarget` 中的 `app://android/com.rodski.demoapp/.MainActivity`。
5. 确认移动端 `verify` 能读取控件文本。
6. 将 `case/mobile_login.xml` 和 `plan/mobile_app_smoke.xml` 的 `execute` 从 `否` 改为 `是`，并在真实设备上执行。
