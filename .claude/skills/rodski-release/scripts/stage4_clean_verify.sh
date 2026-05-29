#!/usr/bin/env bash
# stage4_clean_verify.sh — 阶段 4：干净环境验收 wheel
#
# 用法: stage4_clean_verify.sh <VERSION>
#
# 职责:
#   在全新 venv 里安装刚打出的 wheel，跑一轮验收：
#   1. CLI 版本号正确
#   2. 核心模块可 import
#   3. 用 --headless 跑 demo_full 主用例（不依赖本地 dev 安装）

set -euo pipefail
source "$(dirname "$0")/_common.sh"

VERSION=$(require_version "${1:-}")
cd "$PROJECT_ROOT"

info "═══════════════════════════════════════════════════════════"
info " Stage 4: 干净环境验收 wheel (v${VERSION})"
info "═══════════════════════════════════════════════════════════"

require_stage stage3 "$VERSION"

WHEEL="$DIST_DIR/rodski-${VERSION}-py3-none-any.whl"
[[ -f "$WHEEL" ]] || fail "wheel 不存在: $WHEEL"

VENV_DIR="$PROJECT_ROOT/.release_venv_${VERSION}"
trap 'rm -rf "$VENV_DIR"' EXIT

info "[1/4] 创建干净 venv..."
python3 -m venv "$VENV_DIR"
VENV_PY="$VENV_DIR/bin/python3"
VENV_RODSKI="$VENV_DIR/bin/rodski"
ok "  venv 创建完成: $VENV_DIR"

info "[2/4] 安装 wheel..."
"$VENV_PY" -m pip install --quiet "$WHEEL"
ok "  wheel 安装完成"

info "[3/4] 验证 CLI 版本号..."
INSTALLED_VER=$("$VENV_RODSKI" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
if [[ "$INSTALLED_VER" != "$VERSION" ]]; then
    fail "CLI 版本不匹配: 期望 $VERSION，实际 $INSTALLED_VER"
fi
ok "  CLI 版本: $INSTALLED_VER ✓"

info "[4/4] 用安装包跑 demo_full 主用例（headless）..."
if ! "$VENV_RODSKI" run rodski-demo/DEMO/demo_full/case/demo_case.xml --headless 2>&1 | tail -3; then
    fail "干净环境验收失败，发布中止。"
fi
ok "  干净环境验收通过"

write_state stage4 "$VERSION"

ok "═══════════════════════════════════════════════════════════"
ok " Stage 4 完成"
ok "═══════════════════════════════════════════════════════════"
echo
info "下一步: stage5_publish_and_verify.sh ${VERSION}"
