# mobile_app — Android 真机自动化测试模块

RodSki v7.0.0 移动端测试模块，基于 Appium 2.x + UiAutomator2 驱动。

## 前置条件

| 依赖 | 版本要求 | 安装命令 |
|------|----------|----------|
| Node.js | >= 18 | `brew install node` |
| Appium | 2.x | `npm install -g appium@latest` |
| UiAutomator2 驱动 | latest | `appium driver install uiautomator2` |
| Android SDK / ADB | >= 30 | `brew install --cask android-commandlinetools` |
| Appium-Python-Client | >= 3.0.0 | `pip install "Appium-Python-Client>=3.0.0"` |

设置环境变量（加入 `~/.zshrc` 或 `~/.bash_profile`）：

```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

## 安装

```bash
# 一键安装 Appium 2.x 及 UiAutomator2 驱动
bash scripts/setup_env.sh

# 安装 Python 客户端
pip install "Appium-Python-Client>=3.0.0"
```

## 启动 Appium Server

```bash
appium --port 4723
```

## 验证设备连接

```bash
# 查看已连接设备
adb devices

# 验证 Appium 与真机联通（不传 UDID 时自动选择第一台设备）
python3 scripts/check_device.py
python3 scripts/check_device.py <DEVICE_UDID>
```

## 运行测试

> 测试用例将在 iteration-49 完成后可用。

```bash
# 届时运行方式（示例）
rodski run plan/mobile_smoke.xml
```

## 目录结构

```
mobile_app/
├── case/        # 测试用例（iteration-46+ 创建）
├── model/       # 页面模型（iteration-46 创建）
├── fun/mobile/  # 移动端关键字（iteration-47+ 创建）
├── data/
│   └── globalvalue.xml   # 全局变量（iteration-49 替换占位符）
├── plan/        # 测试计划（iteration-49 创建）
├── result/      # 测试结果（运行后生成）
└── scripts/
    ├── check_device.py   # 设备联通性验证
    └── setup_env.sh      # 环境安装脚本
```

## 配置说明

`data/globalvalue.xml` 中的占位符需在 iteration-49 替换为真实值：

- `REPLACE_WITH_DEVICE_UDID` → 从 `adb devices` 获取的真机 UDID
- `REPLACE_WITH_MAC_IP` → Mac 的局域网 IP（`ipconfig getifaddr en0`）
