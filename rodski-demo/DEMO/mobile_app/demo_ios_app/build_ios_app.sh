#!/usr/bin/env bash
#
# 构建 RodSki iOS Demo App（SwiftUI），目标 iPhone 16 Simulator。
#
# 依赖：
#   - Xcode（xcodebuild）
#   - xcodegen（brew install xcodegen）—— 用于从 project.yml 生成 .xcodeproj
#
# 用法：
#   bash build_ios_app.sh            # 生成工程并编译到模拟器
#   bash build_ios_app.sh install    # 额外安装到已启动的 iPhone 16 模拟器
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SCHEME="RodskiDemo"
DEST="platform=iOS Simulator,name=iPhone 16"
DERIVED="$SCRIPT_DIR/build"

# 1. 用 xcodegen 生成 .xcodeproj
if ! command -v xcodegen >/dev/null 2>&1; then
  echo "xcodegen 未安装，尝试 brew install xcodegen ..."
  brew install xcodegen
fi
echo "==> 生成 Xcode 工程"
xcodegen generate

# 2. 编译到 iPhone 16 模拟器
echo "==> 编译 ($DEST)"
xcodebuild \
  -project RodskiDemo.xcodeproj \
  -scheme "$SCHEME" \
  -configuration Debug \
  -destination "$DEST" \
  -derivedDataPath "$DERIVED" \
  CODE_SIGNING_ALLOWED=NO \
  build

APP_PATH="$DERIVED/Build/Products/Debug-iphonesimulator/$SCHEME.app"
echo "==> 编译完成: $APP_PATH"

# 3. 可选：安装并启动到模拟器
if [[ "${1:-}" == "install" ]]; then
  echo "==> 安装到 iPhone 16 模拟器"
  xcrun simctl boot "iPhone 16" 2>/dev/null || true
  xcrun simctl install booted "$APP_PATH"
  xcrun simctl launch booted com.rodski.demo
  echo "==> 已启动 com.rodski.demo"
fi
