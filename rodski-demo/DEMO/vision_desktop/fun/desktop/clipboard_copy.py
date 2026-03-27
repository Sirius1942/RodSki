#!/usr/bin/env python3
"""读取剪贴板内容"""
import json
import sys

try:
    import pyperclip
    text = pyperclip.paste()
    print(json.dumps({"status": "success", "text": text}))
except ImportError:
    print(json.dumps({"status": "error", "message": "pyperclip not installed"}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"status": "error", "message": str(e)}))
    sys.exit(1)
