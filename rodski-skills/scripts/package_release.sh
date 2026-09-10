#!/usr/bin/env bash
# package_release.sh — 把 rodski-skills/ 打成 dist/rodski-skills-vX.Y.Z.zip
#
# 用法: package_release.sh <VERSION>
#
# 产物只包含对外发行内容：rodski-skills/ 下的 skill 目录、README.md、VERSION
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

# 用 find -type f 收集文件列表再 zip -@，而不是 `zip -r` 直接递归：
# rodski-skills/ 下存在形如 rodski-skill--x/rodski-skill--x -> 自身 的 self-referential
# symlink（clawhub 安装遗留的本地工作区产物）。`zip -r` 会跟随 symlink 无限递归，
# 打出深度嵌套的重复目录树并把发行包撑大；`find -type f` 默认不跟随 symlink，
# 因此既排除 symlink 本身，也排除其指向的内容重复入包。
# 同时排除 scripts/（维护脚本，不对外）与隐藏文件/目录。
find rodski-skills -type f \
    -not -path 'rodski-skills/scripts/*' \
    -not -path '*/.*' \
    -print | zip -q "$ZIP_PATH" -@

[[ -s "$ZIP_PATH" ]] || { echo "[FAIL] 打包失败: $ZIP_PATH" >&2; exit 1; }

# 校验：发行包里不应出现 self-referential symlink 造成的深嵌套路径
DEEPEST=$(unzip -Z1 "$ZIP_PATH" | awk -F/ '{print NF}' | sort -rn | head -1)
if [[ "${DEEPEST:-0}" -gt 4 ]]; then
    echo "[WARN] 发行包中存在异常深层路径（最大层级 ${DEEPEST}），请检查 rodski-skills/ 是否残留 symlink：" >&2
    unzip -Z1 "$ZIP_PATH" | awk -F/ 'NF>4' | head -3 >&2
fi

SIZE=$(du -h "$ZIP_PATH" | awk '{print $1}')
SHA=$(shasum -a 256 "$ZIP_PATH" | awk '{print $1}')

echo "[OK] 已生成 $ZIP_NAME ($SIZE)"
echo "     sha256: $SHA"
echo "     path:   $ZIP_PATH"
