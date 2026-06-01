#!/usr/bin/env bash
# stage2_5_sync_skills.sh — 阶段 2.5：Skills 同步与打包
#
# 用法: stage2_5_sync_skills.sh <VERSION>
#
# 职责:
#   1. 检测 TEST_CASE_WRITING_GUIDE.md 是否有变更
#   2. 有变更则重新切片 reference/，提交 rodski-skills/
#   3. 打 dist/rodski-skills-vX.Y.Z.zip（无论是否变更都打，确保版本对齐）

set -euo pipefail
source "$(dirname "$0")/_common.sh"

VERSION=$(require_version "${1:-}")
cd "$PROJECT_ROOT"

info "═══════════════════════════════════════════════════════════"
info " Stage 2.5: Skills 同步与打包 (v${VERSION})"
info "═══════════════════════════════════════════════════════════"

require_stage stage2 "$VERSION"
require_on_main

SYNC_SCRIPT="$PROJECT_ROOT/rodski-skills/scripts/sync_test_guide.sh"
PKG_SCRIPT="$PROJECT_ROOT/rodski-skills/scripts/package_release.sh"

[[ -f "$SYNC_SCRIPT" ]] || fail "未找到 $SYNC_SCRIPT，请确认 rodski-skills/ 项目已初始化。"
[[ -f "$PKG_SCRIPT" ]]  || fail "未找到 $PKG_SCRIPT，请确认 rodski-skills/ 项目已初始化。"

info "[1/2] 检测测试指南变更..."
set +e
bash "$SYNC_SCRIPT"
SYNC_EXIT=$?
set -e

case $SYNC_EXIT in
    0)
        ok "  测试指南无变更，跳过 commit"
        ;;
    10)
        ok "  测试指南有更新，提交 rodski-skills/"
        git add rodski-skills/
        if git diff --cached --quiet; then
            info "  rodski-skills/ 无暂存变更，跳过 commit"
        else
            git commit -m "docs(skills): sync rodski-test-guide @ v${VERSION}"
            ok "  rodski-skills/ 已提交"
        fi
        ;;
    *)
        fail "sync_test_guide.sh 异常退出 (exit=$SYNC_EXIT)"
        ;;
esac

info "[2/2] 打 skills 发行包..."
bash "$PKG_SCRIPT" "$VERSION"

write_state stage2_5 "$VERSION"

ok "═══════════════════════════════════════════════════════════"
ok " Stage 2.5 完成"
ok "═══════════════════════════════════════════════════════════"
echo
info "下一步: stage3_build_and_tag.sh ${VERSION}"
