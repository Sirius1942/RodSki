#!/usr/bin/env bash
# _common.sh — rodski-release skill 共享函数库
# 所有 stage 脚本 source 此文件

set -euo pipefail

# ── 颜色输出 ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $*" >&2; exit 1; }

# ── 项目根目录 ────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
RODSKI_DIR="$PROJECT_ROOT/rodski"
DIST_DIR="$PROJECT_ROOT/dist"
STATE_FILE="$PROJECT_ROOT/.release_state"

# ── 版本号校验 ────────────────────────────────────────────────────────────────
require_version() {
    local v="${1:-}"
    [[ "$v" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "版本号格式错误: '$v'，需要 X.Y.Z"
    echo "$v"
}

# ── 状态机 ───────────────────────────────────────────────────────────────────
# 每个 stage 完成后写入状态，防止跳步执行
write_state() {
    local stage="$1" version="$2"
    echo "stage=$stage version=$version ts=$(date +%Y%m%d_%H%M%S)" > "$STATE_FILE"
    info "状态已记录: stage=$stage version=$version"
}

read_state() {
    [[ -f "$STATE_FILE" ]] || return 1
    source "$STATE_FILE"
}

require_stage() {
    local required="$1" version="$2"
    if ! read_state; then
        fail "未找到发布状态文件 (.release_state)。请从 stage1 开始执行。"
    fi
    # shellcheck disable=SC2154
    [[ "$stage" == "$required" ]] || fail "当前状态 stage=$stage，需要先完成 $required 才能继续。"
    [[ "$version" == "$version" ]] || fail "版本号不匹配：状态文件 $version，当前 $version"
}

# ── 版本号同步（所有需要写版本号的文件）────────────────────────────────────────
bump_all_versions() {
    local v="$1"
    info "同步版本号到 $v ..."

    # 1. 根 pyproject.toml
    sed -i '' "s/^version = \".*\"/version = \"${v}\"/" "$PROJECT_ROOT/pyproject.toml"
    ok "  根 pyproject.toml → $v"

    # 2. rodski/pyproject.toml（dev install 用）
    sed -i '' "s/^version = \".*\"/version = \"${v}\"/" "$RODSKI_DIR/pyproject.toml"
    ok "  rodski/pyproject.toml → $v"

    # 3. rodski/__init__.py
    sed -i '' "s/^__version__ = \".*\"/__version__ = \"${v}\"/" "$RODSKI_DIR/__init__.py"
    ok "  rodski/__init__.py → $v"

    # 4. CLAUDE.md（项目版本标注行）
    sed -i '' "s/当前版本：v[0-9.]\+/当前版本：v${v}/" "$PROJECT_ROOT/CLAUDE.md"
    ok "  CLAUDE.md → $v"

    # 5. 核心文档版本行（版本: vX.Y.Z 格式）
    for doc in \
        "$RODSKI_DIR/docs/TEST_CASE_WRITING_GUIDE.md" \
        "$RODSKI_DIR/docs/CORE_DESIGN_CONSTRAINTS.md" \
        "$RODSKI_DIR/docs/ARCHITECTURE.md" \
        "$RODSKI_DIR/docs/API_REFERENCE.md"; do
        [[ -f "$doc" ]] || continue
        sed -i '' "s/版本.*v[0-9.]\+/版本: v${v}/" "$doc"
        ok "  $(basename "$doc") → $v"
    done

    # 6. rodski-skills/ 版本号（与发布版本对齐）
    if [[ -f "$PROJECT_ROOT/rodski-skills/VERSION" ]]; then
        echo "$v" > "$PROJECT_ROOT/rodski-skills/VERSION"
        ok "  rodski-skills/VERSION → $v"
    fi
    if [[ -f "$PROJECT_ROOT/rodski-skills/rodski-test-guide/SKILL.md" ]]; then
        sed -i '' "s/^version: [0-9][0-9.]*$/version: ${v}/" \
            "$PROJECT_ROOT/rodski-skills/rodski-test-guide/SKILL.md"
        ok "  rodski-skills/rodski-test-guide/SKILL.md → $v"
    fi
}

# ── PyPI 检查 ─────────────────────────────────────────────────────────────────
check_pypi_not_exists() {
    local v="$1"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rodski/${v}/json")
    if [[ "$code" == "200" ]]; then
        fail "PyPI 上已存在 rodski ${v}，不能重复发布。"
    fi
    ok "PyPI 上无 rodski ${v}，可以发布。"
}

check_pypi_exists() {
    local v="$1"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rodski/${v}/json")
    [[ "$code" == "200" ]] && return 0 || return 1
}

# ── Git 工具 ──────────────────────────────────────────────────────────────────
require_clean_rodski() {
    if [[ -n "$(git -C "$PROJECT_ROOT" status --porcelain rodski/)" ]]; then
        fail "rodski/ 目录有未提交的更改，请先提交。"
    fi
}

require_on_main() {
    local branch
    branch=$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD)
    [[ "$branch" == "main" ]] || fail "当前分支是 '$branch'，发布必须在 main 分支执行。"
}
