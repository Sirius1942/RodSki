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

echo "=== RodSki v${VERSION} 发布流程 ==="

# 1. 确保在 main 分支
echo "[1/10] 切换到 main 分支..."
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
echo "[2/10] 合并 v${VERSION} 功能分支..."
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
echo "[3/10] 检查 tag 是否冲突..."
if git tag -l "v${VERSION}" | grep -q "v${VERSION}"; then
    echo "错误: tag v${VERSION} 已存在，不能重复发布"
    echo "  已有 tags: $(git tag -l 'v6.*' | tail -5 | tr '\n' ' ')"
    exit 1
fi
echo "  ✓ tag v${VERSION} 不存在，可以创建"

# 4. 检查 PyPI 是否已有该版本
echo "[4/10] 检查 PyPI 版本冲突..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rodski/${VERSION}/json")
if [ "$HTTP_CODE" = "200" ]; then
    echo "错误: PyPI 上已存在 rodski ${VERSION}，不能重复发布"
    exit 1
fi
echo "  ✓ PyPI 上无 rodski ${VERSION}"

# 5. 检查工作区干净
echo "[5/10] 检查工作区状态..."
if [ -n "$(git status --porcelain rodski/)" ]; then
    echo "错误: rodski/ 目录有未提交的更改，请先提交或暂存"
    git status --short rodski/
    exit 1
fi
echo "  ✓ 工作区干净"

# 6. 更新版本号
echo "[6/10] 更新版本号为 ${VERSION}..."
sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" "$RODSKI_DIR/pyproject.toml"

# 7. 运行测试
echo "[7/10] 运行单元测试..."
cd "$RODSKI_DIR"
python3 -m pytest tests/unit/ -q
cd "$PROJECT_ROOT"
echo "  ✓ 单元测试全部通过"

echo "  运行 rodski-demo 验收测试..."
python3 rodski/ski_run.py rodski-demo/DEMO/demo_full/case/demo_case.xml --headless
echo "  ✓ rodski-demo 验收测试通过"

# 8. 提交 + 打 tag
echo "[8/10] 提交版本号变更并打 tag..."
git add "$RODSKI_DIR/pyproject.toml"
git commit -m "chore(v${VERSION}): 版本号更新到 ${VERSION}"
git tag -a "v${VERSION}" -m "v${VERSION}"
echo "  ✓ 已提交并创建 tag v${VERSION}"

# 9. 构建 + 发布包验收 + 发布 PyPI
echo "[9/10] 构建、验收并发布到 PyPI..."
rm -rf "$RODSKI_DIR/dist/"
python3 -m build "$RODSKI_DIR/"
"$PROJECT_ROOT/scripts/release_check.sh" "$VERSION"
python3 -m twine upload "$RODSKI_DIR/dist/rodski-${VERSION}"*
echo "  ✓ 已通过发布包验收并发布到 PyPI"

# 10. 推送远端
echo "[10/10] 推送到 GitHub 和 GitLab..."
git push origin main --tags
git push gitlab main --tags
echo "  ✓ 已推送到 GitHub 和 GitLab"

echo ""
echo "=== v${VERSION} 发布完成 ==="
echo "  PyPI:   https://pypi.org/project/rodski/${VERSION}/"
echo "  GitHub: https://github.com/Sirius1942/RodSki/releases/tag/v${VERSION}"
echo "  GitLab: https://gitlab.casstime.net/qa/TestArchitecture/rodski/-/tags/v${VERSION}"
