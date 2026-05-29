#!/bin/bash
# RodSki 发布脚本（遗留入口，已重构为 5 阶段 skill）
#
# 推荐使用新的 skill 流程：
#   .claude/skills/rodski-release/scripts/stage1_merge_to_main.sh <VERSION>
#   .claude/skills/rodski-release/scripts/stage2_acceptance.sh <VERSION>
#   .claude/skills/rodski-release/scripts/stage3_build_and_tag.sh <VERSION>
#   .claude/skills/rodski-release/scripts/stage4_clean_verify.sh <VERSION>
#   .claude/skills/rodski-release/scripts/stage5_publish_and_verify.sh <VERSION>
#
# 本脚本保留用于 Wiki 发布功能（stage5 不含 Wiki）。
# 直接调用时会委托给 skill 脚本完成发布，然后追加 Wiki 发布。
#
# 用法: ./release.sh <version>
# 示例: ./release.sh 7.2.0

set -euo pipefail

VERSION="${1:-}"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$PROJECT_ROOT/.claude/skills/rodski-release/scripts"

if [ -z "$VERSION" ]; then
    echo "用法: ./release.sh <version>"
    echo "示例: ./release.sh 7.2.0"
    echo ""
    echo "推荐使用分阶段 skill 流程（可单独重跑某阶段）："
    echo "  $SKILL_DIR/stage1_merge_to_main.sh <VERSION>"
    echo "  $SKILL_DIR/stage2_acceptance.sh <VERSION>"
    echo "  $SKILL_DIR/stage3_build_and_tag.sh <VERSION>"
    echo "  $SKILL_DIR/stage4_clean_verify.sh <VERSION>"
    echo "  $SKILL_DIR/stage5_publish_and_verify.sh <VERSION>"
    exit 1
fi

# ── Wiki 发布函数（保留原有逻辑）────────────────────────────────────────────
RODSKI_DIR="$PROJECT_ROOT/rodski"

WIKI_DOCS=(
    "rodski/docs/TEST_CASE_WRITING_GUIDE.md|RodSki 用例编写指南"
    "rodski/docs/SKILL_REFERENCE.md|RodSki Skill 参考文档"
    "rodski-agent/docs/USER_GUIDE.md|rodski-agent 用户使用指南"
)

prepend_version_banner() {
    local src="$1" dest="$2"
    printf '> **文档版本**: 对应 RodSki v%s | 发布日期: %s\n\n' "$VERSION" "$(date +%Y-%m-%d)" > "$dest"
    cat "$src" >> "$dest"
}

publish_gitlab_wiki() {
    local WIKI_REPO="https://gitlab.casstime.net/qa/TestArchitecture/rodski.wiki.git"
    local WIKI_TMP
    WIKI_TMP=$(mktemp -d)

    echo "  [GitLab Wiki] 克隆 wiki 仓库..."
    git clone --depth 1 "$WIKI_REPO" "$WIKI_TMP" 2>/dev/null || {
        echo "  ⚠ GitLab Wiki 克隆失败"; rm -rf "$WIKI_TMP"; return 1
    }

    for entry in "${WIKI_DOCS[@]}"; do
        local src="${entry%%|*}" title="${entry##*|}"
        local src_path="$PROJECT_ROOT/$src"
        [ -f "$src_path" ] || continue
        prepend_version_banner "$src_path" "$WIKI_TMP/${title}.md"
        echo "  [GitLab Wiki] 更新: $title"
    done

    cd "$WIKI_TMP"
    git add -A
    if ! git diff --cached --quiet; then
        git commit -m "docs: 更新文档 v${VERSION}" >/dev/null
        git push origin master
        echo "  [GitLab Wiki] ✓ 已推送"
    else
        echo "  [GitLab Wiki] 无变更，跳过"
    fi
    cd "$PROJECT_ROOT"
    rm -rf "$WIKI_TMP"
}

publish_github_wiki() {
    echo "  [GitHub Wiki] 跳过 — 尚未启用"
}

publish_casstime_wiki() {
    if ! command -v jq &>/dev/null; then
        echo "  ⚠ [Casstime Wiki] 需要 jq，跳过"; return 1
    fi
    if [ -z "${WIKI_EMPLOYEE_ID:-}" ] || [ -z "${WIKI_PASSWORD:-}" ]; then
        echo "  ⚠ [Casstime Wiki] 缺少 WIKI_EMPLOYEE_ID/WIKI_PASSWORD，跳过"; return 1
    fi

    local TOKEN
    TOKEN=$(curl -sf -X POST "https://wiki.casstime.com/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"employee_id\":\"$WIKI_EMPLOYEE_ID\",\"password\":\"$WIKI_PASSWORD\"}" \
        | jq -r '.access_token // empty')
    if [ -z "$TOKEN" ]; then
        echo "  ⚠ [Casstime Wiki] 登录失败"; return 1
    fi

    local SPACE_ID="e50d0785-d3bd-4266-a37c-f762db5db3a3"
    local ARTICLES
    ARTICLES=$(curl -sf "http://wiki.casstime.com/api/v1/articles/?space_id=$SPACE_ID" \
        -H "Authorization: Bearer $TOKEN")

    for entry in "${WIKI_DOCS[@]}"; do
        local src="${entry%%|*}" title="${entry##*|}"
        local src_path="$PROJECT_ROOT/$src"
        [ -f "$src_path" ] || continue

        local CONTENT
        CONTENT=$(jq -Rs . < "$src_path")
        local EXISTING_ID
        EXISTING_ID=$(echo "$ARTICLES" | jq -r --arg prefix "$title" \
            '[.[] | select(.title | startswith($prefix))] | .[0].id // empty')

        if [ -n "$EXISTING_ID" ]; then
            curl -sf -X PUT "http://wiki.casstime.com/api/v1/articles/${EXISTING_ID}/" \
                -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                -d "{\"title\":\"${title} (v${VERSION})\",\"content\":$CONTENT,\"status\":\"published\"}" \
                >/dev/null
            echo "  [Casstime Wiki] 更新: $title"
        else
            local NEW_ID
            NEW_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
            curl -sf -X POST "http://wiki.casstime.com/api/v1/articles/" \
                -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
                -d "{\"id\":\"$NEW_ID\",\"title\":\"${title} (v${VERSION})\",\"content\":$CONTENT,\"space_id\":\"$SPACE_ID\",\"status\":\"published\"}" \
                >/dev/null
            echo "  [Casstime Wiki] 创建: $title"
        fi
    done
    echo "  [Casstime Wiki] ✓ 完成"
}

publish_wikis() {
    publish_gitlab_wiki || echo "  ⚠ GitLab Wiki 发布失败"
    publish_github_wiki || true
    publish_casstime_wiki || echo "  ⚠ Casstime Wiki 发布失败"
}

# ── 委托给 skill 脚本执行 5 阶段发布 ─────────────────────────────────────────
echo "=== RodSki v${VERSION} 发布流程（委托 skill 脚本）==="
echo ""

for stage in stage1_merge_to_main stage2_acceptance stage3_build_and_tag stage4_clean_verify stage5_publish_and_verify; do
    script="$SKILL_DIR/${stage}.sh"
    if [ ! -f "$script" ]; then
        echo "错误: skill 脚本不存在: $script"
        exit 1
    fi
    bash "$script" "$VERSION"
    echo ""
done

# ── Wiki 发布（stage5 之后）──────────────────────────────────────────────────
echo "[Wiki] 发布用户文档到 Wiki..."
publish_wikis || echo "  ⚠ Wiki 发布出现问题，但不影响发布结果"
echo "  ✓ Wiki 发布步骤完成"

echo ""
echo "=== v${VERSION} 发布完成 ==="
echo "  PyPI:   https://pypi.org/project/rodski/${VERSION}/"
echo "  GitHub: https://github.com/Sirius1942/RodSki/releases/tag/v${VERSION}"
echo "  GitLab: https://gitlab.casstime.net/qa/TestArchitecture/rodski/-/tags/v${VERSION}"
