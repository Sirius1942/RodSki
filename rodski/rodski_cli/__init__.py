"""CLI 子命令模块"""
import sys
import argparse
import ast
from pathlib import Path
from . import run, model, config, log, report, docs, data, init, plan, capabilities

from importlib.metadata import PackageNotFoundError, version


def _load_version():
    local_version = _load_version_from_file(Path(__file__).resolve().parents[1] / "__init__.py")
    if local_version:
        return local_version

    try:
        from rodski import __version__
        return __version__
    except (ImportError, AttributeError):
        pass

    try:
        import __init__ as _pkg
        return _pkg.__version__
    except (ImportError, AttributeError):
        pass

    try:
        return version("rodski")
    except PackageNotFoundError:
        return "dev"


def _load_version_from_file(path: Path):
    try:
        module = ast.parse(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    return None


VERSION = _load_version()

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
    plan.setup_parser(subparsers)
    capabilities.setup_parser(subparsers)

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
        "plan": plan.handle,
        "capabilities": capabilities.handle,
    }

    try:
        return handlers[args.command](args)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
