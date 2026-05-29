#!/usr/bin/env bash
# stage2_acceptance.sh — 阶段 2：主干验收测试
#
# 用法: stage2_acceptance.sh <VERSION>
#
# 职责:
#   在打 tag 和打包之前，对主干代码跑一轮完整验收：
#   1. 全量单元测试（pytest tests/unit/）
#   2. demo_full UI 用例全量回归

set -euo pipefail
source "$(dirname "$0")/_common.sh"

VERSION=$(require_version "${1:-}")
cd "$PROJECT_ROOT"

info "═══════════════════════════════════════════════════════════"
info " Stage 2: 主干验收测试 (v${VERSION})"
info "═══════════════════════════════════════════════════════════"

require_stage stage1 "$VERSION"
require_on_main

info "[1/2] 跑全量单元测试..."
cd "$RODSKI_DIR"
if ! python3 -m pytest tests/unit/ -q --tb=short; then
    cd "$PROJECT_ROOT"
    fail "单元测试未全部通过，发布中止。修复后重跑 stage2。"
fi
cd "$PROJECT_ROOT"
ok "单元测试全部通过"

info "[2/2] 跑 demo_full UI 用例全量回归..."
DEMO_FILES=(
    "rodski-demo/DEMO/demo_full/case/demo_case.xml"
    "rodski-demo/DEMO/demo_full/case/tc015_only.xml"
    "rodski-demo/DEMO/demo_full/case/tc016_locators.xml"
    "rodski-demo/DEMO/demo_full/case/tc017_keywords.xml"
    "rodski-demo/DEMO/demo_full/case/tc020_windows.xml"
    "rodski-demo/DEMO/demo_full/case/tc021_data_ref.xml"
    "rodski-demo/DEMO/demo_full/case/tc022_negative.xml"
    "rodski-demo/DEMO/demo_full/case/tc050_builtin_functions.xml"
    "rodski-demo/DEMO/demo_full/case/tc_expect_fail.xml"
    "rodski-demo/DEMO/demo_full/case/tc040_scenario_basic.xml"
)
FAILED_CASES=()
for f in "${DEMO_FILES[@]}"; do
    [[ -f "$f" ]] || { warn "  跳过不存在的用例: $f"; continue; }
    name=$(basename "$f" .xml)
    if ! result=$(rodski run "$f" 2>&1 | tail -1); then
        FAILED_CASES+=("$name")
        warn "  ✗ $name: $result"
        continue
    fi
    if [[ "$result" == *"失败"* && "$result" != *"0 失败"* ]]; then
        FAILED_CASES+=("$name: $result")
        warn "  ✗ $name: $result"
    else
        ok "  ✓ $name: $result"
    fi
done

if [[ ${#FAILED_CASES[@]} -gt 0 ]]; then
    fail "${#FAILED_CASES[@]} 个用例失败，发布中止。"
fi
ok "demo_full UI 用例全部通过"

write_state stage2 "$VERSION"

ok "═══════════════════════════════════════════════════════════"
ok " Stage 2 完成"
ok "═══════════════════════════════════════════════════════════"
echo
info "下一步: stage3_build_and_tag.sh ${VERSION}"
