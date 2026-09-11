# RodSki 移动端 App Demo（Android / iOS）

本模块是 RodSki 移动端自动化测试的官方示例与验收载体，演示
**登录 → 主页 → 订单列表 → 订单详情** 多页面流程，全程使用 RodSki 标准关键字
（`navigate` / `type` / `verify` / `wait` / `close`），不新增任何非法 action。
同一套 `case/` 与 `model/` 同时驱动 Android（`demo_android_app/`）与
iOS（`demo_ios_app/`），平台差异由模型的 `platform="ios"` 定位器与运行时的
`Mobile.Platform` 决定。

v11.2.0 起本模块还承担 **多设备并行调度** 的官方验收：
见下方「多设备并行验收」。

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
├── demo_ios_app/              # 被测 iOS 应用源码（SwiftUI，com.rodski.demo）
├── case/
│   ├── login.xml              # 真机验收用例（execute="是"，APP001/002/003）
│   └── mobile_login.xml       # 准备性 scenario 示例（execute="否"）
├── data/
│   ├── data.sqlite            # 唯一测试数据文件
│   ├── globalvalue.xml        # 移动端全局配置（Android）
│   └── globalvalue_ios.xml    # iOS 平台配置（Platform=ios + UDID + BundleId）
├── fun/
│   ├── data/build_mobile_data_sqlite.py   # 重建 data.sqlite
│   └── mobile/android_keycode.py          # run 扩展示例
├── model/
│   └── model.xml              # 4 个页面模型（含 platform="ios" 定位器）
├── plan/
│   ├── ios_app_smoke.xml      # iOS 冒烟（单设备）
│   ├── mobile_app_smoke.xml   # 准备性示例（execute="否"）
│   ├── mobile_smoke.xml       # Android 冒烟
│   ├── queue_{short_a,long_b,short_c}.xml      # 多设备队列验收（v11.2.0）
│   └── android_queue_{a,b}.xml                 # Android 队列预留（execute="否"）
├── scripts/
│   ├── run_dual_device_demo.sh   # 双设备并行验收（v11.2.0）
│   ├── mock_server.py            # mock 后端（/api/login + /api/orders）
│   ├── setup_ios.sh              # 单设备 iOS 环境准备
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

## 多设备并行验收（v11.2.0）

**目标：两台设备同时跑 app 测试，同时保证「一个 plan 只在一台设备上执行」。**

调度的并行单元是**计划**，不是用例：三个长度不等的计划放进一个队列，
每台设备领一个计划整体跑完，先跑完的设备**回去再领下一个**（动态领取，
而不是预先均分）。

### 一条命令

```bash
# 前置：两台模拟器已 boot、com.rodski.demo 已装、Appium 运行在 127.0.0.1:4723
bash rodski-demo/DEMO/mobile_app/scripts/run_dual_device_demo.sh
```

脚本会自动：解析并启动两台模拟器 → 安装预编译的 `RodskiDemo.app` →
跑一遍并行（Run A）与一遍单设备串行（Run B，负对照）→ 用 7 条断言核对
`summary.json`。全部通过时打印 `✅ 双设备并行验收通过（7/7 断言）`。

### 手动执行

```bash
cd rodski-demo/DEMO/mobile_app

# 1) 看有哪些设备可用
rodski queue --list-devices --platform ios

# 2) 三个计划入队，两台设备动态领取
rodski queue --plans @queue_short_a,@queue_long_b,@queue_short_c \
             --devices <UDID-A>,<UDID-B> --platform ios
```

预期排班（`result/rodski_*_queue/summary.json` 里可见）：

```text
设备 A：[ queue_short_a ]→[ queue_short_c ]
设备 B：[ ............ queue_long_b ............ ]
```

### 验收断言（脚本会逐条打印）

| # | 断言 | 为什么这条能证明问题 |
|---|------|---------------------|
| 1 | 两个计划在不同设备上**时间区间重叠 > 5s** | 串行执行不可能产生区间重叠，这是并行唯一诚实的证据 |
| 2 | 每个计划的 `device_udid` 都是两台已 boot 设备之一 | 设备隔离，且没有 `devices[0]` 回落 |
| 3 | 每个计划恰好出现在一条结果里（计划不拆分） | 计划是调度粒度，不会被切到两台设备 |
| 4 | 某台设备领了 ≥2 个计划，且不是跑长计划的那台 | 动态领取；静态均分会把这条卡死 |
| 5 | Run A 全通过（`exit_code=0`、`failed=0`） | 功能正确性 |
| 6 | 负对照：单设备只有 1 个 `device_udid`、无重叠、墙钟明显更慢 | 排除「并行只是假象」 |
| 7 | 每个 `run_dir` 里的 `result.xml` 与计划相符 | 子进程真的走的是既有 `rodski run` 链路，不是桩 |

### 队列专属计划

| 计划 | 用例 | 步数 | 在队列中的作用 |
|------|------|------|---------------|
| `plan/queue_short_a.xml` | APP002 | 3 | 最短 → 它的设备先跑完，**必须再领一个** |
| `plan/queue_long_b.xml` | APP003 | 8 | 最长 → 独占一台设备，**全过程不被拆分** |
| `plan/queue_short_c.xml` | APP001 | 3 | 「第二班」计划，证明**动态领取** |
| `plan/android_queue_a.xml` | APP002 | 3 | Android 预留，`execute="否"`（见下） |
| `plan/android_queue_b.xml` | APP003 | 8 | Android 预留，`execute="否"` |

> **Android 未做动态验收**：本机无 Android 真机/模拟器，故 `android_queue_*.xml`
> 保持 `execute="否"`，两个计划只作为验收落点保留。在有 Android 设备的环境里
> 把 `execute` 改为「是」，再用 `rodski queue --platform android` 把两者入队即可
> 复现同样的调度语义。

### 关键配置项

| 配置 | 位置 | 说明 |
|------|------|------|
| `Mobile.UDID` | `data/globalvalue_ios.xml` | 目标模拟器；可被 `rodski run --udid` 覆盖 |
| `--udid` | `rodski run` | 单设备选择。**必须晚于 `--platform` 的平台配置合并生效**，否则会被 `globalvalue_ios.xml` 里的 UDID 静默改回（不报错但打错机器） |
| `wdaLocalPort` / `systemPort` | 自动推导 | 按 UDID 哈希分槽（8100/8200/9100 + 10×槽位）。不区分端口时，同机第二个 XCUITest 会话会**复用第一台设备的 WDA**，表现为随机的元素定位失败 |

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
