"""CLI 子命令模块"""
import sys
import argparse
from . import run, model, config, log, report, docs, data, init

from rodski import __version__ as VERSION

def main():
    parser = argparse.ArgumentParser(
        prog="rodski",
        description="RodSki - 关键字驱动测试框架"
    )
    parser.add_argument("--version", action="version", version=f"RodSki {VERSION}")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    run.setup_parser(subparsers)
    model.setup_parser(subparsers)
    config.setup_parser(subparsers)
    log.setup_parser(subparsers)
    report.setup_parser(subparsers)
    docs.setup_parser(subparsers)
    data.setup_parser(subparsers)
    init.setup_parser(subparsers)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "run": run.handle,
        "model": model.handle,
        "config": config.handle,
        "log": log.handle,
        "report": report.handle,
        "docs": docs.handle,
        "data": data.handle,
        "init": init.handle,
    }

    try:
        return handlers[args.command](args)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

