#!/usr/bin/env python3
"""RodSki Demo 运行脚本

跨平台运行脚本，支持 Windows/macOS/Linux。

使用示例:
    python3 run_demo.py
    python3 run_demo.py --case case/tc015_only.xml
    python3 run_demo.py --log-level debug
    python3 run_demo.py --init-db
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='RodSki Demo 运行脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 run_demo.py                              # 运行默认测试用例
  python3 run_demo.py --init-db                    # 初始化数据库后运行
  python3 run_demo.py --case case/tc015_only.xml   # 运行指定用例
  python3 run_demo.py --log-level debug            # 使用debug日志级别
        """
    )
    parser.add_argument(
        '--case',
        default='case/demo_case.xml',
        help='测试用例文件 (默认: case/demo_case.xml)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'debug', 'info', 'warning', 'error'],
        help='日志级别 (默认: INFO)'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='运行前初始化数据库'
    )

    args = parser.parse_args()

    # 获取路径
    demo_dir = Path(__file__).parent.resolve()
    project_root = demo_dir.parent.parent.parent

    print("=" * 60)
    print("RodSki Demo 测试运行")
    print("=" * 60)
    print(f"Demo目录: {demo_dir}")
    print(f"项目根目录: {project_root}")
    print(f"测试用例: {args.case}")
    print(f"日志级别: {args.log_level}")
    print("=" * 60)

    # 初始化数据库
    if args.init_db:
        print("\n🔧 初始化数据库...")
        init_db_script = demo_dir / 'init_db.py'
        if not init_db_script.exists():
            print(f"❌ 错误: 找不到 init_db.py")
            return 1

        try:
            subprocess.run(
                [sys.executable, str(init_db_script)],
                cwd=demo_dir,
                check=True
            )
            print("✅ 数据库初始化完成\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ 数据库初始化失败: {e}")
            return 1

    # 运行测试
    print(f"🚀 运行测试用例: {args.case}\n")

    case_file = demo_dir / args.case
    if not case_file.exists():
        print(f"❌ 错误: 找不到测试用例文件 {case_file}")
        return 1

    ski_run = project_root / 'rodski' / 'ski_run.py'
    if not ski_run.exists():
        print(f"❌ 错误: 找不到 ski_run.py at {ski_run}")
        return 1

    # Normalize log level to uppercase
    log_level = args.log_level.upper()

    cmd = [
        sys.executable,
        str(ski_run),
        str(case_file),
        '--log-level', log_level
    ]

    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("✅ 测试完成")
        else:
            print(f"⚠️  测试完成，退出码: {result.returncode}")
        print("=" * 60)
        return result.returncode
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 运行失败: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
