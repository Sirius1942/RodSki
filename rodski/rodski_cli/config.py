"""config 子命令 - 配置管理"""
import sys


def setup_parser(subparsers):
    parser = subparsers.add_parser("config", help="配置管理")
    sub = parser.add_subparsers(dest="action", required=True)

    set_cmd = sub.add_parser("set", help="设置配置")
    set_cmd.add_argument("key", help="配置键")
    set_cmd.add_argument("value", help="配置值")

    get_cmd = sub.add_parser("get", help="获取配置")
    get_cmd.add_argument("key", help="配置键")

    sub.add_parser("list", help="列出所有配置")

    sub.add_parser("reset", help="重置为默认配置")


def handle(args):
    from ..core.config_manager import ConfigManager

    manager = ConfigManager()

    if args.action == "set":
        manager.set(args.key, args.value)
        print(f"已设置: {args.key} = {args.value}")
        return 0

    elif args.action == "get":
        value = manager.get(args.key)
        if value is not None:
            print(f"{args.key} = {value}")
            return 0
        else:
            print(f"配置不存在: {args.key}", file=sys.stderr)
            return 1

    elif args.action == "list":
        configs = manager.list_all()
        print("配置列表:")
        for k, v in configs.items():
            print(f"  {k} = {v}")
        return 0

    elif args.action == "reset":
        manager.reset()
        print("配置已重置为默认值")
        return 0
