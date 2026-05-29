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

info "[1/5] 创建干净 venv..."
python3 -m venv "$VENV_DIR"
VENV_PY="$VENV_DIR/bin/python3"
VENV_RODSKI="$VENV_DIR/bin/rodski"
ok "  venv 创建完成: $VENV_DIR"

info "[2/5] 安装 wheel + UI 测试依赖..."
"$VENV_PY" -m pip install --quiet "$WHEEL"
# playwright 是可选驱动，不在 wheel 依赖里，但 demo_full 验收需要
"$VENV_PY" -m pip install --quiet playwright
"$VENV_PY" -m playwright install chromium --with-deps 2>&1 | tail -3 || true
ok "  wheel + playwright 安装完成"

info "[3/5] 验证 CLI 版本号..."
INSTALLED_VER=$("$VENV_RODSKI" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
if [[ "$INSTALLED_VER" != "$VERSION" ]]; then
    fail "CLI 版本不匹配: 期望 $VERSION，实际 $INSTALLED_VER"
fi
ok "  CLI 版本: $INSTALLED_VER ✓"

info "[4/5] 验证 CLI 子命令（顶层 import 完整性）..."
# 这一步专门防止 v7.1.2 里 "No module named 'core'" 之类的 import 残留漏检
CLI_CHECKS=(
    "capabilities"
    "data validate $PROJECT_ROOT/rodski-demo/DEMO/demo_full"
)
for cmd in "${CLI_CHECKS[@]}"; do
    # 必须在非项目根目录执行，避免 dev 模式的 sys.path 误救
    if ! out=$(cd /tmp && "$VENV_RODSKI" $cmd 2>&1); then
        fail "CLI 子命令 'rodski $cmd' 失败：$out"
    fi
    if [[ "$out" == *"No module named"* ]]; then
        fail "CLI 子命令 'rodski $cmd' 有 import 残留：$out"
    fi
    ok "  ✓ rodski $cmd"
done

info "[5/5] 用安装包跑 demo_full 纯 UI 用例（headless）..."
# 只跑不依赖接口/DB 的纯 UI 用例，避免干净环境缺少外部服务
UI_ONLY_CASES=(
    "rodski-demo/DEMO/demo_full/case/tc017_keywords.xml"
    "rodski-demo/DEMO/demo_full/case/tc015_only.xml"
    "rodski-demo/DEMO/demo_full/case/tc050_builtin_functions.xml"
)
FAILED=0
for f in "${UI_ONLY_CASES[@]}"; do
    name=$(basename "$f" .xml)
    result=$("$VENV_RODSKI" run "$f" --headless 2>&1 | tail -1) || true
    if [[ "$result" == *"失败"* && "$result" != *"0 失败"* ]]; then
        warn "  ✗ $name: $result"
        FAILED=$((FAILED + 1))
    else
        ok "  ✓ $name: $result"
    fi
done
[[ $FAILED -eq 0 ]] || fail "干净环境验收失败：$FAILED 个用例未通过"

write_state stage4 "$VERSION"

ok "═══════════════════════════════════════════════════════════"
ok " Stage 4 完成"
ok "═══════════════════════════════════════════════════════════"
echo
info "下一步: stage5_publish_and_verify.sh ${VERSION}"
