#!/usr/bin/env bash
#
# setup_ios.sh — RodSki iOS Simulator 测试环境准备脚本（WI-55）
#
# 流程：
#   1. 检查 Xcode / xcodegen / Appium / xcuitest driver
#   2. 启动 iPhone 16 Simulator（已启动则跳过）
#   3. 构建并安装 demo_ios_app 到模拟器
#   4. 提示手动启动 Appium server
#
# 用法：
#   bash scripts/setup_ios.sh                # 默认目标：iPhone 16
#   SIMULATOR_NAME="iPhone 15" bash scripts/setup_ios.sh
#
# 环境要求：
#   - macOS（Xcode 15+ 已安装）
#   - Node.js（brew install node）
#   - appium（npm install -g appium）
#   - xcuitest driver（appium driver install xcuitest）
#   - xcodegen（brew install xcodegen，可选；xcodeproj 已存在时不需要）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IOS_APP_DIR="$MODULE_DIR/demo_ios_app"

SIMULATOR_NAME="${SIMULATOR_NAME:-iPhone 16}"
BUNDLE_ID="com.rodski.demo"
APPIUM_PORT="${APPIUM_PORT:-4723}"

# ─────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────
ok()   { echo "[OK]   $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }
info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }

check_cmd() {
  local cmd="$1"; local install_hint="$2"
  if ! command -v "$cmd" &>/dev/null; then
    fail "$cmd 未安装。$install_hint"
  fi
  ok "$cmd: $(\"$cmd\" --version 2>&1 | head -1)"
}

# ─────────────────────────────────────────────────────
# Step 1：环境检查
# ─────────────────────────────────────────────────────
echo ""
echo "=== [1/4] 环境检查 ==="

# macOS 平台
if [[ "$(uname)" != "Darwin" ]]; then
  fail "iOS Simulator 仅支持 macOS，当前系统：$(uname)"
fi

# Xcode Command Line Tools（xcodebuild）
if ! command -v xcodebuild &>/dev/null; then
  fail "xcodebuild 未找到，请安装 Xcode（App Store）并运行：sudo xcode-select --install"
fi
XCODE_VER=$(xcodebuild -version 2>&1 | head -1)
ok "Xcode：$XCODE_VER"

# xcrun（simctl）
if ! command -v xcrun &>/dev/null; then
  fail "xcrun 未找到，请确认 Xcode Command Line Tools 已安装"
fi
ok "xcrun：available"

# Appium
if ! command -v appium &>/dev/null; then
  fail "appium 未安装。请运行：npm install -g appium"
fi
APPIUM_VER=$(appium --version 2>&1 | head -1)
ok "Appium：$APPIUM_VER"

# xcuitest driver
XCUI_INSTALLED=$(appium driver list --installed 2>&1 | grep -i xcuitest || true)
if [[ -z "$XCUI_INSTALLED" ]]; then
  info "xcuitest driver 未安装，正在安装..."
  appium driver install xcuitest
  ok "xcuitest driver 安装完成"
else
  ok "xcuitest driver：$XCUI_INSTALLED"
fi

# xcodegen（可选，仅在 .xcodeproj 不存在时需要）
XCODEPROJ="$IOS_APP_DIR/RodskiDemo.xcodeproj"
if [[ ! -d "$XCODEPROJ" ]]; then
  if command -v xcodegen &>/dev/null; then
    ok "xcodegen：$(xcodegen --version 2>&1 | head -1)"
  else
    fail "xcodegen 未安装且 .xcodeproj 不存在。请运行：brew install xcodegen，然后重试。"
  fi
else
  ok ".xcodeproj 已存在，xcodegen 可选"
fi

# ─────────────────────────────────────────────────────
# Step 2：启动 iPhone 16 Simulator
# ─────────────────────────────────────────────────────
echo ""
echo "=== [2/4] 启动 ${SIMULATOR_NAME} Simulator ==="

# 查询 UDID
SIM_UDID=$(xcrun simctl list devices available 2>/dev/null \
  | grep "\"${SIMULATOR_NAME}\"" \
  | grep -Eo '\([A-Z0-9-]{36}\)' \
  | head -1 \
  | tr -d '()')

if [[ -z "$SIM_UDID" ]]; then
  fail "未找到可用的模拟器：${SIMULATOR_NAME}。请在 Xcode > Simulator 中创建。"
fi
info "UDID：$SIM_UDID"

# 检查是否已启动
BOOTED=$(xcrun simctl list devices booted 2>/dev/null | grep "$SIM_UDID" || true)
if [[ -n "$BOOTED" ]]; then
  ok "${SIMULATOR_NAME} 已处于 Booted 状态，跳过启动"
else
  info "正在启动 ${SIMULATOR_NAME}..."
  xcrun simctl boot "$SIM_UDID"
  # 等待 Springboard
  info "等待 Simulator 就绪..."
  local_wait=0
  while ! xcrun simctl list devices booted 2>/dev/null | grep -q "$SIM_UDID"; do
    sleep 2
    local_wait=$((local_wait + 2))
    if [[ $local_wait -ge 60 ]]; then
      fail "等待 Simulator 启动超时（60s），请检查 Xcode / Simulator 状态"
    fi
  done
  ok "${SIMULATOR_NAME} 已启动"
fi

# 打开 Simulator.app（让窗口可见，方便调试）
open -a Simulator 2>/dev/null || warn "无法打开 Simulator.app（headless 模式可忽略）"

# ─────────────────────────────────────────────────────
# Step 3：构建并安装 demo_ios_app
# ─────────────────────────────────────────────────────
echo ""
echo "=== [3/4] 构建并安装 $BUNDLE_ID ==="

# 检查是否已安装
ALREADY_INSTALLED=$(xcrun simctl listapps booted 2>/dev/null | grep -i "$BUNDLE_ID" || true)
if [[ -n "$ALREADY_INSTALLED" ]]; then
  ok "App $BUNDLE_ID 已安装，跳过构建（如需重新安装，请先运行：xcrun simctl uninstall booted $BUNDLE_ID）"
else
  info "App 未安装，开始构建..."

  # 生成 .xcodeproj（如需）
  if [[ ! -d "$XCODEPROJ" ]]; then
    info "运行 xcodegen generate..."
    cd "$IOS_APP_DIR"
    xcodegen generate
  fi

  # 编译
  DERIVED="$IOS_APP_DIR/build"
  info "运行 xcodebuild（目标：iOS Simulator，名称：${SIMULATOR_NAME}）..."
  xcodebuild \
    -project "$XCODEPROJ" \
    -scheme "RodskiDemo" \
    -configuration Debug \
    -destination "platform=iOS Simulator,name=${SIMULATOR_NAME}" \
    -derivedDataPath "$DERIVED" \
    CODE_SIGNING_ALLOWED=NO \
    build 2>&1 | grep -E "error:|warning:|Build succeeded|BUILD FAILED|CompileSwift|Compile" || true

  APP_PATH="$DERIVED/Build/Products/Debug-iphonesimulator/RodskiDemo.app"
  if [[ ! -d "$APP_PATH" ]]; then
    fail "编译失败，未找到 $APP_PATH。请检查上方 xcodebuild 输出。"
  fi
  ok "编译完成：$APP_PATH"

  # 安装
  info "安装到 Simulator..."
  xcrun simctl install booted "$APP_PATH"
  ok "安装完成：$BUNDLE_ID"

  # 验证
  VERIFY=$(xcrun simctl listapps booted 2>/dev/null | grep "$BUNDLE_ID" || true)
  if [[ -z "$VERIFY" ]]; then
    fail "安装后未在 Booted 设备应用列表中找到 $BUNDLE_ID"
  fi
  ok "验证安装：$BUNDLE_ID 已出现在 Simulator 应用列表"
fi

# ─────────────────────────────────────────────────────
# Step 4：提示启动 Appium server
# ─────────────────────────────────────────────────────
echo ""
echo "=== [4/4] Appium Server 提示 ==="

if curl -sf "http://127.0.0.1:${APPIUM_PORT}/status" &>/dev/null; then
  ok "Appium server 已在 127.0.0.1:${APPIUM_PORT} 运行"
else
  echo ""
  echo "  Appium server 未运行，请在另一个终端执行："
  echo ""
  echo "      appium --address 127.0.0.1 --port ${APPIUM_PORT} &"
  echo ""
  echo "  等待输出 'Appium REST http interface listener started' 后再运行测试。"
fi

echo ""
echo "=== 环境准备完成 ==="
echo ""
echo "运行 iOS 冒烟测试："
echo "  cd $MODULE_DIR"
echo "  # 确保 data/globalvalue.xml 的 Mobile.Platform=ios（或使用 globalvalue_ios.xml）"
echo "  rodski run @ios_app_smoke"
echo ""
