#!/usr/bin/env python3
"""RodSki CLI 入口"""
import sys
import argparse
import traceback
from rodski_cli import run, model, config, log, report, profile, docs

VERSION = "3.1.0"


def format_error(e, verbose=False):
    """格式化错误信息，提高可读性"""
    error_type = type(e).__name__
    error_msg = str(e)

    # 常见错误的友好提示
    hints = {
        FileNotFoundError: "请检查文件路径是否正确",
        PermissionError: "请检查文件权限或以管理员身份运行",
        ConnectionError: "请检查网络连接或目标服务是否可用",
        TimeoutError: "操作超时，请检查网络或增加超时时间",
        KeyboardInterrupt: "用户中断执行",
        ImportError: "缺少依赖包，请运行: pip install -r requirements.txt",
    }

    hint = hints.get(type(e), "")
    lines = [f"错误 [{error_type}]: {error_msg}"]
    if hint:
        lines.append(f"提示: {hint}")
    if verbose:
        lines.append("")
        lines.append("详细堆栈信息:")
        lines.append(traceback.format_exc())
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="rodski",
        description="RodSki - 关键字驱动测试框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  ski run case/                        执行测试用例\n"
               "  ski run case/ --dry-run               验证用例但不执行\n"
               "  ski run case/ --verbose               详细输出模式\n"
               "  ski run case/ --step-by-step          单步执行模式\n"
               "  ski run case/ --pause-on-error        错误时暂停\n"
               "  ski run case/ --interactive           交互模式\n"
               "  ski config list                           查看配置\n"
    )
    parser.add_argument("--version", action="version", version=f"RodSki {VERSION}")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run 子命令
    run.setup_parser(subparsers)

    # model 子命令
    model.setup_parser(subparsers)

    # config 子命令
    config.setup_parser(subparsers)

    # log 子命令
    log.setup_parser(subparsers)

    # report 子命令
    report.setup_parser(subparsers)

    # profile 子命令
    profile.setup_parser(subparsers)

    # docs 子命令
    docs.setup_parser(subparsers)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # 执行对应子命令
    handlers = {
        "run": run.handle,
        "model": model.handle,
        "config": config.handle,
        "log": log.handle,
        "report": report.handle,
        "profile": profile.handle,
        "docs": docs.handle
    }

    verbose = getattr(args, "verbose", False)

    try:
        return handlers[args.command](args)
    except KeyboardInterrupt:
        print("\n操作已被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(format_error(e, verbose=verbose), file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
