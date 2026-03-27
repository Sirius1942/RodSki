#!/usr/bin/env python3
"""设置剪贴板内容并粘贴"""
import json
import sys

try:
    import pyperclip
    import pyautogui

    text = sys.argv[1] if len(sys.argv) > 1 else ""
    pyperclip.copy(text)
    pyautogui.hotkey('command' if sys.platform == 'darwin' else 'ctrl', 'v')
    print(json.dumps({"status": "success", "text": text}))
except ImportError as e:
    print(json.dumps({"status": "error", "message": f"Missing dependency: {e}"}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"status": "error", "message": str(e)}))
    sys.exit(1)
