"""debug 子命令 - 调试信息查看命令

支持的调试命令：
- rodski debug status - 查看调试会话状态
- rodski debug queue - 查看执行队列
- rodski debug objects - 查看运行时对象
- rodski debug context - 查看上下文变量
- rodski debug get-object <id> - 获取指定对象详情
"""
import argparse
import sys
import logging
from pathlib import Path

logger = logging.getLogger("rodski")


def setup_parser(subparsers):
    """设置 debug 子命令的参数解析器"""
    parser = subparsers.add_parser(
        "debug",
        help="调试信息查看（需要在另一个终端运行 rodski run 时使用）"
    )
    parser.add_argument(
        "action",
        choices=["status", "queue", "objects", "context", "get-object"],
        help="调试动作"
    )
    parser.add_argument(
        "object_id",
        nargs="?",
        help="对象 ID（仅用于 get-object）"
    )


def handle(args):
    """处理 debug 命令"""
    try:
        from ..core.debug_session import get_debug_session
    except ImportError:
        from rodski.core.debug_session import get_debug_session

    session = get_debug_session()

    if not session.enabled:
        print("⚠️  Debug session is not active.")
        print("Please run 'rodski run' with debug options (e.g., --break-at step:5)")
        return 1

    if args.action == "status":
        print(session.format_status())
        return 0

    elif args.action == "queue":
        print(session.execution_queue.to_text())
        return 0

    elif args.action == "objects":
        print(session.object_pool.to_text())
        return 0

    elif args.action == "context":
        print(session.format_context())
        return 0

    elif args.action == "get-object":
        if not args.object_id:
            print("❌ Error: object_id is required for get-object")
            print("Usage: rodski debug get-object <object_id>")
            return 1

        runtime_obj = session.object_pool.get_runtime_object(args.object_id)
        if not runtime_obj:
            print(f"❌ Object not found: {args.object_id}")
            print("\nAvailable objects:")
            print(session.object_pool.to_text())
            return 1

        # 显示对象详情
        print(f"\nObject: {runtime_obj.id}")
        print(f"Type: {runtime_obj.type}")
        print(f"Status: {runtime_obj.status}")
        print(f"Created: {runtime_obj.created_at.isoformat()}")
        print(f"Lifetime: {runtime_obj.get_lifetime_seconds()}s")

        if runtime_obj.metadata:
            print("\nMetadata:")
            for key, value in runtime_obj.metadata.items():
                print(f"  {key}: {value}")

        # 如果是浏览器对象，显示额外信息
        obj = runtime_obj.object
        if hasattr(obj, "current_url"):
            print(f"\nCurrent URL: {obj.current_url}")
        if hasattr(obj, "title"):
            try:
                print(f"Title: {obj.title}")
            except:
                pass

        print("\nPython Access:")
        print("  from rodski.core.debug_session import get_debug_session")
        print("  session = get_debug_session()")
        print(f"  obj = session.object_pool.get_object('{runtime_obj.id}')")
        print("  # Now you can use the object")

        return 0

    return 0
