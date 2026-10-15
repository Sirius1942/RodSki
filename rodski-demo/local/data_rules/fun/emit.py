#!/usr/bin/env python3
"""输出一个 JSON 作为 run 步骤的返回值：python3 emit.py <tag>  →  {"tag": "<tag>"}

用于 F055（Return 引用）构造可辨识的步骤返回值链。
"""
import json
import sys

print(json.dumps({"tag": sys.argv[1] if len(sys.argv) > 1 else ""}))
