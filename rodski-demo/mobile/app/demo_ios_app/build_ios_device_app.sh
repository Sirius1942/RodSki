#!/usr/bin/env bash
#
# build_ios_device_app.sh — 构建并安装 RodSki iOS Demo App 到 **真机**
#
# 与 build_ios_app.sh 的区别：那个面向模拟器（CODE_SIGNING_ALLOWED=NO），
# 这个面向真机，必须用开发证书签名。
#
# 依赖：
#   - Xcode（xcodebuild + devicectl）
#   - xcodegen（brew install xcodegen）
#   - 一个**有效**的 Apple Development 证书（钥匙串里带私钥、未被吊销）
#   - 真机已开「开发者模式」并信任本机
#
# 用法：
#   bash build_ios_device_app.sh                  # 自动探测唯一可用真机
#   bash build_ios_device_app.sh install          # 编译 + 安装到真机
#   TEAM_ID=ABCDE12345 bash build_ios_device_app.sh install
#   DEVICE_UDID=00008130-001979EE3CF3803A bash build_ios_device_app.sh install
#
# 环境变量：
#   TEAM_ID       开发团队 ID。缺省时从 Xcode 上次选中的团队读（PBX 里的
#                 IDEProvisioningTeamManagerLastSelectedTeamID），读不到则报错。
#   DEVICE_UDID   目标真机 UDID（devicectl 的硬件 UDID，形如 00008130-XXXX）。
#                 缺省时自动探测：恰好一台 wired + paired 的真机才接受。
#   BUNDLE_ID     默认 com.rodski.demo，需与 model/case 无关（定位器不依赖 bundle）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SCHEME="RodskiDemo"
BUNDLE_ID="${BUNDLE_ID:-com.rodski.demo}"
DERIVED="${DERIVED:-$SCRIPT_DIR/build_device}"

# ─────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────
ok()   { echo "[OK]   $*"; }
info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

# ─────────────────────────────────────────────────────
# Step 1：环境检查
# ─────────────────────────────────────────────────────
echo ""
echo "=== [1/4] 环境检查 ==="

[[ "$(uname)" == "Darwin" ]] || fail "真机构建仅支持 macOS，当前系统：$(uname)"
command -v xcodebuild >/dev/null || fail "xcodebuild 未找到，请安装 Xcode"
command -v xcrun      >/dev/null || fail "xcrun 未找到，请安装 Xcode Command Line Tools"
ok "Xcode：$(xcodebuild -version 2>&1 | head -1)"

# 签名证书必须**有效**：被吊销的证书 find-identity -v 不列出，
# 但 -p codesigning 会以 CSSMERR_TP_CERT_REVOKED 列出，故两处都查。
VALID_IDS=$(security find-identity -v -p codesigning 2>/dev/null | grep -c "Apple Development" || true)
if [[ "$VALID_IDS" -eq 0 ]]; then
  echo ""
  echo "  钥匙串里没有**有效**的 Apple Development 证书。诊断："
  security find-identity -p codesigning 2>/dev/null | grep -i "Apple Development" | sed 's/^/    /' || true
  echo ""
  fail "请在 Xcode > Settings > Accounts 重新登录 Apple ID 并生成开发证书后重试"
fi
ok "开发证书：$VALID_IDS 个可用"

# 团队 ID：显式 > Xcode 上次选中的团队
if [[ -z "${TEAM_ID:-}" ]]; then
  TEAM_ID=$(defaults read com.apple.dt.Xcode IDEProvisioningTeamManagerLastSelectedTeamID 2>/dev/null || true)
fi
[[ -n "${TEAM_ID:-}" ]] || fail "无法确定 TEAM_ID。请显式传入：TEAM_ID=ABCDE12345 bash $0 install"
ok "TEAM_ID：$TEAM_ID"

# ─────────────────────────────────────────────────────
# Step 2：探测真机
# ─────────────────────────────────────────────────────
echo ""
echo "=== [2/4] 探测真机 ==="

# 真机枚举不走 simctl：devicectl 的 --json-output 是 Apple 唯一承诺稳定的脚本接口。
# 只接受 wired + paired 的 iOS 真机（tunnelState 在开发者模式关闭时是 disconnected，
# 故不能拿它当可用性判据 —— 否则开发者模式已开但隧道未建的窗口期会被误判）。
probe_devices() {
  local out
  out="$(mktemp -t rodski_devices)"
  xcrun devicectl list devices --json-output "$out" >/dev/null 2>&1 || true
  [[ -s "$out" ]] || { rm -f "$out"; return 1; }
  python3 - "$out" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
for x in payload.get("result", {}).get("devices", []):
    props = x.get("deviceProperties", {}) or {}
    conn  = x.get("connectionProperties", {}) or {}
    hw    = x.get("hardwareProperties", {}) or {}
    if (hw.get("platform") or "").lower() != "ios":
        continue
    if (hw.get("reality") or "").lower() != "physical":
        continue
    if conn.get("transportType") != "wired" or conn.get("pairingState") != "paired":
        continue
    print("\t".join([
        hw.get("udid", ""),
        props.get("name", ""),
        props.get("osVersionNumber", ""),
        props.get("developerModeStatus", "unknown"),
    ]))
PY
  rm -f "$out"
}

if [[ -n "${DEVICE_UDID:-}" ]]; then
  ok "使用显式 DEVICE_UDID：$DEVICE_UDID"
else
  # macOS 自带 bash 3.2 没有 mapfile，用 while-read 收集（进程替换不受影响）
  _lines=()
  while IFS= read -r _line; do
    [[ -n "$_line" ]] && _lines+=("$_line")
  done < <(probe_devices || true)

  [[ "${#_lines[@]}" -gt 0 ]] || fail "未探测到已连接的真机。请确认 USB 连接、已配对，并运行：xcrun devicectl list devices"
  if [[ "${#_lines[@]}" -gt 1 ]]; then
    echo "  探测到多台真机，请用 DEVICE_UDID 指定其一："
    for l in "${_lines[@]}"; do echo "    $(cut -f1 <<<"$l")  $(cut -f2,3 <<<"$l")"; done
    fail "目标真机不唯一"
  fi
  DEVICE_UDID="$(cut -f1 <<<"${_lines[0]}")"
  ok "真机：$(cut -f2 <<<"${_lines[0]}") ($(cut -f3 <<<"${_lines[0]}"))  $DEVICE_UDID"
fi

# 开发者模式是硬前置：关闭时 devicectl install 与 WebDriverAgent 都会失败
DEV_MODE="$(probe_devices 2>/dev/null | awk -F'\t' -v u="$DEVICE_UDID" '$1==u {print $4}' || true)"
if [[ "$DEV_MODE" == "disabled" ]]; then
  fail "真机 $DEVICE_UDID 的开发者模式是关闭的。请在手机上开启：设置 > 隐私与安全性 > 开发者模式，然后重启并在弹窗确认"
fi
[[ -n "$DEV_MODE" ]] && ok "开发者模式：$DEV_MODE"

# ─────────────────────────────────────────────────────
# Step 3：生成工程并编译（真机 SDK + 自动签名）
# ─────────────────────────────────────────────────────
echo ""
echo "=== [3/4] 编译到真机 ==="

if ! command -v xcodegen >/dev/null 2>&1; then
  warn "xcodegen 未安装，尝试 brew install xcodegen ..."
  brew install xcodegen
fi
info "生成 Xcode 工程"
xcodegen generate >/dev/null
ok ".xcodeproj 已生成"

info "xcodebuild（-sdk iphoneos，自动签名，TEAM_ID=${TEAM_ID}）"
xcodebuild \
  -project RodskiDemo.xcodeproj \
  -scheme "$SCHEME" \
  -configuration Debug \
  -sdk iphoneos \
  -derivedDataPath "$DERIVED" \
  -allowProvisioningUpdates \
  DEVELOPMENT_TEAM="$TEAM_ID" \
  CODE_SIGN_STYLE=Automatic \
  CODE_SIGN_IDENTITY="Apple Development" \
  PRODUCT_BUNDLE_IDENTIFIER="$BUNDLE_ID" \
  build

APP_PATH="$DERIVED/Build/Products/Debug-iphoneos/$SCHEME.app"
[[ -d "$APP_PATH" ]] || fail "编译失败，未找到 $APP_PATH"
ok "编译完成：$APP_PATH"

# 验证真的签了（模拟器构建的产物没有 _CodeSignature）
if [[ -d "$APP_PATH/_CodeSignature" ]]; then
  ok "签名校验：_CodeSignature 存在"
else
  fail "产物没有 _CodeSignature —— 未签名，无法安装到真机"
fi
codesign -dv "$APP_PATH" 2>&1 | grep -E "Identifier|TeamIdentifier|Authority" | sed 's/^/    /' || true

# ─────────────────────────────────────────────────────
# Step 4：安装到真机
# ─────────────────────────────────────────────────────
echo ""
echo "=== [4/4] 安装到真机 ==="

if [[ "${1:-}" != "install" ]]; then
  echo ""
  echo "  编译完成。安装到真机请运行："
  echo ""
  echo "      bash $0 install"
  echo ""
  exit 0
fi

info "devicectl device install_app → $DEVICE_UDID"
xcrun devicectl device install app --device "$DEVICE_UDID" "$APP_PATH" \
  || fail "安装失败。常见原因：手机未信任本机（设置 > 通用 > VPN与设备管理）、描述文件过期、bundleId 冲突"

# 校验安装结果
VERIFY="$(xcrun devicectl device info apps --device "$DEVICE_UDID" 2>/dev/null | grep -c "$BUNDLE_ID" || true)"
if [[ "$VERIFY" -gt 0 ]]; then
  ok "$BUNDLE_ID 已安装到真机 $DEVICE_UDID"
else
  warn "安装命令返回成功，但未在应用列表中查到 ${BUNDLE_ID}（部分 iOS 版本不列出全部应用，可忽略）"
fi

echo ""
echo "=== 真机构建 + 安装完成 ==="
echo ""
echo "运行混跑验收："
echo "  bash $SCRIPT_DIR/run_mixed_device_demo.sh"
echo ""
