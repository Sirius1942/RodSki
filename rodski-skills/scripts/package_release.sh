#!/usr/bin/env bash
# package_release.sh — 把 rodski-skills/ 打成 dist/rodski-skills-vX.Y.Z.zip
#
# 用法: package_release.sh <VERSION>
#
# 产物只包含对外发行内容：rodski-test-guide/, README.md, VERSION
# 不包含 scripts/、.* 隐藏文件

set -euo pipefail

VERSION="${1:-}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || { echo "[FAIL] 版本号格式错误: '$VERSION'，需要 X.Y.Z" >&2; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
ZIP_NAME="rodski-skills-v${VERSION}.zip"
ZIP_PATH="$DIST_DIR/$ZIP_NAME"

[[ -d "$PROJECT_ROOT/rodski-skills/rodski-test-guide" ]] \
    || { echo "[FAIL] 未找到 rodski-skills/rodski-test-guide/，请先运行 sync_test_guide.sh" >&2; exit 1; }

mkdir -p "$DIST_DIR"
rm -f "$ZIP_PATH"

cd "$PROJECT_ROOT"
zip -rq "$ZIP_PATH" rodski-skills/ \
    -x 'rodski-skills/scripts/*' \
    -x 'rodski-skills/.*' \
    -x 'rodski-skills/**/.*'

[[ -f "$ZIP_PATH" ]] || { echo "[FAIL] 打包失败: $ZIP_PATH" >&2; exit 1; }

SIZE=$(du -h "$ZIP_PATH" | awk '{print $1}')
SHA=$(shasum -a 256 "$ZIP_PATH" | awk '{print $1}')

echo "[OK] 已生成 $ZIP_NAME ($SIZE)"
echo "     sha256: $SHA"
echo "     path:   $ZIP_PATH"
