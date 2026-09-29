"""model 子命令 - 模型管理"""
import sys
from pathlib import Path


def setup_parser(subparsers):
    parser = subparsers.add_parser("model", help="模型管理")
    sub = parser.add_subparsers(dest="action", required=True)

    create = sub.add_parser("create", help="创建模型")
    create.add_argument("name", help="模型名称")
    create.add_argument("type", help="模型类型")

    sub.add_parser("list", help="列出所有模型")

    validate = sub.add_parser("validate", help="验证模型")
    validate.add_argument("name", help="模型名称")

    delete = sub.add_parser("delete", help="删除模型")
    delete.add_argument("name", help="模型名称")

    # lint: 检查未使用/未定义的 model
    lint = sub.add_parser("lint", help="检查未使用/未定义的 model")
    lint.add_argument("module", help="测试模块目录")


def handle(args):
    if args.action == "lint":
        return _lint(args.module)

    from data.model_manager import ModelManager
    manager = ModelManager()

    if args.action == "create":
        manager.create_model(args.name, args.type)
        print(f"已创建模型: {args.name} ({args.type})")
        return 0

    elif args.action == "list":
        models = manager.list_models()
        if not models:
            print("暂无模型")
        else:
            print("模型列表:")
            for m in models:
                print(f"  - {m}")
        return 0

    elif args.action == "validate":
        valid = manager.validate_model(args.name)
        if valid:
            print(f"模型有效: {args.name}")
            return 0
        else:
            print(f"模型无效: {args.name}", file=sys.stderr)
            return 1

    elif args.action == "delete":
        if manager.delete(args.name):
            print(f"已删除模型: {args.name}")
            return 0
        else:
            print(f"模型不存在: {args.name}", file=sys.stderr)
            return 1


def _lint(module: str) -> int:
    """检查未使用/未定义的 model。

    递归扫描全部用例、business/ 与数据表，输出：
    - 未被引用的 model
    - 被引用但未定义的 model

    返回：有问题时返回 0（提示性），始终 0 退出
    """
    module_path = Path(module).resolve()
    model_file = module_path / "model" / "model.xml"

    if not model_file.is_file():
        print(f"错误: 模型文件不存在: {model_file}", file=sys.stderr)
        return 1

    # 加载模型定义
    from rodski.core.model_parser import ModelParser
    try:
        parser = ModelParser(str(model_file))
        defined_models = set(parser.models.keys())
    except Exception as e:
        print(f"错误: 模型解析失败: {e}", file=sys.stderr)
        return 1

    # 扫描用例、business、数据表中引用的 model
    from rodski.core.case_discovery import discover_case_files
    import xml.etree.ElementTree as ET

    referenced_models = set()
    case_dir = module_path / "case"
    business_dir = module_path / "business"
    data_dir = module_path / "data"

    # 扫描用例
    if case_dir.is_dir():
        for case_file in discover_case_files(case_dir):
            try:
                tree = ET.parse(case_file)
                for step in tree.findall('.//test_step'):
                    model = step.get('model', '').strip()
                    if model and '.' in model:
                        model_name = model.split('.')[0]
                        referenced_models.add(model_name)
            except:
                pass

    # 扫描 business
    if business_dir.is_dir():
        for biz_file in business_dir.glob('*.xml'):
            try:
                tree = ET.parse(biz_file)
                for step in tree.findall('.//step'):
                    model = step.get('model', '').strip()
                    if model and '.' in model:
                        model_name = model.split('.')[0]
                        referenced_models.add(model_name)
            except:
                pass

    # 扫描数据表（data.sqlite 中的逻辑表名可能对应 model）
    # 注意：这是启发式检查，动态拼接的 model 名无法静态分析
    if data_dir.is_dir() and (data_dir / "data.sqlite").is_file():
        try:
            from rodski.core.data_table_parser import DataTableParser
            dm = DataTableParser(str(data_dir))
            dm.parse_all_tables()
            for table_name in dm.tables.keys():
                if table_name in defined_models:
                    referenced_models.add(table_name)
        except:
            pass

    # 输出未被引用的 model
    unused = defined_models - referenced_models
    if unused:
        print("[未被引用的 model]")
        for name in sorted(unused):
            print(f"  {name}")

    # 输出被引用但未定义的 model
    undefined = referenced_models - defined_models
    if undefined:
        print("[被引用但未定义的 model]")
        for name in sorted(undefined):
            print(f"  {name}")

    # 提示
    if not unused and not undefined:
        print("[OK] 所有 model 都被引用且已定义")
    else:
        print(f"\n注意：动态拼接的 model 名无法静态分析，以上结果仅供参考")

    return 0
