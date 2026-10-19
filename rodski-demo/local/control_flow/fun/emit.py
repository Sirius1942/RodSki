#!/usr/bin/env python3
"""输出接口风格的 JSON 作为步骤返回值：python3 emit.py STATUS [MSG]

run 关键字会把 stdout 自动 JSON 解析后写入 Return，供 ${Return[-1].status} 条件使用。
"""
import json
import sys

status = int(sys.argv[1]) if len(sys.argv) > 1 else 200
msg = sys.argv[2] if len(sys.argv) > 2 else ""
print(json.dumps({"status": status, "msg": msg}))
