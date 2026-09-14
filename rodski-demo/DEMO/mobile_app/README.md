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
│   ├── build_ios_app.sh       # 构建到**模拟器**（CODE_SIGNING_ALLOWED=NO）
│   └── build_ios_device_app.sh # 构建并安装到**真机**（需有效开发证书 + 开发者模式）
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
│   ├── queue_{short_a,long_b,short_c}.xml      # 双模拟器队列验收（v11.2.0）
│   ├── mixed_{short_a,long_b,short_c}.xml      # iOS 真机+模拟器混跑（v11.3.0）
│   └── android_queue_{a,b,c}.xml               # Android 真机+模拟器混跑（v11.3.0）
├── scripts/
│   ├── run_dual_device_demo.sh   # 双模拟器并行验收（v11.2.0）
│   ├── run_mixed_device_demo.sh  # iOS 真机 + 模拟器混跑验收（v11.3.0）
│   ├── run_android_mixed_demo.sh # Android 真机 + 模拟器混跑验收（v11.3.0）
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
| `plan/android_queue_a.xml` | APP002 | 3 | Android 混跑：短计划 |
| `plan/android_queue_b.xml` | APP003 | 8 | Android 混跑：长计划 |
| `plan/android_queue_c.xml` | APP001 | 3 | Android 混跑：第二班计划 |

> **Android 混跑已实地验收**（v11.3.0，见下方「Android 真机 + 模拟器混跑验收」）。

### 关键配置项

| 配置 | 位置 | 说明 |
|------|------|------|
| `Mobile.UDID` | `data/globalvalue_ios.xml` | 目标模拟器；可被 `rodski run --udid` 覆盖 |
| `--udid` | `rodski run` | 单设备选择。**必须晚于 `--platform` 的平台配置合并生效**，否则会被 `globalvalue_ios.xml` 里的 UDID 静默改回（不报错但打错机器） |
| `wdaLocalPort` / `systemPort` | 自动推导 | 按 UDID 哈希分槽（8100/8200/9100 + 10×槽位）。不区分端口时，同机第二个 XCUITest 会话会**复用第一台设备的 WDA**，表现为随机的元素定位失败 |

## 真机 + 模拟器混跑验收（v11.3.0）

**目标：一台 iOS 真机 + 一台 iOS 模拟器同时跑 app 测试。**

比双模拟器（上一节）强在哪：两台设备**平台相同但设备类别不同**。真机走 XCUITest
的真实设备路径（要签名并部署 WebDriverAgent 到手机上），模拟器走模拟器路径 ——
这两条路径在 Appium 内部差异很大，混跑能验证调度与并发端口隔离在异构设备上同样成立。

### 真机前置（三项缺一不可）

| # | 前置 | 怎么确认 |
|---|------|---------|
| 1 | **开发者模式已开** | 手机：设置 > 隐私与安全性 > 开发者模式 → 打开 → 重启 → 弹窗确认。脚本与构建脚本都会硬校验 |
| 2 | **有效的开发证书** | `security find-identity -v -p codesigning` 有输出。证书被吊销时该命令不列出，但 `security find-identity -p codesigning` 会显示 `CSSMERR_TP_CERT_REVOKED` —— 需要到 Xcode > Settings > Accounts 重新登录 Apple ID 签一张 |
| 3 | **手机已信任本机** | 首次连接时手机上点「信任」。否则 `devicectl device install` 失败 |

再加一条经验项：真机首次跑 XCUITest 要**现编译并部署 WDA**（数分钟），脚本用
`WARMUP=1`（默认）把这次预热放在计时窗口之外，队列里测的才是「调度」而不是「首次部署」。

### 一条命令

```bash
# 前置：真机已连接且开发者模式已开、模拟器已 boot、Appium 运行在 127.0.0.1:4723
bash rodski-demo/DEMO/mobile_app/scripts/run_mixed_device_demo.sh
```

真机上的 App 需要单独构建安装（模拟器那份是未签名的，装不上真机）：

```bash
# 构建并安装到真机（自动探测唯一一台 wired+paired 真机）
bash rodski-demo/DEMO/mobile_app/demo_ios_app/build_ios_device_app.sh install

# 多台真机时显式指定
DEVICE_UDID=00008130-001979EE3CF3803A bash .../build_ios_device_app.sh install
TEAM_ID=ABCDE12345 bash .../build_ios_device_app.sh install   # 团队 ID 探测失败时
```

脚本会自动：解析真机（`devicectl`）与模拟器（`simctl`）→ 校验两台都装了 App →
真机预热 → 用 `--dry-run` 确认配置选中的正是这两台 → 三个计划入队 →
用 8 条断言核对 `summary.json`。全部通过时打印
`✅ 真机 + 模拟器混跑验收通过（8/8 断言）`。

### 手动执行

```bash
cd rodski-demo/DEMO/mobile_app

# 1) 看有哪些设备（模拟器 + 真机都在这条命令里）
rodski queue --list-devices --platform ios

# 2) 三个计划入队。**不用给 UDID** —— 用几台、什么类别由
#    data/globalvalue_ios.xml 的 Mobile 组决定（见下一节）
rodski queue --plans @mixed_short_a,@mixed_long_b,@mixed_short_c --platform ios

# 3) 只想先看看会选中哪几台设备（不执行）
rodski queue --plans @mixed_short_a --platform ios --dry-run
```

预期排班（真机显著慢于模拟器，故长计划大概率落在真机；但调度是动态的，
实际归属由 `summary.json` 决定）：

```text
模拟器：[ mixed_short_a ]→[ mixed_short_c ]
真机  ：[ ............ mixed_long_b ............ ]
```

### 设备配置写在用例执行层

「用几台、什么类别的设备」不用每次手敲 UDID，它写在模块的
`data/globalvalue_ios.xml` 里，随用例一起版本化：

```xml
<group name="Mobile">
  <var name="Platform"    value="ios"/>
  <var name="DeviceCount" value="2"/>                 <!-- 期望设备数 -->
  <var name="DeviceMix"   value="real,simulator"/>    <!-- 组合偏好，顺序即优先级 -->
</group>
```

| 变量 | 取值 | 语义 |
|------|------|------|
| `DeviceCount` | 正整数 | 期望设备数。**不写 = 用上全部发现的设备** |
| `DeviceMix` | `real,simulator` | 组合偏好，逗号分隔、**顺序即优先级**。是偏好不是门槛 |
| `DeviceScope` | `all`\|`real`\|`simulator` | 只在某个设备类别里挑 |
| `DeviceList` | UDID **或设备名**列表 | 显式设备池，给定时跳过自动发现 |

**插着真机时真机优先**：发现结果里模拟器常有 20+ 台而真机只有 1 台，
若按发现顺序取前 N 台，真机会被挤出去 —— 明明能用却一台都用不上。故**没写
`DeviceMix` 时真机排在最前**（同类内已就绪的优先）。`DeviceScope=simulator` 是
显式排除真机，该优先级不会越过它。

**零设备是唯一的硬失败**；数量不足或组合凑不齐一律**降级并打印 `[WARN]`**，
用实际可用的设备继续执行（「至少一台能跑就自动执行」）：

```
设备选择（执行配置）：DeviceCount=2, DeviceMix=real+simulator
实际选用 2 台设备（1 台真机、1 台模拟器）：
  - [真机] 00008130-001979EE3CF3803A  Tars2
  - [模拟器] 015EA67B-C996-48DE-A5F3-576B2BED409B  iPhone 16 Pro
```

`rodski run @plan` 也会读这份配置：非默认时**自动转 `rodski queue`**，
不必记两个命令。

```bash
rodski run @mixed_short_a --platform ios              # 配置要求多设备 → 自动转队列
rodski run @mixed_short_a --platform ios --no-queue   # 强制单设备
rodski run @mixed_short_a --platform ios --udid <UDID> # 点名一台，同样不转
```

> 转队列与否取决于 `--platform` 解析出的那份配置：`globalvalue_ios.xml`（有
> `DeviceCount=2`）会转，`globalvalue.xml`（Android，无 `Device*` 变量）不转。

### 验收断言（脚本会逐条打印）

| # | 断言 | 为什么这条能证明问题 |
|---|------|---------------------|
| 1 | 真机与模拟器**都被实际调度到** | 不是靠「给两台设备但其实只用了一台」蒙混过关 |
| 2 | 跨设备计划**时间区间重叠 > 5s** | 串行不可能产生重叠，这是并行唯一诚实的证据 |
| 3 | 每个计划恰好出现在一条结果里（计划不拆分） | 计划是调度粒度，不会被切到两台设备 |
| 4 | 某台设备领了 ≥2 个计划 | 动态领取；静态均分会把这条卡死 |
| 5 | 全部通过（`exit_code=0`、`failed=0`、`error=0`） | 功能正确性 |
| 6 | 真机与模拟器的 **WDA 端口槽不同** | 同槽会复用对方的 WebDriverAgent，表现为随机的元素定位失败 |
| 7 | 每个 `run_dir` 里的 `result.xml` 与计划相符 | 子进程真的走的是既有 `rodski run` 链路，不是桩 |
| 8 | **真机至少完整执行了 1 个计划** | 真机链路真实生效，不是空跑 |

### 混跑专属计划

| 计划 | 用例 | 步数 | 在队列中的作用 |
|------|------|------|---------------|
| `plan/mixed_short_a.xml` | APP002 | 3 | 最短 → 它的设备先跑完，**必须再领一个** |
| `plan/mixed_long_b.xml` | APP003 | 8 | 最长 → 独占一台设备，**全过程不被拆分** |
| `plan/mixed_short_c.xml` | APP001 | 3 | 「第二班」计划，证明**动态领取**；也用作真机预热计划 |

> 与 `queue_*` 计划**内容相同、id 不同**：目的是让两套验收互不干扰 ——
> `rodski queue` 不带 `--plans` 时会取 `plan/` 下全部 `execute="是"` 的计划，
> 两套 id 分开后可以各自单独入队，也便于在 `result/` 里区分是哪套验收的产物。

### 真机与模拟器都在自动发现范围内

`rodski queue --list-devices --platform ios` 会**同时**列出：

- **模拟器** —— `xcrun simctl list devices available --json`（只取 iOS 运行时，
  watchOS/tvOS 模拟器会被滤掉：它们装不了 iOS 应用）
- **真机** —— `xcrun devicectl list devices`（v11.3.0 起）

真机过滤条件是 `platform=iOS` + `reality=physical` + `transportType=wired` +
`pairingState=paired`；**刻意不用 `tunnelState` 当可用性判据** —— 开发者模式刚开、
CoreDevice 隧道尚未建立时它是 `disconnected`，拿它过滤会把一台完全正常的设备误杀
（开发者模式关闭时隧道同样是 `disconnected`，两者无法靠 tunnelState 区分）。
watchOS 设备与「已配对但未连接」的 iPhone 都会被滤掉。

> `devicectl` 的 stdout 面向人眼、Apple 不保证跨版本稳定，框架读的是
> `--json-output` 写出的 JSON 文件 —— 这是 Apple 唯一承诺对脚本稳定的接口。

`--devices` 仍可用作 CLI 覆盖（条目可以是 UDID **或设备名**，如
`--devices Tars2,"iPhone 16"`），它跳过发现、直接信任调用方；日常执行不需要它，
设备由上面的 Mobile 组配置决定。

## Android 真机 + 模拟器混跑验收（v11.3.0）

**目标：一台 Android 真机 + 一台 Android 模拟器（AVD）同时跑 app 测试。**

与上一节的 iOS 混跑同构 —— 平台相同、**设备类别不同**：真机走 USB 上的实体
手机，模拟器走 AVD，设备发现、系统镜像、端口转发都不同，调度与并发端口隔离
能不能在两者之间成立，只能实测。

### 一条命令

```bash
# 前置：真机 USB 已授权、AVD 已创建、Appium 运行在 127.0.0.1:4723
bash rodski-demo/DEMO/mobile_app/scripts/run_android_mixed_demo.sh
```

脚本会自动：解析真机（adb）→ 启动 AVD 并等 `sys.boot_completed` → 起 mock 后端
→ **逐台** `adb reverse` → 按需安装 APK 与 UiAutomator2 server → `--dry-run` 确认
配置选中的正是这两台 → 三个计划入队 → 用 8 条断言核对 `summary.json`。全部通过时
打印 `✅ Android 真机 + 模拟器混跑验收通过（8/8 断言）`。

### 安装 App 时的手机确认弹窗

**华为 HarmonyOS / EMUI 会拦截 adb 侧安装外部 APK**，弹出「风险提示 — 来历不明的
应用」确认框。不确认的后果按安装方式分化，且都不好认：

| 安装方式 | 表现 |
|---------|------|
| `adb install -r` | **静默挂起**（实测 2 分钟无任何输出），看起来像卡死 |
| `adb push` + `pm install -r` | 立刻返回 `INSTALL_FAILED_ABORTED: User rejected permissions`，看起来像权限问题 |

两者其实是同一件事：设备在等**屏幕上的确认**。脚本Step 5 的 `install_apk()` 因此
改成「后台发起安装 + 轮询等待，并在等待期间提示你去点按钮」，实测可用：

```bash
INSTALL_WAIT=180 bash scripts/run_android_mixed_demo.sh   # 留足手动确认时间
```

看到 `⚠️ 若手机上弹出「风险提示 / 继续安装」，请手动点【继续安装】` 时，
**拿起手机点那个按钮**即可，脚本会继续。

> 脚本**不会**去关设备的安装校验（`settings put global package_verifier_enable 0` /
> `verifier_verify_adb_installs 0` / `adb_install_need_confirm 0`）—— 那是降低设备
> 安全策略，不该由一个测试脚本替用户决定。确认框交由人在设备上点。

**Appium 的 UiAutomator2 server 也一并预装**（`~/.appium/.../appium-uiautomator2-server/apks/`）。
若留给 Appium 在建会话时才装，同一个确认框会藏在 Appium 内部，而它的默认超时只有
20s —— 表现为「建会话失败」而不是「有个弹窗等你点」，极难定位。

### 准备 AVD

```bash
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export JAVA_HOME=/opt/homebrew/opt/openjdk@17

sdkmanager --install emulator "system-images;android-34;google_apis;arm64-v8a"
avdmanager create avd -n rodski_api34 \
  -k "system-images;android-34;google_apis;arm64-v8a" -d pixel_6
```

> 用 `arm64-v8a` 镜像：Apple Silicon 上跑 x86_64 镜像要开二进制翻译，慢且不稳。
> 选 API 34 与 `demo_android_app/app/build.gradle` 的 `compileSdk 34` 对齐。

### 后端与端口转发

`demo_android_app` 的 `API_BASE_URL` 是**编译期常量** `http://127.0.0.1:8000`，
改它要重新编译 APK。设备上的 `127.0.0.1` 不是本机，所以必须 `adb reverse`：

```bash
# 设备侧端口固定 8000（改不了），本机侧端口随 MOCK_PORT —— 这样与占用 8000 的
# 其它 demo 可以共存。脚本默认 MOCK_PORT=8000，被占用时用其它端口重跑即可。
MOCK_PORT=18000 bash scripts/run_android_mixed_demo.sh
```

脚本对**每一台**设备各做一次 `adb reverse`。漏掉任何一台，那台上的用例会在
登录页超时失败，而错误信息看起来像「应用 bug」——这是最容易误判的一种失败。

### 设备配置同样写在执行层

Android 侧读的是 `data/globalvalue.xml` 的 Mobile 组（与 iOS 的
`globalvalue_ios.xml` 对应）：

```xml
<group name="Mobile">
  <var name="Platform"    value="android"/>
  <var name="DeviceCount" value="2"/>
  <var name="DeviceMix"   value="real,simulator"/>
</group>
```

| 变量 | 取值 | 语义 |
|------|------|------|
| `DeviceCount` | 正整数 | 期望设备数。**不写 = 用上全部发现的设备** |
| `DeviceMix` | `real,simulator` | 组合偏好，逗号分隔、**顺序即优先级** |
| `DeviceScope` | `all`\|`real`\|`simulator` | 只在某个设备类别里挑 |
| `DeviceList` | serial **或设备名**列表 | 显式设备池，给定时跳过自动发现 |

**Android 侧 `real` / `simulator` 怎么判定**：按 adb serial 前缀 —— `emulator-`
开头（如 `emulator-5554`）是 AVD，其余（`JTK5T19929003495`、`192.168.1.9:5555`）
是实体设备。判据刻意不用 `model:` 限定符或设备名，那些由设备端上报、换镜像就变；
serial 形式由 adb 生成。`--list-devices` 里的 `[真机]` / `[模拟器]` 标签即由此得来。

### 验收断言（脚本会逐条打印）

与 iOS 混跑同一张表（8 条），只有端口那条的措辞不同：Android 的并发隔离靠
`systemPort`（默认 8200/8201），iOS 靠 `wdaLocalPort`（默认 8100）。两者都由
`mobile_port_slot()` 按设备 serial 哈希分槽（步长 10），同槽会复用彼此的
UiAutomator2 会话端口，表现为偶发的建会话失败。

### 混跑专属计划

| 计划 | 用例 | 步数 | 在队列中的作用 |
|------|------|------|---------------|
| `plan/android_queue_a.xml` | APP002 | 3 | 最短 → 它的设备先跑完，**必须再领一个** |
| `plan/android_queue_b.xml` | APP003 | 8 | 最长 → 独占一台设备，**全过程不被拆分** |
| `plan/android_queue_c.xml` | APP001 | 3 | 「第二班」计划，证明**动态领取** |

### 实测结果（本机，8/8 断言通过）

```
设备选择（执行配置）：DeviceCount=2, DeviceMix=real+simulator
实际选用 2 台设备（1 台真机、1 台模拟器）：
  - [真机] JTK5T19929003495  TAS_AL00
  - [模拟器] emulator-5554  sdk_gphone64_arm64

  android_queue_b   模拟器  emulator-5554    PASS  10:26:24 → 10:26:45   21.1s
  android_queue_a   真机    JTK5T19929003495 PASS  10:26:24 → 10:26:55   31.5s
  android_queue_c   模拟器  emulator-5554    PASS  10:26:45 → 10:26:58   13.4s

✅ 断言 1：真机与模拟器都被实际调度到
✅ 断言 2：跨设备计划区间重叠 21.1s（> 5s，真并行）
✅ 断言 3：每个计划恰好出现一次（计划粒度，不被拆分）
✅ 断言 4：模拟器领了 2 个计划（动态领取，非静态均分）
✅ 断言 5：3/3 全部通过（failed=0, error=0, unclaimed=0）
✅ 断言 6：systemPort 槽不同（真机 8740 / 模拟器 8560）
✅ 断言 7：三个 run_dir 里的 result.xml 与计划相符
✅ 断言 8：真机完整执行 1 个计划
✅ Android 真机 + 模拟器混跑验收通过（8/8 断言）—— 墙钟 34s
```

### 混跑才暴露的两个缺陷（v11.3.0 修复）

首次混跑是 **2/3 通过**，失败的是落在模拟器上的 `android_queue_c`。报错说
「元素 `username` 所有定位器均失败」，但根因与元素无关 —— 是**导航根本没生效**：

```
[1] navigate → adb am start 失败: adb: more than one device/emulator → status=OK
[1] type(model=LoginScreen) → ❌ 元素 'username' 所有定位器均失败
```

**缺陷 A：`start_app` 的 adb 调用不带 `-s <serial>`。** `adb shell am start` 是
**独立于 Appium session 的第二条通道**，adb 不知道 session 绑在哪台设备上。
真机 + 模拟器同时在线时它直接拒绝执行（`exit=1`）。修复：
`AppiumDriver` 持有 `self.udid`，据此发 `adb -s <udid> shell am start ...`；
无 udid 时不写 `-s`，单设备路径不变。

**为什么只有 `c` 失败**：`NoReset=true` 时 UiAutomator2 建会话会先查进程是否还在，
在就**跳过启动**。于是同一台设备上的**第二个计划**完全依赖 `am start` 把它带回
登录页 —— 上一轮结束时 App 停在订单详情页，这条链路一断就必然失败；第一个计划
因恰好停在登录页而侥幸通过。

**缺陷 B：`_kw_navigate` 把启动失败吞掉。** 原实现无论 `start_app` 返回什么
都 `store_return(True)` 并照常返回，于是日志里出现「`am start 失败`」与
「`navigate 成功 status=OK`」相邻，步骤状态是 `OK`。修复：失败时抛 `DriverError`，
让步骤如实失败 —— 报错指向真正出问题的那一步。

> 附带发现：`am start` 的**退出码不可靠**。Activity 不存在时它照样 `exit=0`，
> 只在 stderr 打 `Error type 3`，所以判据必须是「退出码非 0 **或** stderr 命中失败标记」。
> 标记取具体的 `Error type` / `does not exist` / `Permission Denial` / `SecurityException`，
> **不是**裸的 `"Error"` —— 目标 Activity 已在最前时 `am start` 会打
> `Warning: Activity not started, intent has been delivered to currently top Activity`
> 且 `exit=0`，那是重复导航的常态，不能判成失败。

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
