#!/bin/bash
# RodSki 双 remote 推送脚本
# 用法: scripts/git_push.sh [branch]
#
# 策略:
#   - GitLab: 推送完整代码（含 releases/ 发布包）
#   - GitHub: 推送代码但不含 releases/（二进制包不上 GitHub）
#
# 原理:
#   main 分支正常开发，releases/ 在 .gitignore 中。
#   GitLab 使用独立的 gitlab-release 分支，包含 releases/ 目录。
#   本脚本自动同步两边。

set -euo pipefail

BRANCH=${1:-main}
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== RodSki 双 remote 推送 ==="
echo "  分支: $BRANCH"
echo ""

# ── 1. 推送到 GitHub（不含 releases/）────────────────────────
echo "[1/2] 推送到 GitHub (origin)..."
git push origin "$BRANCH"
echo "  GitHub 推送完成"

# ── 2. 推送到 GitLab（含 releases/）──────────────────────────
echo "[2/2] 推送到 GitLab (gitlab)..."

# 检查 releases/ 是否有内容需要同步
if [ -d "releases/rodski" ] && [ "$(ls -A releases/rodski 2>/dev/null)" ]; then
    # 创建临时提交包含 releases/
    echo "  同步 releases/ 到 GitLab..."

    # 保存当前状态
    STASH_NEEDED=false
    if ! git diff --quiet || ! git diff --cached --quiet; then
        git stash push -q -m "git_push temp stash"
        STASH_NEEDED=true
    fi

    # 强制添加 releases/ 并创建临时提交
    git add -f releases/
    if git diff --cached --quiet; then
        # releases/ 已经在 tracking 中，直接推送
        git push gitlab "$BRANCH"
    else
        # 有新的 releases/ 文件需要提交
        git commit -m "chore: sync releases/ to GitLab [skip ci]"
        git push gitlab "$BRANCH"
        # 回退这个临时提交（GitHub 不需要）
        git reset --soft HEAD~1
        git reset HEAD releases/
    fi

    # 恢复 stash
    if [ "$STASH_NEEDED" = true ]; then
        git stash pop -q
    fi
else
    # 没有 releases/，直接推送
    git push gitlab "$BRANCH"
fi

echo "  GitLab 推送完成"

# ── 推送 tags ─────────────────────────────────────────────────
echo ""
echo "同步 tags..."
git push origin --tags 2>/dev/null || true
git push gitlab --tags 2>/dev/null || true

echo ""
echo "=== 推送完成 ==="
echo "  GitHub (origin): $BRANCH (不含 releases/)"
echo "  GitLab (gitlab):  $BRANCH (含 releases/)"
