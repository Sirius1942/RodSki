#!/bin/bash
# RodSki 发布脚本
# 用法: ./release.sh <version>
# 示例: ./release.sh 6.8.0

set -e

VERSION=$1
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
RODSKI_DIR="$PROJECT_ROOT/rodski"

if [ -z "$VERSION" ]; then
    echo "用法: ./release.sh <version>"
    echo "示例: ./release.sh 6.8.0"
    exit 1
fi

# ── Wiki 发布函数 ─────────────────────────────────────────────

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
    # TODO: 启用后克隆 https://github.com/Sirius1942/RodSki.wiki.git 并按 GitLab 相同模式操作
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

echo "=== RodSki v${VERSION} 发布流程 ==="

# 1. 确保在 main 分支
echo "[1/11] 切换到 main 分支..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
MERGED=false
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "  当前在 ${CURRENT_BRANCH}，合并到 main..."
    git checkout main
    git merge "$CURRENT_BRANCH" --no-ff -m "Merge ${CURRENT_BRANCH}: release v${VERSION}"
    MERGED=true
fi
echo "  ✓ 当前在 main 分支"

# 2. 合并未合并的功能分支
echo "[2/11] 合并 v${VERSION} 功能分支..."
UNMERGED=$(git branch --no-merged main | grep "feature/v${VERSION}" || true)
if [ -n "$UNMERGED" ]; then
    for branch in $UNMERGED; do
        echo "  合并 ${branch}..."
        git merge "$branch" --no-ff -m "Merge ${branch}: release v${VERSION}"
        MERGED=true
    done
fi
echo "  ✓ 所有 v${VERSION} 功能分支已合并"

# 如果有合并动作，先跑全量测试确保合并后代码正确
if [ "$MERGED" = true ]; then
    echo "  [!] 检测到合并动作，执行合并后全量测试..."
    cd "$RODSKI_DIR"
    python3 -m pytest tests/unit/ -q
    cd "$PROJECT_ROOT"
    python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml --headless
    echo "  ✓ 合并后全量测试通过（单元测试 + rodski-demo）"
fi

# 3. 检查 tag 是否已存在
echo "[3/11] 检查 tag 是否冲突..."
if git tag -l "v${VERSION}" | grep -q "v${VERSION}"; then
    echo "错误: tag v${VERSION} 已存在，不能重复发布"
    echo "  已有 tags: $(git tag -l 'v6.*' | tail -5 | tr '\n' ' ')"
    exit 1
fi
echo "  ✓ tag v${VERSION} 不存在，可以创建"

# 4. 检查 PyPI 是否已有该版本
echo "[4/11] 检查 PyPI 版本冲突..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rodski/${VERSION}/json")
if [ "$HTTP_CODE" = "200" ]; then
    echo "错误: PyPI 上已存在 rodski ${VERSION}，不能重复发布"
    exit 1
fi
echo "  ✓ PyPI 上无 rodski ${VERSION}"

# 5. 检查工作区干净
echo "[5/11] 检查工作区状态..."
if [ -n "$(git status --porcelain rodski/)" ]; then
    echo "错误: rodski/ 目录有未提交的更改，请先提交或暂存"
    git status --short rodski/
    exit 1
fi
echo "  ✓ 工作区干净"

# 6. 更新版本号
echo "[6/11] 更新版本号为 ${VERSION}..."
sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" "$RODSKI_DIR/pyproject.toml"

# 7. 运行测试
echo "[7/11] 运行单元测试..."
cd "$RODSKI_DIR"
python3 -m pytest tests/unit/ -q
cd "$PROJECT_ROOT"
echo "  ✓ 单元测试全部通过"

echo "  运行 rodski-demo 验收测试..."
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml --headless
echo "  ✓ rodski-demo 验收测试通过"

# 8. 提交 + 打 tag
echo "[8/11] 提交版本号变更并打 tag..."
git add "$RODSKI_DIR/pyproject.toml"
git commit -m "chore(v${VERSION}): 版本号更新到 ${VERSION}"
git tag -a "v${VERSION}" -m "v${VERSION}"
echo "  ✓ 已提交并创建 tag v${VERSION}"

# 9. 构建 + 发布包验收 + 发布 PyPI
echo "[9/11] 构建、验收并发布到 PyPI..."
rm -rf "$RODSKI_DIR/dist/"
python3 -m build "$RODSKI_DIR/"
"$PROJECT_ROOT/scripts/release_check.sh" "$VERSION"
python3 -m twine upload "$RODSKI_DIR/dist/rodski-${VERSION}"*
echo "  ✓ 已通过发布包验收并发布到 PyPI"

# 10. 发布用户文档到 Wiki
echo "[10/11] 发布用户文档到 Wiki..."
publish_wikis || echo "  ⚠ Wiki 发布出现问题，但不影响发布流程"
echo "  ✓ Wiki 发布步骤完成"

# 11. 推送远端
echo "[11/11] 推送到 GitHub 和 GitLab..."
git push origin main --tags
git push gitlab main --tags
echo "  ✓ 已推送到 GitHub 和 GitLab"

echo ""
echo "=== v${VERSION} 发布完成 ==="
echo "  PyPI:   https://pypi.org/project/rodski/${VERSION}/"
echo "  GitHub: https://github.com/Sirius1942/RodSki/releases/tag/v${VERSION}"
echo "  GitLab: https://gitlab.casstime.net/qa/TestArchitecture/rodski/-/tags/v${VERSION}"
