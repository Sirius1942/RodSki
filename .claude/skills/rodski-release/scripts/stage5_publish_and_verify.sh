#!/usr/bin/env bash
# stage5_publish_and_verify.sh — 阶段 5：上传 PyPI + push git + 核验
#
# 用法: stage5_publish_and_verify.sh <VERSION>
#
# 职责:
#   1. twine upload 到 PyPI（使用 ~/.pypirc）
#   2. 轮询 PyPI API 确认包真实可访问（最多等 120s）
#   3. push main 分支 + tag 到 origin（GitHub）
#   4. push main 分支 + tag 到 gitlab（如果 remote 存在）
#   5. 最终核验：git remote 上 tag 存在 + PyPI 版本正确
#
# 失败回滚:
#   - PyPI 上传失败 → 不 push git，运行 rollback_tag.sh 撤 tag
#   - git push 失败 → PyPI 已上传无法撤回，但 tag 可重新 push

set -euo pipefail
source "$(dirname "$0")/_common.sh"

VERSION=$(require_version "${1:-}")
cd "$PROJECT_ROOT"

info "═══════════════════════════════════════════════════════════"
info " Stage 5: 上传 PyPI + push git + 核验 (v${VERSION})"
info "═══════════════════════════════════════════════════════════"

require_stage stage4 "$VERSION"

WHEEL="$DIST_DIR/rodski-${VERSION}-py3-none-any.whl"
SDIST="$DIST_DIR/rodski-${VERSION}.tar.gz"
[[ -f "$WHEEL" ]] || fail "wheel 不存在: $WHEEL"
[[ -f "$SDIST" ]] || fail "sdist 不存在: $SDIST"

info "[1/5] 上传到 PyPI..."
python3 -m twine upload "$WHEEL" "$SDIST" \
    || fail "PyPI 上传失败。tag 尚未 push，可运行 rollback_tag.sh ${VERSION} 撤销。"
ok "  twine upload 完成"

info "[2/5] 等待 PyPI 索引更新（最多 120s）..."
MAX_WAIT=120
INTERVAL=10
ELAPSED=0
while true; do
    if check_pypi_exists "$VERSION"; then
        ok "  PyPI 已可访问 rodski ${VERSION} (等待 ${ELAPSED}s)"
        break
    fi
    if [[ $ELAPSED -ge $MAX_WAIT ]]; then
        warn "  PyPI 120s 内未索引，可能延迟。请稍后手动确认: https://pypi.org/project/rodski/${VERSION}/"
        break
    fi
    info "  等待 PyPI 索引... (${ELAPSED}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

info "[3/5] push main + tag 到所有 git remote..."
# 遍历所有 remote 全部推，避免 origin/github/gitlab 命名混乱导致漏推
PUSH_FAILED=()
PUSH_OK=()
for remote in $(git remote); do
    info "  → push $remote ..."
    if git push "$remote" main --tags 2>&1 | tail -3; then
        ok "  ✓ $remote push 完成"
        PUSH_OK+=("$remote")
    else
        warn "  ✗ $remote push 失败"
        PUSH_FAILED+=("$remote")
    fi
done
if [[ ${#PUSH_OK[@]} -eq 0 ]]; then
    fail "所有 remote push 均失败。PyPI 已上传成功，请手动 push。"
fi
if [[ ${#PUSH_FAILED[@]} -gt 0 ]]; then
    warn "  以下 remote 推送失败，需要手动处理: ${PUSH_FAILED[*]}"
    warn "  常见原因: GitHub token 失效 (gh auth login)、GitLab SSH key 过期"
fi

info "[4/5] 跳过（合并入 3/5）"

info "[5/5] 最终核验..."
ERRORS=0

# 核验 PyPI
if check_pypi_exists "$VERSION"; then
    ok "  ✓ PyPI: https://pypi.org/project/rodski/${VERSION}/"
else
    warn "  ✗ PyPI 上暂未找到 rodski ${VERSION}（可能仍在索引中）"
    ERRORS=$((ERRORS + 1))
fi

# 核验所有 remote 上的 tag
for remote in $(git remote); do
    REMOTE_TAG=$(git ls-remote --tags "$remote" "refs/tags/v${VERSION}" 2>/dev/null | head -1)
    if [[ -n "$REMOTE_TAG" ]]; then
        ok "  ✓ $remote 上 tag v${VERSION} 已存在"
    else
        warn "  ✗ $remote 上未找到 tag v${VERSION}"
        ERRORS=$((ERRORS + 1))
    fi
done

# 清理状态文件（发布完成）
rm -f "$STATE_FILE"

if [[ $ERRORS -gt 0 ]]; then
    warn "发布完成，但有 $ERRORS 项核验警告，请手动确认。"
else
    ok "═══════════════════════════════════════════════════════════"
    ok " Stage 5 完成 — v${VERSION} 发布成功！"
    ok "═══════════════════════════════════════════════════════════"
    echo
    ok "  PyPI:   https://pypi.org/project/rodski/${VERSION}/"
    ok "  GitHub: https://github.com/Sirius1942/RodSki/releases/tag/v${VERSION}"
fi
