#!/usr/bin/env python3
"""切换到指定标题的窗口"""
import json
import sys
import subprocess

try:
    title = sys.argv[1] if len(sys.argv) > 1 else ""

    if sys.platform == 'darwin':
        # macOS: 使用 AppleScript
        script = f'tell application "{title}" to activate'
        subprocess.run(['osascript', '-e', script], check=True)
    else:
        # Windows: 使用 pyautogui
        import pyautogui
        windows = pyautogui.getWindowsWithTitle(title)
        if windows:
            windows[0].activate()
        else:
            raise Exception(f"Window not found: {title}")

    print(json.dumps({"status": "success", "window": title}))
except Exception as e:
    print(json.dumps({"status": "error", "message": str(e)}))
    sys.exit(1)
