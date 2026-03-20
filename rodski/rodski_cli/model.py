"""model 子命令 - 模型管理"""
import sys


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


def handle(args):
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
