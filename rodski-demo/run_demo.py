#!/usr/bin/env python3
"""RodSki Demo 跨平台运行脚本

用法:
    python run_demo.py                         # 默认: 初始化数据库 + 运行测试
    python run_demo.py --init-db               # 仅初始化数据库
    python run_demo.py --case case/demo_case.xml  # 运行指定用例
    python run_demo.py --start-server          # 启动 demosite 服务
    python run_demo.py --log-level DEBUG       # 设置日志级别
"""

import argparse
import subprocess
import sys
from pathlib import Path


DEMO_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = DEMO_DIR.parent  # rodski-demo -> RodSki


def init_db():
    """初始化 SQLite 数据库"""
    print("初始化数据库...")
    result = subprocess.run(
        [sys.executable, str(DEMO_DIR / "init_db.py")],
        cwd=str(DEMO_DIR),
    )
    if result.returncode != 0:
        print("数据库初始化失败")
        sys.exit(1)
    print("数据库初始化成功")


def start_server(host="0.0.0.0", port=8000):
    """启动 demosite FastAPI 服务"""
    print(f"启动 demosite 服务: http://{host}:{port}")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "demosite.app:app",
         "--host", host, "--port", str(port), "--reload"],
        cwd=str(DEMO_DIR),
    )


def run_case(case_path, log_level="INFO"):
    """运行测试用例"""
    ski_run = PROJECT_ROOT / "rodski" / "ski_run.py"
    if not ski_run.exists():
        print(f"找不到 ski_run.py: {ski_run}")
        sys.exit(1)

    # 构建相对于项目根目录的用例路径
    full_case_path = DEMO_DIR / case_path
    if not full_case_path.exists():
        print(f"找不到用例文件: {full_case_path}")
        sys.exit(1)

    rel_case = full_case_path.relative_to(PROJECT_ROOT)
    print(f"运行测试用例: {rel_case}")

    cmd = [sys.executable, str(ski_run), str(rel_case)]
    if log_level != "INFO":
        cmd.extend(["--log-level", log_level])

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="RodSki Demo 运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--init-db", action="store_true",
        help="初始化数据库",
    )
    parser.add_argument(
        "--case", type=str, default="case/demo_case.xml",
        help="测试用例文件路径（相对于 rodski-demo 目录），默认: case/demo_case.xml",
    )
    parser.add_argument(
        "--start-server", action="store_true",
        help="启动 demosite Web 服务",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别，默认: INFO",
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="服务绑定地址，默认: 0.0.0.0",
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="服务端口，默认: 8000",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("  RodSki Demo Runner")
    print("=" * 50)
    print(f"  Demo 目录: {DEMO_DIR}")
    print(f"  项目根目录: {PROJECT_ROOT}")
    print()

    if args.start_server:
        init_db()
        start_server(args.host, args.port)
        return

    if args.init_db:
        init_db()
        return

    # 默认: 初始化数据库 + 运行测试
    init_db()
    print()
    rc = run_case(args.case, args.log_level)
    print()
    if rc == 0:
        print("测试完成！")
    else:
        print(f"测试执行返回码: {rc}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
