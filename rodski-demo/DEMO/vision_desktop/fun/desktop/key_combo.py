#!/usr/bin/env python3
"""执行组合键"""
import json
import sys

try:
    import pyautogui

    keys = sys.argv[1] if len(sys.argv) > 1 else "Ctrl+C"
    key_list = keys.replace('+', ',').split(',')
    pyautogui.hotkey(*key_list)
    print(json.dumps({"status": "success", "keys": keys}))
except ImportError:
    print(json.dumps({"status": "error", "message": "pyautogui not installed"}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"status": "error", "message": str(e)}))
    sys.exit(1)
