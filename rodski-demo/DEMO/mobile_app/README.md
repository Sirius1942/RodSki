# RodSki Android 真机 App Demo

本模块是 RodSki 移动端（Android）自动化测试的官方示例与验收载体，演示
**登录 → 主页 → 订单列表 → 订单详情** 多页面流程，全程使用 RodSki 标准关键字
（`navigate` / `type` / `verify` / `wait` / `close`），不新增任何非法 action。

## 被测应用

`demo_android_app/`（包名 `com.rodski.demo`）是一个最小 Kotlin Android 应用：

| Activity | 控件 resource-id | 说明 |
|----------|-----------------|------|
| `.LoginActivity` | `username` / `password` / `loginBtn` / `errorMsg` | 登录页（调 `/api/login`） |
| `.HomeActivity` | `welcomeText` / `orderListBtn` | 主页（欢迎，{username}） |
| `.OrderListActivity` | `orderList` / `orderItem` | 订单列表（调 `/api/orders`） |
| `.OrderDetailActivity` | `orderNo` / `customerName` / `amount` / `status` | 订单详情 |

控件 id 与 `model/model.xml` 一一对齐（4 个 model：`LoginScreen` / `HomeScreen` /
`OrderListScreen` / `OrderDetailScreen`）。

**有效测试账号：`demo` / `demo123`**

> 说明：登录与订单数据来自后端 API（`BuildConfig.API_BASE_URL`），因此真机验收
> 需要一个可达的后端。本模块自带 `scripts/mock_server.py` 作为 mock 后端，
> 无需依赖真实业务服务。

## 目录结构

```text
mobile_app/
├── demo_android_app/          # 被测 Android 应用源码（com.rodski.demo）
├── case/
│   ├── login.xml              # 真机验收用例（execute="是"，APP001/002/003）
│   └── mobile_login.xml       # 准备性 scenario 示例（execute="否"）
├── data/
│   ├── data.sqlite            # 唯一测试数据文件
│   └── globalvalue.xml        # 移动端全局配置（包名/Activity/Appium）
├── fun/
│   ├── data/build_mobile_data_sqlite.py   # 重建 data.sqlite
│   └── mobile/android_keycode.py          # run 扩展示例
├── model/
│   └── model.xml              # 4 个页面模型
├── plan/
│   └── mobile_app_smoke.xml
├── scripts/
│   ├── mock_server.py         # mock 后端（/api/login + /api/orders）
│   ├── check_device.py
│   └── init_data.py
└── result/                    # 框架自动生成
```

## 真机验收（端到端）

### 前置条件

- Android 真机通过 USB 连接，`adb devices` 可见
- 真机已安装 `com.rodski.demo`（见下方"构建并安装 APK"）
- Appium server 可访问（`http://127.0.0.1:4723`）
- Python 已装 Flask（RodSki 依赖已含）

### 步骤

```bash
# 1. 启动 mock 后端（默认 0.0.0.0:8000）
python3 rodski-demo/DEMO/mobile_app/scripts/mock_server.py &

# 2. USB 端口转发：让真机的 127.0.0.1:8000 指向本机 mock 后端
#    （免去局域网 IP 漂移问题；APK 的 API_BASE_URL 应指向 http://127.0.0.1:8000）
adb reverse tcp:8000 tcp:8000

# 3. 启动 Appium server
appium &

# 4. 执行 RodSki 真机验收用例
rodski run rodski-demo/DEMO/mobile_app/case/login.xml

# （可选）带 trace/报告
rodski run rodski-demo/DEMO/mobile_app/case/login.xml --report html --trace
```

预期：APP001 / APP002 / APP003 三个用例全部通过。

### 构建并安装 APK

需要 JDK 17+ 与 Android SDK（`ANDROID_HOME` 指向 commandline-tools）：

```bash
cd rodski-demo/DEMO/mobile_app/demo_android_app
# API_BASE_URL 默认 http://10.x.x.x:8000，配合 adb reverse 建议改为 127.0.0.1:8000
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

> `app/build.gradle` 的 `API_BASE_URL` 决定 APK 访问的后端地址。使用
> `adb reverse` 方案时设为 `http://127.0.0.1:8000`；直连局域网时设为本机 IP。

## RodSki 数据与校验

```bash
# 重建唯一数据文件
python3 rodski-demo/DEMO/mobile_app/fun/data/build_mobile_data_sqlite.py

# 查看数据
sqlite3 rodski-demo/DEMO/mobile_app/data/data.sqlite \
  "select table_name, model_name, table_kind from rs_datatable order by table_name;"

# XML 校验
xmllint --noout --schema rodski/schemas/case.xsd  rodski-demo/DEMO/mobile_app/case/login.xml
xmllint --noout --schema rodski/schemas/model.xsd rodski-demo/DEMO/mobile_app/model/model.xml
xmllint --noout --schema rodski/schemas/globalvalue.xsd rodski-demo/DEMO/mobile_app/data/globalvalue.xml
```
