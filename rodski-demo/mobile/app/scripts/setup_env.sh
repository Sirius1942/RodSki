#!/usr/bin/env bash
# Android 自动化测试环境安装脚本
# 用途：安装 Appium 2.x 及 UiAutomator2 驱动
set -e

echo "=== RodSki Mobile 环境安装 ==="

# 1. 检查 Node.js
if ! command -v node &>/dev/null; then
  echo "[ERROR] Node.js 未安装。请先运行: brew install node"
  exit 1
fi
NODE_VER=$(node --version)
echo "[OK] Node.js: $NODE_VER"

# 2. 安装 Appium 2.x
echo ""
echo "--- 安装 Appium 2.x ---"
sudo npm install -g appium@latest
APPIUM_VER=$(appium --version)
echo "[OK] Appium: $APPIUM_VER"

# 3. 安装 UiAutomator2 驱动
echo ""
echo "--- 安装 UiAutomator2 驱动 ---"
appium driver install uiautomator2

# 4. 验证安装
echo ""
echo "--- 验证安装结果 ---"
appium driver list --installed

echo ""
echo "=== 安装完成 ==="
echo "启动 Appium Server: appium --port 4723"
echo "验证设备连接:       python3 scripts/check_device.py [UDID]"
