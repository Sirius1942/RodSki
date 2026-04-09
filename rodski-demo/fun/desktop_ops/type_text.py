#!/usr/bin/env python3
"""桌面文本输入脚本 - 使用 pyautogui"""
import sys
import pyautogui
import time

def main():
    if len(sys.argv) < 2:
        print("用法: python type_text.py <text> [interval]")
        sys.exit(1)

    text = sys.argv[1]
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05

    time.sleep(0.5)  # Brief pause before typing
    pyautogui.typewrite(text, interval=interval)
    print(f"已输入文本: {text}")

if __name__ == "__main__":
    main()
