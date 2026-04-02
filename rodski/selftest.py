#!/usr/bin/env python3
"""RodSki 自检入口

用法（在 rodski/ 目录下）::

    python selftest.py                                         # 跑全部测试
    python selftest.py tests/unit/test_case_parser.py          # 指定文件
    python selftest.py tests/unit/test_case_parser.py tests/unit/test_auto_screenshot.py  # 多个文件
    python selftest.py -v                                      # 详细输出
    python selftest.py -- -k test_click                        # 只跑匹配关键字的测试
"""
import sys
from pathlib import Path


def main():
    import pytest

    # 收集 pytest 参数（去掉开头的 'selftest.py' 自身）
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    pytest_args = ["-v"] if "-v" in sys.argv or "--verbose" in sys.argv else []

    if args:
        # 指定了文件/目录
        files = [Path(a) for a in args if Path(a).exists()]
        pytest_args.extend([str(f) for f in files])
    else:
        # 默认跑全部 tests/
        pytest_args.append("tests/")

    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
