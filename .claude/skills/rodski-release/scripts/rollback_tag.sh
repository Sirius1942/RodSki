#!/usr/bin/env bash
# rollback_tag.sh — 紧急回滚：撤销 tag 和版本号 commit
#
# 用法: rollback_tag.sh <VERSION>
#
# 适用场景:
#   - stage3 打了 tag 但 stage4/stage5 失败，需要重新来过
#   - PyPI 上传失败，需要修复后重新发布
#
# 注意: 如果 tag 已 push 到远端，此脚本会提示但不强制删除远端 tag

set -euo pipefail
source "$(dirname "$0")/_common.sh"

VERSION=$(require_version "${1:-}")
cd "$PROJECT_ROOT"

warn "═══════════════════════════════════════════════════════════"
warn " 回滚 v${VERSION} 发布（撤销 tag + 版本号 commit）"
warn "═══════════════════════════════════════════════════════════"

# 删除本地 tag
if git tag -l "v${VERSION}" | grep -q "v${VERSION}"; then
    git tag -d "v${VERSION}"
    ok "  本地 tag v${VERSION} 已删除"
else
    info "  本地 tag v${VERSION} 不存在，跳过"
fi

# 检查远端 tag
REMOTE_TAG=$(git ls-remote --tags origin "refs/tags/v${VERSION}" 2>/dev/null | head -1)
if [[ -n "$REMOTE_TAG" ]]; then
    warn "  远端 origin 上存在 tag v${VERSION}，需要手动删除："
    warn "    git push origin :refs/tags/v${VERSION}"
fi

# 撤销版本号 commit（如果最后一个 commit 是 chore(v${VERSION})）
LAST_MSG=$(git log -1 --pretty=%s)
if [[ "$LAST_MSG" == "chore(v${VERSION}): 版本号更新到 ${VERSION}" ]]; then
    git reset --soft HEAD~1
    ok "  版本号 commit 已撤销（文件保留在暂存区）"
    git restore --staged . 2>/dev/null || true
    ok "  暂存区已清空"
else
    info "  最后一个 commit 不是版本号 commit，跳过撤销"
    info "  最后 commit: $LAST_MSG"
fi

# 清理状态文件
rm -f "$STATE_FILE"
ok "  发布状态文件已清除"

warn "═══════════════════════════════════════════════════════════"
warn " 回滚完成。修复问题后从 stage1 重新开始。"
warn "═══════════════════════════════════════════════════════════"
