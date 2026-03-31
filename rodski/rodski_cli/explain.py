"""explain 子命令 - 将测试用例 XML 解析为人类可读的步骤说明"""
import sys
from pathlib import Path


def setup_parser(subparsers):
    parser = subparsers.add_parser(
        "explain",
        help="将测试用例 XML 解析为人类可读的步骤说明",
    )
    parser.add_argument(
        "case",
        help="用例路径（XML 文件路径或 case/ 目录）",
    )
    parser.add_argument(
        "--model",
        help="模型文件路径 (model.xml)，不指定则自动推断",
    )
    parser.add_argument(
        "--data-dir",
        help="数据文件目录 (data/)，不指定则自动推断",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "markdown", "html"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径，不指定则输出到标准输出",
    )


def _resolve_module_dir(case_path: Path) -> Path:
    """从 case 路径推导测试模块目录"""
    if case_path.is_file():
        return case_path.parent.parent
    elif case_path.is_dir() and case_path.name == 'case':
        return case_path.parent
    return case_path


def handle(args):
    from core.test_case_explainer import TestCaseExplainer
    from core.model_parser import ModelParser
    from core.data_table_parser import DataTableParser

    raw_path = Path(args.case)
    if not raw_path.exists():
        print(f"错误: 路径不存在: {args.case}", file=sys.stderr)
        return 1

    # 推断 case 路径和模块目录
    if raw_path.is_file() and raw_path.suffix == '.xml':
        case_path = raw_path
    elif raw_path.is_dir():
        if raw_path.name == 'case':
            case_path = raw_path
        else:
            case_path = raw_path / 'case'
            if not case_path.exists():
                case_path = raw_path
    else:
        case_path = raw_path

    module_dir = _resolve_module_dir(case_path)

    # 解析模型和数据
    model_parser = None
    data_manager = None

    if args.model:
        model_path = Path(args.model)
    else:
        model_path = module_dir / "model" / "model.xml"

    if model_path.exists():
        try:
            model_parser = ModelParser(str(model_path))
        except Exception as e:
            print(f"警告: 无法加载模型文件 {model_path}: {e}", file=sys.stderr)
    else:
        print(f"提示: 未找到模型文件，使用无模型模式 → {model_path}", file=sys.stderr)

    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = module_dir / "data"

    if data_dir.exists():
        try:
            data_manager = DataTableParser(str(data_dir))
            data_manager.parse_all_tables()
        except Exception as e:
            print(f"警告: 无法加载数据目录 {data_dir}: {e}", file=sys.stderr)
    else:
        print(f"提示: 未找到数据目录，使用无数据模式 → {data_dir}", file=sys.stderr)

    # 生成说明
    explainer = TestCaseExplainer(
        model_parser=model_parser,
        data_manager=data_manager,
    )

    print(f"[explain] 用例路径: {case_path}")
    if model_parser:
        print(f"[explain] 模型文件: {model_path}")
    if data_manager and data_manager.tables:
        print(f"[explain] 数据表: {list(data_manager.tables.keys())}")
    print("-" * 60)

    try:
        output = explainer.explain_case(str(case_path), format=args.format)
    except Exception as e:
        print(f"错误: 解析失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    # 输出到文件或标准输出
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output, encoding="utf-8")
        print(f"[explain] 已输出到: {output_path}")
    else:
        print(output)

    return 0
