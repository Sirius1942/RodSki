#!/usr/bin/env bash
#
# rodski sandbox — Docker 沙箱测试环境管理脚本
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="rodski-sandbox"
CONTAINER_NAME="rodski-sandbox"
COMPOSE="docker compose"
CASES_DIR="sandbox/cases"
RESULTS_DIR="sandbox/results"

_color()  { printf "\033[%sm%s\033[0m" "$1" "$2"; }
_info()   { echo "$(_color 36 "[sandbox]") $*"; }
_ok()     { echo "$(_color 32 "[sandbox]") $*"; }
_err()    { echo "$(_color 31 "[sandbox]") $*" >&2; }

_docker_exec() {
    local flags="-i"
    [[ -t 0 ]] && flags="-it"
    docker exec $flags "$CONTAINER_NAME" "$@"
}

_ensure_dirs() {
    mkdir -p "$CASES_DIR" "$RESULTS_DIR" sandbox/screenshots sandbox/logs
}

_is_running() {
    docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"
}

_ensure_running() {
    if ! _is_running; then
        _err "沙箱未运行，请先执行: $0 up"
        exit 1
    fi
}

cmd_build() {
    _info "构建 Docker 镜像..."
    _ensure_dirs
    $COMPOSE build "$@"
    _ok "镜像构建完成"
}

cmd_up() {
    _ensure_dirs
    if _is_running; then
        _info "沙箱已在运行中"
        return
    fi
    _info "启动沙箱..."
    $COMPOSE up -d "$@"
    _ok "沙箱已启动 (容器: $CONTAINER_NAME)"
    _info "用例目录: $CASES_DIR/"
    _info "结果目录: $RESULTS_DIR/"
}

cmd_down() {
    _info "停止沙箱..."
    $COMPOSE down "$@"
    _ok "沙箱已停止"
}

cmd_restart() {
    cmd_down
    cmd_up
}

cmd_run() {
    _ensure_running
    if [[ $# -lt 1 ]]; then
        _err "用法: $0 run <用例文件> [选项...]"
        _err "示例: $0 run examples/demo_case.xlsx --verbose"
        _err "      $0 run sandbox/cases/my_test.xlsx --retry 2"
        exit 1
    fi
    local case_file="$1"; shift
    _info "执行测试用例: $case_file"
    _docker_exec python3 cli_main.py run "$case_file" --headless "$@"
}

cmd_push() {
    if [[ $# -lt 1 ]]; then
        _err "用法: $0 push <本地文件> [容器内目标路径]"
        _err "示例: $0 push ~/tests/login.xlsx"
        _err "      $0 push ~/tests/login.xlsx examples/"
        exit 1
    fi
    _ensure_dirs
    local src="$1"
    local dest="${2:-}"
    local filename
    filename="$(basename "$src")"

    if [[ -n "$dest" ]]; then
        if _is_running; then
            _info "推送 $filename → 容器 $dest"
            docker cp "$src" "${CONTAINER_NAME}:/app/$dest"
        else
            _err "指定容器路径时沙箱需要运行中"
            exit 1
        fi
    else
        _info "复制 $filename → $CASES_DIR/"
        cp "$src" "$CASES_DIR/"
        _ok "文件已就位: $CASES_DIR/$filename"
        if _is_running; then
            _info "提示: 执行 → $0 run sandbox/cases/$filename"
        fi
    fi
}

cmd_push_run() {
    if [[ $# -lt 1 ]]; then
        _err "用法: $0 push-run <本地文件> [运行选项...]"
        _err "示例: $0 push-run ~/tests/login.xlsx --verbose"
        exit 1
    fi
    _ensure_running
    local src="$1"; shift
    local filename
    filename="$(basename "$src")"

    cp "$src" "$CASES_DIR/"
    _info "推送并执行: $filename"
    _docker_exec python3 cli_main.py run "sandbox/cases/$filename" --headless "$@"
}

cmd_pytest() {
    _ensure_running
    _info "运行单元/集成测试..."
    _docker_exec python3 -m pytest "${@:--v --tb=short}"
}

cmd_logs() {
    local log_dir="sandbox/logs"
    if [[ $# -ge 1 ]]; then
        case "$1" in
            -f|--follow)
                _ensure_running
                _docker_exec tail -f /app/logs/latest.log 2>/dev/null \
                    || _err "暂无日志文件"
                return
                ;;
        esac
    fi
    if [[ -d "$log_dir" ]] && ls "$log_dir"/*.log 1>/dev/null 2>&1; then
        _info "最近日志:"
        ls -lt "$log_dir"/*.log 2>/dev/null | head -5
        echo "---"
        tail -50 "$(ls -t "$log_dir"/*.log 2>/dev/null | head -1)" 2>/dev/null
    else
        _info "暂无日志文件"
    fi
}

cmd_report() {
    _ensure_running
    _info "生成测试报告..."
    _docker_exec python3 cli_main.py report "${@:---format html}"
    if ls sandbox/logs/report.html 1>/dev/null 2>&1; then
        _ok "报告已生成: sandbox/logs/report.html"
    fi
}

cmd_screenshots() {
    local ss_dir="sandbox/screenshots"
    if [[ -d "$ss_dir" ]] && ls "$ss_dir"/*.png 1>/dev/null 2>&1; then
        _info "截图列表:"
        ls -lt "$ss_dir"/*.png | head -20
    else
        _info "暂无截图"
    fi
}

cmd_shell() {
    _ensure_running
    _info "进入沙箱 shell..."
    docker exec -it "$CONTAINER_NAME" /bin/bash
}

cmd_status() {
    if _is_running; then
        _ok "沙箱运行中"
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Status}}\t{{.Ports}}\t{{.Size}}"
    else
        _info "沙箱未运行"
    fi
}

cmd_clean() {
    _info "清理输出文件..."
    rm -rf sandbox/logs/* sandbox/screenshots/* sandbox/results/*
    _ok "清理完成"
}

cmd_nuke() {
    _info "完全清除沙箱环境..."
    $COMPOSE down --rmi all --volumes 2>/dev/null || true
    rm -rf sandbox/
    _ok "沙箱环境已完全清除"
}

cmd_help() {
    cat <<EOF
$(_color 36 "rodski sandbox") — Docker 沙箱测试环境

$(_color 33 "生命周期管理:")
  build             构建 Docker 镜像
  up                启动沙箱容器 (后台)
  down              停止沙箱
  restart           重启沙箱
  status            查看沙箱状态
  clean             清理输出文件 (日志/截图/结果)
  nuke              完全清除 (含镜像)

$(_color 33 "测试执行:")
  run <用例> [选项]        在沙箱中执行测试用例
  push <文件> [目标路径]   推送用例文件到沙箱
  push-run <文件> [选项]   推送并立即执行用例 (一键操作)
  pytest [选项]            运行 pytest 单元/集成测试

$(_color 33 "结果查看:")
  logs [-f]         查看/追踪日志
  report [选项]     生成测试报告
  screenshots       列出截图文件

$(_color 33 "其他:")
  shell             进入容器交互式 shell
  help              显示本帮助信息

$(_color 33 "使用示例:")
  $0 build && $0 up                        # 首次使用: 构建并启动
  $0 push-run ~/test/login.xlsx --verbose  # 推送用例并执行
  $0 run examples/demo_case.xlsx           # 执行内置示例
  $0 pytest tests/unit/ -v                 # 运行单元测试
  $0 logs -f                               # 实时追踪日志

EOF
}

# ----- 主入口 -----
case "${1:-help}" in
    build)       shift; cmd_build "$@" ;;
    up|start)    shift; cmd_up "$@" ;;
    down|stop)   shift; cmd_down "$@" ;;
    restart)     shift; cmd_restart "$@" ;;
    run)         shift; cmd_run "$@" ;;
    push)        shift; cmd_push "$@" ;;
    push-run)    shift; cmd_push_run "$@" ;;
    pytest|test) shift; cmd_pytest "$@" ;;
    logs|log)    shift; cmd_logs "$@" ;;
    report)      shift; cmd_report "$@" ;;
    screenshots) shift; cmd_screenshots "$@" ;;
    shell|sh)    shift; cmd_shell "$@" ;;
    status)      shift; cmd_status "$@" ;;
    clean)       shift; cmd_clean "$@" ;;
    nuke)        shift; cmd_nuke "$@" ;;
    help|--help|-h) cmd_help ;;
    *)
        _err "未知命令: $1"
        echo ""
        cmd_help
        exit 1
        ;;
esac
