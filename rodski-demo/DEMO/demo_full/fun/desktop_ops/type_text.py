#!/usr/bin/env python3
"""
桌面自动化 - 文本输入脚本
使用 pyautogui 在当前焦点窗口输入文本

用法: python type_text.py "要输入的文本"
"""
import sys
import time

try:
    import pyautogui
except ImportError:
    print("错误: 需要安装 pyautogui")
    print("安装命令: pip install pyautogui")
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python type_text.py <文本内容>")
        sys.exit(1)

    text = sys.argv[1]

    # 等待窗口准备好
    time.sleep(0.5)

    # 输入文本，每个字符间隔 0.1 秒
    pyautogui.write(text, interval=0.1)

    print(f"已输入文本: {text}")
