#!/usr/bin/env python3
"""桌面鼠标点击脚本 - 使用 pyautogui"""
import sys
import pyautogui
import time

def main():
    if len(sys.argv) < 3:
        print("用法: python mouse_click.py <x> <y> [click_type]")
        print("click_type: left(默认), right, double")
        sys.exit(1)

    x = int(sys.argv[1])
    y = int(sys.argv[2])
    click_type = sys.argv[3] if len(sys.argv) > 3 else 'left'

    time.sleep(0.3)

    if click_type == 'right':
        pyautogui.rightClick(x, y)
    elif click_type == 'double':
        pyautogui.doubleClick(x, y)
    else:
        pyautogui.click(x, y)

    print(f"已点击: ({x}, {y}) 类型: {click_type}")

if __name__ == "__main__":
    main()
