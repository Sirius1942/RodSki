"""Single-case roaming CLI adapter.

The roaming command deliberately delegates to ``run.handle`` so path
resolution, hooks, compliance checks, driver lifecycle, and output formatting
keep exactly the same behavior as a normal run.

v11.5.0: 支持 --case-file + --case-id 定位用例（多级嵌套目录）。
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import run


def setup_parser(subparsers):
    parser = subparsers.add_parser("roam", help="对指定用例执行漫游测试")
    parser.add_argument(
        "path",
        nargs="?",
        help="用例 XML、case/ 目录或测试模块目录（默认当前目录）",
    )
    # v11.5.0: 新增 --case-file + --case-id，保留旧 --case 为兼容路径
    parser.add_argument("--case-file", dest="roam_case_file", help="用例文件路径（相对 case/ 的 POSIX 路径）")
    parser.add_argument("--case-id", dest="roam_case_id_new", help="用例 ID")
    parser.add_argument("--case", dest="roam_case_id", help="（向后兼容）用例 ID，仅当模块只有一个用例文件或 ID 全模块唯一时可用")
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
    # 供 handle() 在缺少用例定位参数时调用 parser.error()（argparse 惯例：exit code 2）
    parser.set_defaults(_roam_parser=parser)


def handle(args):
    """Map ``rodski roam`` onto the shared run execution pipeline.

    v11.5.0: 支持 --case-file + --case-id 定位用例；保留旧 --case 仅在
    单文件模块或 ID 全模块唯一时可用，否则提示使用新参数。
    """
    from pathlib import Path

    # 解析用例定位参数
    case_file = getattr(args, "roam_case_file", None)
    case_id_new = getattr(args, "roam_case_id_new", None)
    case_id_old = getattr(args, "roam_case_id", None)

    # 优先使用新参数
    if case_file and case_id_new:
        # 新模式：--case-file + --case-id
        module_dir = Path(args.path or Path.cwd()).resolve()
        if module_dir.is_file():
            module_dir = module_dir.parent.parent
        elif module_dir.name == "case":
            module_dir = module_dir.parent
        args.case = str(module_dir / "case" / case_file)
        args.roam_case_id = case_id_new
    elif case_id_old:
        # 旧模式：--case（向后兼容），路径推导由 run.handle 完成
        args.case = args.path or str(Path.cwd())
        args.roam_case_id = case_id_old
        # 在多文件模块中会有歧义，这里暂不检查，留给 run.handle 判断
    elif case_id_new:
        print("错误: --case-id 必须与 --case-file 一起使用", file=sys.stderr)
        return 1
    elif case_file:
        print("错误: --case-file 必须与 --case-id 一起使用", file=sys.stderr)
        return 1
    else:
        parser = getattr(args, "_roam_parser", None)
        message = "必须指定 --case-file + --case-id 或使用旧 --case"
        if parser is not None:
            # argparse 惯例：用法错误以 exit code 2 退出（与缺失必填参数一致）
            parser.error(message)
        print(f"错误: {message}", file=sys.stderr)
        return 1

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
