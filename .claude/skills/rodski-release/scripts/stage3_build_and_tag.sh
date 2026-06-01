#!/usr/bin/env bash
# stage3_build_and_tag.sh — 阶段 3：同步版本号 + 打包 + 打 tag
#
# 用法: stage3_build_and_tag.sh <VERSION>
#
# 职责:
#   1. 同步所有版本号文件（根 pyproject / rodski/__init__.py / 文档）
#   2. 从根目录构建 wheel + sdist
#   3. 运行 release_check.sh 验证 wheel 完整性
#   4. git commit 版本号变更
#   5. 打 annotated tag
#
# 注意: tag 在 PyPI 上传成功之前不 push 远端（由 stage5 负责）

set -euo pipefail
source "$(dirname "$0")/_common.sh"

VERSION=$(require_version "${1:-}")
cd "$PROJECT_ROOT"

info "═══════════════════════════════════════════════════════════"
info " Stage 3: 打包 + 打 tag (v${VERSION})"
info "═══════════════════════════════════════════════════════════"

require_stage stage2_5 "$VERSION"
require_on_main

# 防止重复打 tag
if git tag -l "v${VERSION}" | grep -q "v${VERSION}"; then
    fail "tag v${VERSION} 已存在。若需重新发布，先运行 rollback_tag.sh ${VERSION}。"
fi

info "[1/5] 同步所有版本号文件..."
bump_all_versions "$VERSION"

info "[2/5] 提交版本号变更..."
git add \
    "$PROJECT_ROOT/pyproject.toml" \
    "$RODSKI_DIR/pyproject.toml" \
    "$RODSKI_DIR/__init__.py" \
    "$PROJECT_ROOT/CLAUDE.md" \
    "$RODSKI_DIR/docs/" \
    2>/dev/null || true
# 只提交有变更的文件
if git diff --cached --quiet; then
    info "  版本号无变更，跳过 commit"
else
    git commit -m "chore(v${VERSION}): 版本号更新到 ${VERSION}"
    ok "  版本号 commit 已创建"
fi

info "[3/5] 清理旧产物并构建..."
rm -rf "$DIST_DIR" "$PROJECT_ROOT/build"
python3 -m build "$PROJECT_ROOT/" --outdir "$DIST_DIR"
ok "  构建完成: $(ls "$DIST_DIR")"

info "[4/5] 验证 wheel 完整性..."
if [[ -f "$PROJECT_ROOT/scripts/release_check.sh" ]]; then
    "$PROJECT_ROOT/scripts/release_check.sh" "$VERSION" \
        || fail "wheel 完整性验证失败，发布中止。"
    ok "  wheel 完整性验证通过"
else
    warn "  release_check.sh 不存在，跳过完整性验证"
fi

info "[5/5] 打 annotated tag v${VERSION}..."
git tag -a "v${VERSION}" -m "v${VERSION}"
ok "  tag v${VERSION} 已创建（尚未 push 远端）"

write_state stage3 "$VERSION"

ok "═══════════════════════════════════════════════════════════"
ok " Stage 3 完成"
ok "═══════════════════════════════════════════════════════════"
echo
info "下一步: stage4_clean_verify.sh ${VERSION}"
warn "注意: tag 尚未 push 远端，等 stage5 上传 PyPI 成功后统一 push。"
