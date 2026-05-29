#!/usr/bin/env bash
# stage1_merge_to_main.sh — 阶段 1：合并功能分支到 main
#
# 用法: stage1_merge_to_main.sh <VERSION>
#
# 职责:
#   1. 检查当前在 main 分支
#   2. 拉取最新远端
#   3. 检查是否存在 feature/v<VERSION>* 未合并分支，全部 merge 进来
#   4. 检查工作区干净
#   5. 写入状态文件标记 stage1 完成

set -euo pipefail
source "$(dirname "$0")/_common.sh"

VERSION=$(require_version "${1:-}")
cd "$PROJECT_ROOT"

info "═══════════════════════════════════════════════════════════"
info " Stage 1: 合并功能分支到 main (v${VERSION})"
info "═══════════════════════════════════════════════════════════"

require_on_main

info "[1/4] 拉取远端最新..."
git fetch origin main
LOCAL_HEAD=$(git rev-parse main)
REMOTE_HEAD=$(git rev-parse origin/main)
if [[ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]]; then
    git merge --ff-only origin/main || fail "main 与 origin/main 出现分叉，无法 fast-forward。请先 rebase。"
fi
ok "main 与 origin/main 同步"

info "[2/4] 检查 PyPI 上 v${VERSION} 是否已存在..."
check_pypi_not_exists "$VERSION"

info "[3/4] 合并 feature/v${VERSION}* 未合并分支..."
UNMERGED=$(git branch --no-merged main | grep "feature/v${VERSION}" || true)
if [[ -n "$UNMERGED" ]]; then
    while IFS= read -r branch; do
        branch=$(echo "$branch" | xargs)
        [[ -z "$branch" ]] && continue
        info "  合并 $branch ..."
        git merge "$branch" --no-ff -m "Merge ${branch}: release v${VERSION}" \
            || fail "合并 $branch 失败，请手动解决冲突后重跑 stage1。"
        ok "  ✓ $branch 已合并"
    done <<< "$UNMERGED"
else
    info "  无需合并的 feature/v${VERSION}* 分支"
fi

info "[4/4] 检查工作区干净..."
require_clean_rodski

write_state stage1 "$VERSION"

ok "═══════════════════════════════════════════════════════════"
ok " Stage 1 完成"
ok "═══════════════════════════════════════════════════════════"
echo
info "下一步: stage2_acceptance.sh ${VERSION}"
