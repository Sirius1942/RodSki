#!/usr/bin/env python3
"""用例内自检：python3 assert_eq.py ACTUAL EXPECTED [说明]

相等则回显并退出 0；不等则 stderr 说明并退出 1（run 关键字判定步骤失败）。
ACTUAL 通常是 ${var} 解析后的值，用于统计分支命中次数（如 loop 内 if 命中计数）。
"""
import sys

actual = sys.argv[1] if len(sys.argv) > 1 else ""
expected = sys.argv[2] if len(sys.argv) > 2 else ""
note = " ".join(sys.argv[3:])
if actual != expected:
    sys.stderr.write(f"CF_ASSERT 不相等 {note}: 实际={actual!r} 期望={expected!r}\n")
    sys.exit(1)
print(actual)
