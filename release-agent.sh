#!/bin/bash
# rodski-agent 发布脚本
# 用法: ./release-agent.sh <version>
# 示例: ./release-agent.sh 2.3.0
# 版本号独立于 rodski，tag 格式: agent-v2.3.0

set -e

VERSION=$1
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$PROJECT_ROOT/rodski-agent"

if [ -z "$VERSION" ]; then
    echo "用法: ./release-agent.sh <version>"
    echo "示例: ./release-agent.sh 2.3.0"
    exit 1
fi

echo "=== rodski-agent v${VERSION} 发布流程 ==="

# 1. 确保在 main 分支，不在则合并
echo "[1/9] 切换到 main 分支..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
MERGED=false
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "  当前在 ${CURRENT_BRANCH}，合并到 main..."
    git checkout main
    git merge "$CURRENT_BRANCH" --no-ff -m "Merge ${CURRENT_BRANCH}: release rodski-agent v${VERSION}"
    MERGED=true
fi
echo "  ✓ 当前在 main 分支"

# 2. 合并未合并的 agent 功能分支
echo "[2/9] 合并 rodski-agent 功能分支..."
UNMERGED=$(git branch --no-merged main | grep -E "feature/.*agent" || true)
if [ -n "$UNMERGED" ]; then
    for branch in $UNMERGED; do
        echo "  合并 ${branch}..."
        git merge "$branch" --no-ff -m "Merge ${branch}: release rodski-agent v${VERSION}"
        MERGED=true
    done
fi
echo "  ✓ 所有功能分支已合并"

# 合并后跑全量测试
if [ "$MERGED" = true ]; then
    echo "  [!] 检测到合并动作，执行合并后全量测试..."
    cd "$AGENT_DIR"
    python3 -m pytest tests/unit/ -q
    cd "$PROJECT_ROOT"
    echo "  ✓ 合并后全量测试通过"
fi

# 3. 检查 tag 是否已存在
echo "[3/9] 检查 tag 是否冲突..."
TAG_NAME="agent-v${VERSION}"
if git tag -l "$TAG_NAME" | grep -q "$TAG_NAME"; then
    echo "错误: tag ${TAG_NAME} 已存在，不能重复发布"
    exit 1
fi
echo "  ✓ tag ${TAG_NAME} 不存在"

# 4. 检查 PyPI 是否已有该版本
echo "[4/9] 检查 PyPI 版本冲突..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rodski-agent/${VERSION}/json")
if [ "$HTTP_CODE" = "200" ]; then
    echo "错误: PyPI 上已存在 rodski-agent ${VERSION}"
    exit 1
fi
echo "  ✓ PyPI 上无 rodski-agent ${VERSION}"

# 5. 检查工作区干净
echo "[5/9] 检查工作区状态..."
if [ -n "$(git status --porcelain rodski-agent/)" ]; then
    echo "错误: rodski-agent/ 目录有未提交的更改"
    git status --short rodski-agent/
    exit 1
fi
echo "  ✓ 工作区干净"

# 6. 更新版本号 + 运行测试
echo "[6/9] 更新版本号为 ${VERSION}..."
sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" "$AGENT_DIR/pyproject.toml"

echo "  运行单元测试..."
cd "$AGENT_DIR"
python3 -m pytest tests/unit/ -q
cd "$PROJECT_ROOT"
echo "  ✓ 测试全部通过"

# 7. 提交 + 打 tag
echo "[7/9] 提交版本号变更并打 tag..."
git add "$AGENT_DIR/pyproject.toml"
git commit -m "chore(rodski-agent/v${VERSION}): 版本号更新到 ${VERSION}"
git tag -a "$TAG_NAME" -m "rodski-agent v${VERSION}"
echo "  ✓ 已提交并创建 tag ${TAG_NAME}"

# 8. 构建 + 发布 PyPI
echo "[8/9] 构建并发布到 PyPI..."
rm -rf "$AGENT_DIR/dist/"
python3 -m build "$AGENT_DIR/"
python3 -m twine upload "$AGENT_DIR/dist/rodski_agent-${VERSION}"*
echo "  ✓ 已发布到 PyPI"

# 9. 推送远端
echo "[9/9] 推送到 GitHub 和 GitLab..."
git push origin main --tags
git push gitlab main --tags
echo "  ✓ 已推送到 GitHub 和 GitLab"

echo ""
echo "=== rodski-agent v${VERSION} 发布完成 ==="
echo "  PyPI:   https://pypi.org/project/rodski-agent/${VERSION}/"
echo "  GitHub: https://github.com/Sirius1942/RodSki/releases/tag/${TAG_NAME}"
echo "  GitLab: https://gitlab.casstime.net/qa/TestArchitecture/rodski/-/tags/${TAG_NAME}"
