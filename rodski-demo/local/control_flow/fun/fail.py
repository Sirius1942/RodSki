#!/usr/bin/env python3
"""不可达分支 / 故意失败的步骤：python3 fail.py LABEL

非零退出 → run 关键字判定步骤失败。写在"按文档不应执行"的分支里，
一旦框架走错分支，用例自身就会失败（无需编排脚本也能发现）。
"""
import sys

sys.stderr.write("CF_FAIL: " + " ".join(sys.argv[1:]) + "\n")
sys.exit(1)
