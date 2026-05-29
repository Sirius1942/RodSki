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

info "[3/5] push main + tag 到 origin (GitHub)..."
git push origin main --tags \
    || fail "push origin 失败。PyPI 已上传成功，请手动 push: git push origin main --tags"
ok "  origin push 完成"

info "[4/5] push main + tag 到 gitlab（如果 remote 存在）..."
if git remote | grep -q "^gitlab$"; then
    git push gitlab main --tags \
        || warn "  push gitlab 失败，请手动 push: git push gitlab main --tags"
    ok "  gitlab push 完成"
else
    info "  无 gitlab remote，跳过"
fi

info "[5/5] 最终核验..."
ERRORS=0

# 核验 PyPI
if check_pypi_exists "$VERSION"; then
    ok "  ✓ PyPI: https://pypi.org/project/rodski/${VERSION}/"
else
    warn "  ✗ PyPI 上暂未找到 rodski ${VERSION}（可能仍在索引中）"
    ERRORS=$((ERRORS + 1))
fi

# 核验 GitHub tag
REMOTE_TAG=$(git ls-remote --tags origin "refs/tags/v${VERSION}" 2>/dev/null | head -1)
if [[ -n "$REMOTE_TAG" ]]; then
    ok "  ✓ GitHub tag v${VERSION} 已存在"
else
    warn "  ✗ GitHub tag v${VERSION} 未找到"
    ERRORS=$((ERRORS + 1))
fi

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
