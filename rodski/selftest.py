#!/usr/bin/env python3
"""RodSki 自检入口 — 使用框架自有测试执行器运行全部测试

用法（在 rodski/ 目录下）::

    python selftest.py                                         # 跑全部测试
    python selftest.py tests/unit/test_case_parser.py          # 指定文件
    python selftest.py tests/unit/test_case_parser.py tests/unit/test_auto_screenshot.py  # 多个文件
    python selftest.py -v                                      # 详细输出
"""
import sys
from pathlib import Path

# 确保 rodski/ 在 sys.path 最前，以便 from core.xxx 能正确导入
_rodski_dir = Path(__file__).resolve().parent
if str(_rodski_dir) not in sys.path:
    sys.path.insert(0, str(_rodski_dir))

from core.test_runner import RodskiTestRunner


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    verbosity = 2 if verbose else 1

    runner = RodskiTestRunner(verbosity=verbosity)
    files = runner.discover_files(args, test_dir="tests")

    if not files:
        print("未找到测试文件")
        sys.exit(1)

    print(f"RodSki 自检 — 共发现 {len(files)} 个测试文件")
    exit_code = runner.run(files)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
