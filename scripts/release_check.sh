#!/bin/bash
# RodSki wheel 发布包验收脚本
# 用法: scripts/release_check.sh <version>
# 示例: scripts/release_check.sh 6.7.3

set -euo pipefail

VERSION=${1:-}
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RODSKI_DIR="$PROJECT_ROOT/rodski"
DIST_DIR="$RODSKI_DIR/dist"
WHEEL="$DIST_DIR/rodski-${VERSION}-py3-none-any.whl"
SDIST="$DIST_DIR/rodski-${VERSION}.tar.gz"
TMP_DIR=$(mktemp -d)

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [ -z "$VERSION" ]; then
    echo "用法: scripts/release_check.sh <version>"
    exit 1
fi

echo "=== RodSki v${VERSION} 发布包验收 ==="

# 1. 构建产物存在性
if [ ! -f "$WHEEL" ]; then
    echo "错误: wheel 不存在: $WHEEL"
    exit 1
fi
if [ ! -f "$SDIST" ]; then
    echo "错误: sdist 不存在: $SDIST"
    exit 1
fi

echo "[1/5] 构建产物存在"

# 2. wheel 内容完整性
REQUIRED_FILES=(
    "core/keyword_engine.py"
    "core/xml_schema_validator.py"
    "data/data_resolver.py"
    "data/builtin_functions.py"
    "drivers/__init__.py"
    "api/__init__.py"
    "llm/__init__.py"
    "report/__init__.py"
    "vision/__init__.py"
    "rodski_cli/__init__.py"
    "schemas/model.xsd"
    "schemas/case.xsd"
    "schemas/data.xsd"
    "schemas/result.xsd"
)

for file in "${REQUIRED_FILES[@]}"; do
    if ! python3 -m zipfile -l "$WHEEL" | grep -q "$file"; then
        echo "错误: wheel 缺少必要文件: $file"
        exit 1
    fi
done

echo "[2/5] wheel 内容完整"

# 3. 干净 venv 安装
python3 -m venv "$TMP_DIR/venv"
source "$TMP_DIR/venv/bin/activate"
pip install "$WHEEL" --quiet

echo "[3/5] 干净 venv 安装成功"

# 4. 安装态 import + schemas 校验
python - <<'PY'
import importlib

modules = [
    "core",
    "data",
    "drivers",
    "api",
    "llm",
    "report",
    "vision",
    "rodski_cli",
]
for module in modules:
    importlib.import_module(module)

from core.xml_schema_validator import schemas_directory
schema_dir = schemas_directory()
assert schema_dir.exists(), f"schemas 目录不存在: {schema_dir}"
for name in ["model.xsd", "case.xsd", "data.xsd", "result.xsd"]:
    assert (schema_dir / name).exists(), f"缺少 XSD: {name}"

from data.builtin_functions import call_function
assert call_function("random", ["int", "4"]).isdigit()

from data.data_resolver import DataResolver
resolved = DataResolver().resolve_with_return("user_${random(int, 4)}")
assert resolved.startswith("user_"), resolved
assert resolved[5:].isdigit(), resolved

print("install imports ok")
PY

echo "[4/5] 安装态模块和 schemas 验证通过"

# 5. CLI 验证
rodski --version | grep -q "$VERSION"

echo "[5/5] CLI 验证通过"

deactivate

echo "=== RodSki v${VERSION} 发布包验收通过 ==="
