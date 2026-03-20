"""log 子命令 - 日志管理"""
from pathlib import Path


def setup_parser(subparsers):
    parser = subparsers.add_parser("log", help="日志管理")
    sub = parser.add_subparsers(dest="action", required=True)

    view = sub.add_parser("view", help="查看日志")
    view.add_argument("--lines", type=int, default=50, help="显示行数")
    view.add_argument("--file", help="指定日志文件")

    sub.add_parser("list", help="列出日志文件")
    sub.add_parser("clear", help="清空日志")


def handle(args):
    log_dir = Path("logs")

    if args.action == "view":
        if hasattr(args, "file") and args.file:
            log_file = log_dir / args.file
        else:
            log_files = sorted(log_dir.glob("*.log"))
            if not log_files:
                print("暂无日志")
                return 0
            log_file = log_files[-1]

        if not log_file.exists():
            print(f"日志文件不存在: {log_file}")
            return 1

        print(f"日志文件: {log_file.name}")
        lines = log_file.read_text(encoding="utf-8").splitlines()
        for line in lines[-args.lines:]:
            print(line)
        return 0

    elif args.action == "list":
        log_files = sorted(log_dir.glob("*.log"))
        if not log_files:
            print("暂无日志文件")
        else:
            print("日志文件:")
            for f in log_files:
                size = f.stat().st_size
                print(f"  {f.name} ({size} bytes)")
        return 0

    elif args.action == "clear":
        count = 0
        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                log_file.unlink()
                count += 1
        print(f"已清空 {count} 个日志文件")
        return 0
