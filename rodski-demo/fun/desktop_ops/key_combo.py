#!/usr/bin/env python3
"""桌面快捷键组合脚本 - 使用 pyautogui"""
import sys
import pyautogui
import time

def main():
    if len(sys.argv) < 2:
        print("用法: python key_combo.py <key_combo>")
        print("示例: python key_combo.py Ctrl+A")
        print("      python key_combo.py Ctrl+Shift+S")
        sys.exit(1)

    combo = sys.argv[1]
    keys = [k.strip().lower() for k in combo.split('+')]

    # Map common key names
    key_map = {
        'ctrl': 'ctrl',
        'alt': 'alt',
        'shift': 'shift',
        'cmd': 'command',
        'command': 'command',
        'enter': 'enter',
        'tab': 'tab',
        'esc': 'escape',
        'escape': 'escape',
        'delete': 'delete',
        'backspace': 'backspace',
        'space': 'space',
        'up': 'up',
        'down': 'down',
        'left': 'left',
        'right': 'right',
        'f4': 'f4',
    }

    mapped_keys = [key_map.get(k, k) for k in keys]

    time.sleep(0.3)
    pyautogui.hotkey(*mapped_keys)
    print(f"已执行快捷键: {combo}")

if __name__ == "__main__":
    main()
