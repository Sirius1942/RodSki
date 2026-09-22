#!/usr/bin/env bash
# clean.sh — RodSki 仓库定期清理脚本
#
# 用途：清理构建缓存、运行产物、调试残留，保持仓库整洁
# 等级：
#   --tier1  清理第一档（缓存、构建产物、调试文件）
#   --tier2  清理第二档（demo 运行结果、移动端构建）
#   --all    清理第一档 + 第二档（默认）
#
# 安全保证：
#   - 只删除 gitignore 的文件（git clean -X）
#   - 保留所有被跟踪的历史结果文件
#   - 提供 --dry-run 模式预览

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色输出
ok()   { echo -e "\033[32m✓\033[0m $*"; }
info() { echo -e "\033[34m➜\033[0m $*"; }
warn() { echo -e "\033[33m⚠\033[0m $*"; }
fail() { echo -e "\033[31m✗\033[0m $*" >&2; exit 1; }

usage() {
    cat <<EOF
用法: $0 [选项]

选项:
  --tier1        只清理第一档（缓存、构建产物、调试文件）
  --tier2        只清理第二档（demo 运行结果、移动端构建）
  --all          清理第一档 + 第二档（默认）
  --dry-run      仅预览，不实际删除
  -h, --help     显示此帮助信息

清理范围:
  第一档（约 1.5G）:
    - 构建缓存: .npm-cache/, .next/, __pycache__/, dist/, *.egg-info/
    - 调试残留: *.log, test_*.py (根目录), .schema 等
    - 系统文件: .DS_Store
    - 空目录

  第二档（约 3.6G，会随运行不断增长）:
    - rodski-demo 运行结果: DEMO/*/result/
    - iOS 构建: demo_ios_app/build/, demo_ios_app/*.xcodeproj/
    - Android 构建: demo_android_app/app/build/, .gradle/, .kotlin/
    - 压测产物: demo_load/perf/*.py (LoadCompiler 生成)

示例:
  $0                      # 清理所有（第一档 + 第二档）
  $0 --tier1              # 只清理缓存和构建产物
  $0 --tier2 --dry-run    # 预览第二档清理内容
EOF
    exit 0
}

# 默认参数
TIER1=0
TIER2=0
DRY_RUN=0

# 解析参数
[[ $# -eq 0 ]] && TIER1=1 && TIER2=1  # 无参数 = --all
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tier1) TIER1=1; shift ;;
        --tier2) TIER2=1; shift ;;
        --all) TIER1=1; TIER2=1; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) usage ;;
        *) fail "未知参数: $1（使用 -h 查看帮助）" ;;
    esac
done

[[ $TIER1 -eq 0 && $TIER2 -eq 0 ]] && fail "至少选择一个清理等级（--tier1 / --tier2 / --all）"

cd "$PROJECT_ROOT"

# 检查 git 仓库
[[ ! -d .git ]] && fail "必须在 git 仓库根目录运行"

# 预览模式提示
[[ $DRY_RUN -eq 1 ]] && warn "预览模式（--dry-run），不会实际删除文件"

info "开始清理 $(basename "$PROJECT_ROOT")..."
echo

# ============================================================================
# 第一档：缓存、构建产物、调试残留
# ============================================================================
if [[ $TIER1 -eq 1 ]]; then
    info "═══════════════════════════════════════════════════════════"
    info " 第一档：缓存、构建产物、调试残留"
    info "═══════════════════════════════════════════════════════════"

    # 1. 大型缓存目录（使用 git clean -X 确保只删 gitignore 的）
    info "[1/6] 清理构建缓存..."
    CACHE_DIRS=(
        ".npm-cache"
        "rodski-website/.npm-cache"
        "rodski-website/.next"
        "rodski-vscode/.npm-cache"
    )
    for dir in "${CACHE_DIRS[@]}"; do
        if [[ -d "$dir" ]]; then
            SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
            if [[ $DRY_RUN -eq 1 ]]; then
                echo "  [预览] 将删除: $dir ($SIZE)"
            else
                rm -rf "$dir"
                ok "  已删除: $dir ($SIZE)"
            fi
        fi
    done

    # 2. Python 构建产物
    info "[2/6] 清理 Python 构建产物..."
    if [[ $DRY_RUN -eq 1 ]]; then
        git clean -Xdn | grep -E "(dist/|\.egg-info/)" || echo "  (无待清理项)"
    else
        git clean -Xdf --quiet -- "*/dist" "*/*.egg-info" 2>/dev/null || true
        ok "  已清理 dist/ 和 *.egg-info/"
    fi

    # 3. __pycache__
    info "[3/6] 清理 __pycache__..."
    COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
    if [[ $COUNT -gt 0 ]]; then
        if [[ $DRY_RUN -eq 1 ]]; then
            echo "  [预览] 将删除 $COUNT 个 __pycache__ 目录"
        else
            find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            ok "  已删除 $COUNT 个 __pycache__ 目录"
        fi
    else
        echo "  (无 __pycache__)"
    fi

    # 4. 根目录调试文件
    info "[4/6] 清理根目录调试文件..."
    DEBUG_FILES=(
        ".schema rs_field"
        "explore_demo_full_output.log"
        "test_explore_demo_full.py"
        "test_explore_demo_full_v9.2.3.py"
        "test_explore_v920.py"
        "test_summary.txt"
    )
    for f in "${DEBUG_FILES[@]}"; do
        if [[ -e "$f" ]]; then
            if [[ $DRY_RUN -eq 1 ]]; then
                echo "  [预览] 将删除: $f"
            else
                rm -f "$f"
                ok "  已删除: $f"
            fi
        fi
    done

    # 5. .DS_Store
    info "[5/6] 清理 .DS_Store..."
    COUNT=$(find . -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
    if [[ $COUNT -gt 0 ]]; then
        if [[ $DRY_RUN -eq 1 ]]; then
            echo "  [预览] 将删除 $COUNT 个 .DS_Store 文件"
        else
            find . -name ".DS_Store" -delete 2>/dev/null || true
            ok "  已删除 $COUNT 个 .DS_Store 文件"
        fi
    else
        echo "  (无 .DS_Store)"
    fi

    # 6. 空目录
    info "[6/6] 清理空目录..."
    if [[ $DRY_RUN -eq 1 ]]; then
        EMPTY=$(find . -type d -empty 2>/dev/null | wc -l | tr -d ' ')
        [[ $EMPTY -gt 0 ]] && echo "  [预览] 将删除 $EMPTY 个空目录" || echo "  (无空目录)"
    else
        find . -type d -empty -delete 2>/dev/null || true
        ok "  已清理空目录"
    fi

    ok "第一档清理完成"
    echo
fi

# ============================================================================
# 第二档：运行产物与移动端构建
# ============================================================================
if [[ $TIER2 -eq 1 ]]; then
    info "═══════════════════════════════════════════════════════════"
    info " 第二档：运行产物与移动端构建"
    info "═══════════════════════════════════════════════════════════"

    info "[1/4] 清理 demo_full 运行结果..."
    TARGET="rodski-demo/DEMO/demo_full/result"
    if [[ -d "$TARGET" ]]; then
        # 统计但保留被跟踪的历史结果
        TOTAL=$(find "$TARGET" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
        TRACKED=$(git ls-files "$TARGET" | wc -l | tr -d ' ')
        if [[ $DRY_RUN -eq 1 ]]; then
            SIZE=$(du -sh "$TARGET" 2>/dev/null | cut -f1)
            echo "  [预览] $TARGET: $TOTAL 个 run 目录 ($SIZE)，$TRACKED 个跟踪文件将保留"
        else
            git clean -Xdf --quiet "$TARGET" 2>/dev/null || true
            ok "  已清理 $TARGET ($TOTAL 个 run 目录，保留 $TRACKED 个跟踪文件)"
        fi
    else
        echo "  ($TARGET 不存在)"
    fi

    info "[2/4] 清理 mobile_app 运行结果..."
    TARGET="rodski-demo/DEMO/mobile_app/result"
    if [[ -d "$TARGET" ]]; then
        if [[ $DRY_RUN -eq 1 ]]; then
            SIZE=$(du -sh "$TARGET" 2>/dev/null | cut -f1)
            echo "  [预览] 将清理: $TARGET ($SIZE)"
        else
            git clean -Xdf --quiet "$TARGET" 2>/dev/null || true
            ok "  已清理 $TARGET"
        fi
    fi

    info "[3/4] 清理 iOS 构建产物..."
    IOS_TARGETS=(
        "rodski-demo/DEMO/mobile_app/demo_ios_app/build"
        "rodski-demo/DEMO/mobile_app/demo_ios_app/build_device"
        "rodski-demo/DEMO/mobile_app/demo_ios_app/RodskiDemo.xcodeproj"
    )
    for t in "${IOS_TARGETS[@]}"; do
        if [[ -e "$t" ]]; then
            if [[ $DRY_RUN -eq 1 ]]; then
                SIZE=$(du -sh "$t" 2>/dev/null | cut -f1)
                echo "  [预览] 将删除: $t ($SIZE)"
            else
                rm -rf "$t"
                ok "  已删除: $t"
            fi
        fi
    done

    info "[4/4] 清理 Android 构建产物..."
    ANDROID_TARGETS=(
        "rodski-demo/DEMO/mobile_app/demo_android_app/app/build"
        "rodski-demo/DEMO/mobile_app/demo_android_app/.gradle"
        "rodski-demo/DEMO/mobile_app/demo_android_app/.kotlin"
        "rodski-demo/DEMO/mobile_app/demo_android_app/local.properties"
    )
    for t in "${ANDROID_TARGETS[@]}"; do
        if [[ -e "$t" ]]; then
            if [[ $DRY_RUN -eq 1 ]]; then
                [[ -d "$t" ]] && SIZE=$(du -sh "$t" 2>/dev/null | cut -f1) || SIZE="0B"
                echo "  [预览] 将删除: $t ($SIZE)"
            else
                rm -rf "$t"
                ok "  已删除: $(basename "$t")"
            fi
        fi
    done

    # LoadCompiler 生成的 perf/*.py
    info "清理 LoadCompiler 产物..."
    PERF_DIR="rodski-demo/DEMO/demo_load/perf"
    if [[ -d "$PERF_DIR" ]]; then
        if [[ $DRY_RUN -eq 1 ]]; then
            COUNT=$(git clean -Xdn "$PERF_DIR" 2>/dev/null | grep "\.py$" | wc -l | tr -d ' ')
            [[ $COUNT -gt 0 ]] && echo "  [预览] 将删除 $COUNT 个生成的 .py 文件" || echo "  (无待清理项)"
        else
            git clean -Xdf --quiet "$PERF_DIR" 2>/dev/null || true
            ok "  已清理 $PERF_DIR/*.py"
        fi
    fi

    ok "第二档清理完成"
    echo
fi

# ============================================================================
# 总结
# ============================================================================
if [[ $DRY_RUN -eq 0 ]]; then
    ok "═══════════════════════════════════════════════════════════"
    ok " 清理完成"
    ok "═══════════════════════════════════════════════════════════"
    echo
    info "当前仓库体积: $(du -sh . 2>/dev/null | cut -f1)"
    info "磁盘可用空间: $(df -h . | tail -1 | awk '{print $4}')"
    echo
    warn "注意: 第二档的产物会随着运行用例不断增长，建议定期执行清理"
else
    info "预览完成，使用 $0 [选项] 实际执行清理"
fi
