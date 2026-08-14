"""Single-case roaming CLI adapter.

The roaming command deliberately delegates to ``run.handle`` so path
resolution, hooks, compliance checks, driver lifecycle, and output formatting
keep exactly the same behavior as a normal run.
"""
from __future__ import annotations

from pathlib import Path

from . import run


def setup_parser(subparsers):
    parser = subparsers.add_parser("roam", help="对指定用例执行漫游测试")
    parser.add_argument(
        "path",
        nargs="?",
        help="用例 XML、case/ 目录或测试模块目录（默认当前目录）",
    )
    parser.add_argument("--case", required=True, dest="roam_case_id", help="基础用例 ID")
    parser.add_argument("--model", help="模型文件路径 (model.xml)，不指定则自动推断")
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="浏览器类型 (默认: chromium)",
    )
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")
    parser.add_argument("--output", help="报告输出路径")
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--report",
        choices=["html"],
        default=None,
        help="执行完毕后自动生成报告 (可选值: html)",
    )
    parser.add_argument("--trace", action="store_true", help="启用 observability 并导出 trace.json")
    parser.add_argument(
        "--platform",
        choices=["android", "ios"],
        default=None,
        help="移动端平台（android/ios），覆盖 globalvalue.xml Mobile.Platform",
    )
    parser.add_argument(
        "--force-compliance",
        action="store_true",
        dest="force_compliance",
        help="显式跳过可豁免的 on_run_start 内置合规检查，跳过会留痕",
    )
    parser.add_argument(
        "--roam-engine",
        dest="roam_engine_module",
        default=None,
        metavar="MODULE_PATH",
        help="漫游决策引擎模块路径（Python 文件），须导出 create_engine() 工厂函数",
    )


def handle(args):
    """Map ``rodski roam`` onto the shared run execution pipeline."""
    args.case = args.path or str(Path.cwd())
    args.roam = True
    args.roam_mode = "single_case"

    # ``run.handle`` directly reads these three fields; all other run options
    # already use getattr defaults and remain disabled for the focused command.
    if not hasattr(args, "model"):
        args.model = None
    if not hasattr(args, "browser"):
        args.browser = "chromium"
    if not hasattr(args, "output"):
        args.output = None

    return run.handle(args)
