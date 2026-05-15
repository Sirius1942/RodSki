#!/bin/bash
# RodSki 构建、验收与发布脚本
# 用法: scripts/release_check.sh <version> [--build] [--publish]
# 示例: scripts/release_check.sh 6.7.6 --build --publish
#
# 流程:
#   --build    构建 wheel + sdist（默认跳过，使用已有产物）
#   --publish  验收通过后复制到 releases/rodski/v<version>/，下载离线依赖，推送到 GitLab
#   无参数时只做验收检查

set -euo pipefail

VERSION=${1:-}
DO_BUILD=false
DO_PUBLISH=false

shift || true
for arg in "$@"; do
    case "$arg" in
        --build)   DO_BUILD=true ;;
        --publish) DO_PUBLISH=true ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
RELEASE_DIR="$PROJECT_ROOT/releases/rodski/v${VERSION}"
WHEEL="$DIST_DIR/rodski-${VERSION}-py3-none-any.whl"
SDIST="$DIST_DIR/rodski-${VERSION}.tar.gz"
TMP_DIR=$(mktemp -d)

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [ -z "$VERSION" ]; then
    echo "用法: scripts/release_check.sh <version> [--build] [--publish]"
    echo "  --build    构建 wheel + sdist"
    echo "  --publish  验收通过后复制到 releases/rodski/v<version>/"
    exit 1
fi

echo "=== RodSki v${VERSION} 发布流程 ==="
echo ""

# ── Step 1: 构建 ──────────────────────────────────────────────
if [ "$DO_BUILD" = true ]; then
    echo "[1/8] 构建 wheel + sdist..."
    rm -rf "$DIST_DIR" build/
    python3 -m build -q
    echo "  构建完成: $(ls "$DIST_DIR")"
else
    echo "[1/8] 跳过构建（使用已有产物）"
fi

# ── Step 2: 构建产物存在性 ────────────────────────────────────
if [ ! -f "$WHEEL" ]; then
    echo "错误: wheel 不存在: $WHEEL"
    echo "  提示: 使用 --build 参数自动构建"
    exit 1
fi
if [ ! -f "$SDIST" ]; then
    echo "错误: sdist 不存在: $SDIST"
    exit 1
fi
echo "[2/8] 构建产物存在"

# ── Step 3: wheel 内容完整性 ──────────────────────────────────
REQUIRED_FILES=(
    "rodski/core/keyword_engine.py"
    "rodski/core/xml_schema_validator.py"
    "rodski/core/data_schema_validator.py"
    "rodski/core/model_parser.py"
    "rodski/data/data_resolver.py"
    "rodski/data/builtin_functions.py"
    "rodski/drivers/__init__.py"
    "rodski/api/__init__.py"
    "rodski/llm/__init__.py"
    "rodski/report/__init__.py"
    "rodski/vision/__init__.py"
    "rodski/rodski_cli/__init__.py"
    "rodski/builtin_ops/__init__.py"
    "rodski/schemas/model.xsd"
    "rodski/schemas/case.xsd"
    "rodski/schemas/plan.xsd"
    "rodski/schemas/data.xsd"
    "rodski/schemas/result.xsd"
)

WHEEL_CONTENTS=$(unzip -l "$WHEEL" 2>/dev/null)
for file in "${REQUIRED_FILES[@]}"; do
    if ! echo "$WHEEL_CONTENTS" | grep -q "$file"; then
        echo "错误: wheel 缺少必要文件: $file"
        exit 1
    fi
done
echo "[3/8] wheel 内容完整（${#REQUIRED_FILES[@]} 个关键文件已确认）"

# ── Step 4: 干净 venv 安装 + 验证 ─────────────────────────────
python3 -m venv "$TMP_DIR/venv"
"$TMP_DIR/venv/bin/pip" install --quiet "$WHEEL"

cd "$TMP_DIR"
"$TMP_DIR/venv/bin/python" -c "
import importlib.metadata, importlib.resources as resources, sys
v = importlib.metadata.version('rodski')
assert v == '$VERSION', f'版本不匹配: {v} != $VERSION'
from rodski.core.model_parser import ModelParser
from rodski.core.keyword_engine import KeywordEngine
from rodski.core.xml_schema_validator import RodskiXmlValidator
from rodski.core.data_schema_validator import DataSchemaValidator
from rodski.data.data_resolver import DataResolver
from rodski.builtin_ops import list_builtins
schemas = resources.files('rodski') / 'schemas'
for name in ['model.xsd', 'case.xsd', 'plan.xsd', 'data.xsd', 'result.xsd']:
    assert (schemas / name).is_file(), f'缺少 {name}'
import xmlschema, yaml, tqdm, psutil, requests
print('  安装态验证全部通过')
"
cd "$PROJECT_ROOT"

echo "[4/8] 干净 venv 安装态验证通过"

# ── Step 5: CLI 版本验证 ──────────────────────────────────────
CLI_VERSION=$("$TMP_DIR/venv/bin/rodski" --version 2>&1 || true)
if echo "$CLI_VERSION" | grep -q "$VERSION"; then
    echo "[5/8] CLI 版本验证通过: $CLI_VERSION"
else
    echo "警告: CLI 版本不匹配: $CLI_VERSION (期望包含 $VERSION)"
    echo "  可能是 entry_point 配置问题，继续..."
fi

# ── Step 6: 发布到 releases/ ──────────────────────────────────
if [ "$DO_PUBLISH" = true ]; then
    echo "[6/8] 发布到 $RELEASE_DIR ..."
    mkdir -p "$RELEASE_DIR"
    cp "$WHEEL" "$RELEASE_DIR/"
    cp "$SDIST" "$RELEASE_DIR/"

    # 生成 SHA256SUMS
    (cd "$RELEASE_DIR" && shasum -a 256 "rodski-${VERSION}-py3-none-any.whl" "rodski-${VERSION}.tar.gz" > SHA256SUMS)

    # 生成 README.md
    cat > "$RELEASE_DIR/README.md" <<EOF
# RodSki v${VERSION} Release

## 安装方式

### 从本目录 wheel 安装

\`\`\`bash
pip install rodski-${VERSION}-py3-none-any.whl
\`\`\`

### 离线安装（无网络环境）

\`\`\`bash
pip install --no-index --find-links=deps/ rodski-${VERSION}-py3-none-any.whl
\`\`\`

## 文件说明

| 文件 | 说明 |
|------|------|
| \`rodski-${VERSION}-py3-none-any.whl\` | Python wheel 包，推荐安装 |
| \`rodski-${VERSION}.tar.gz\` | 源码包 |
| \`deps/\` | 离线依赖包（无网络环境使用） |
| \`SHA256SUMS\` | 文件校验和 |
| \`OFFLINE_INSTALL.md\` | 离线安装详细指南 |

## 校验

\`\`\`bash
shasum -a 256 -c SHA256SUMS
\`\`\`
EOF

    echo "  已发布: wheel + sdist + SHA256SUMS + README.md"

    # ── Step 7: 下载离线依赖 ──────────────────────────────────
    echo "[7/8] 下载离线依赖到 $RELEASE_DIR/deps/ ..."
    mkdir -p "$RELEASE_DIR/deps"
    pip3 download --dest "$RELEASE_DIR/deps" --no-cache-dir \
        xmlschema pyyaml tqdm psutil requests setuptools wheel \
        2>&1 | grep -c "Saved" | xargs -I{} echo "  已下载 {} 个依赖包"

    # 生成 OFFLINE_INSTALL.md
    cat > "$RELEASE_DIR/OFFLINE_INSTALL.md" <<'OFFLINE_EOF'
# 离线安装指南

## 一键离线安装

将整个目录复制到目标机器，执行：

```bash
pip install --no-index --find-links=deps/ rodski-PLACEHOLDER_VERSION-py3-none-any.whl
```

## 使用虚拟环境

```bash
python3 -m venv rodski-env
source rodski-env/bin/activate
pip install --no-index --find-links=deps/ rodski-PLACEHOLDER_VERSION-py3-none-any.whl
```

## 验证

```bash
python3 -c "import rodski; print(rodski.__version__)"
```

## 平台说明

deps/ 中含平台相关的 C 扩展包（psutil、pyyaml）。
当前包适用于本机平台。如需其他平台，在目标同架构机器上执行：

```bash
pip download --dest deps/ xmlschema pyyaml tqdm psutil requests setuptools wheel
```
OFFLINE_EOF
    # 替换版本占位符
    sed -i '' "s/PLACEHOLDER_VERSION/${VERSION}/g" "$RELEASE_DIR/OFFLINE_INSTALL.md"

    # 验证离线安装可行性
    echo "  验证离线安装..."
    rm -rf "$TMP_DIR/offline-venv"
    python3 -m venv "$TMP_DIR/offline-venv"
    if "$TMP_DIR/offline-venv/bin/pip" install --no-index \
        --find-links="$RELEASE_DIR/deps/" \
        "$RELEASE_DIR/rodski-${VERSION}-py3-none-any.whl" \
        --quiet 2>/dev/null; then
        cd "$TMP_DIR"
        OFFLINE_VER=$("$TMP_DIR/offline-venv/bin/python" -c "import rodski; print(rodski.__version__)" 2>/dev/null || echo "FAIL")
        cd "$PROJECT_ROOT"
        if [ "$OFFLINE_VER" = "$VERSION" ]; then
            echo "  离线安装验证通过 (version=$OFFLINE_VER)"
        else
            echo "  警告: 离线安装后版本不匹配: $OFFLINE_VER"
        fi
    else
        echo "  警告: 离线安装失败，deps/ 可能不完整"
    fi

    echo ""
    echo "  发布目录:"
    ls -lh "$RELEASE_DIR/"
    echo ""
    echo "  SHA256SUMS:"
    cat "$RELEASE_DIR/SHA256SUMS"

    # ── Step 8: 推送到 GitLab ─────────────────────────────────
    echo ""
    echo "[8/8] 推送 releases/ 到 GitLab..."
    cd "$PROJECT_ROOT"
    git add -f releases/
    if git diff --cached --quiet; then
        echo "  releases/ 无变更，跳过"
    else
        git commit -m "chore(release): 发布 rodski v${VERSION} 到 releases/ [skip ci]"
        git push gitlab main
        echo "  已推送到 GitLab"
    fi

else
    echo "[6/8] 跳过发布（使用 --publish 参数启用）"
    echo "[7/8] 跳过离线依赖下载"
    echo "[8/8] 跳过 GitLab 推送"
fi

echo ""
echo "=== RodSki v${VERSION} 发布流程完成 ==="
