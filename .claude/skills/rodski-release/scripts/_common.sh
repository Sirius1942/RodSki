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
    # requested 必须与 $version 分开存：read_state 会 source 状态文件，
    # 而状态文件里的 `version=` 正好会覆盖同名局部变量。旧写法把请求版本
    # 也存进 $version，source 之后两者恒等，那道版本校验永远不可能触发。
    local required="$1" requested="$2"
    if ! read_state; then
        fail "未找到发布状态文件 (.release_state)。请从 stage1 开始执行。"
    fi
    # shellcheck disable=SC2154
    [[ "$stage" == "$required" ]] || fail "当前状态 stage=${stage}，需要先完成 $required 才能继续。"
    [[ "$version" == "$requested" ]] || fail "版本号不匹配：状态文件 v${version}，当前 v${requested}"
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
    #    用 \{1,\} 而不是 \+ —— BSD sed（macOS）的 ERE 转义不适用于 BRE，
    #    `[0-9.]\+` 在 BSD sed 里匹配不到任何东西，整条替换静默变成空操作。
    sed -i '' "s/当前版本：v[0-9.]\{1,\}/当前版本：v${v}/" "$PROJECT_ROOT/CLAUDE.md"
    ok "  CLAUDE.md → $v"

    # 5. 核心文档版本行（`**版本**: vX.Y.Z` 格式）
    #    这些文档里「版本」二字只出现在第 3 行的标题块，用 ^ 锚死；
    #    旧写法 `s/版本.*v[0-9.]\+/.../` 是贪婪匹配，既会命中正文里带
    #    「版本」的任意一行，又同样被 \+ 的空操作静默吃掉。
    #
    #    只认**三段式** `vX.Y.Z`。API_REFERENCE.md 里那句 `**版本**: v5.0+`
    #    属于文件内部内嵌的「DB 关键字 API 文档」子文档，标的是该模块自己的
    #    版本，不是 RodSki 发布版本 —— 用 `[0-9]\{1,\}\.[0-9]\{1,\}\.[0-9]\{1,\}`
    #    把它排除在外，免得把子文档标成框架版本。
    for doc in \
        "$RODSKI_DIR/docs/TEST_CASE_WRITING_GUIDE.md" \
        "$RODSKI_DIR/docs/CORE_DESIGN_CONSTRAINTS.md" \
        "$RODSKI_DIR/docs/ARCHITECTURE.md" \
        "$RODSKI_DIR/docs/API_REFERENCE.md"; do
        [[ -f "$doc" ]] || continue
        # ARCHITECTURE.md 等没有版本行，不命中是正常的，不当失败
        pattern='^\*\*版本\*\*: v[0-9]\{1,\}\.[0-9]\{1,\}\.[0-9]\{1,\}'
        if grep -q "$pattern" "$doc"; then
            sed -i '' "s/${pattern}/**版本**: v${v}/" "$doc"
            ok "  $(basename "$doc") → $v"
        else
            info "  $(basename "$doc")：无 RodSki 版本行，跳过"
        fi
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
