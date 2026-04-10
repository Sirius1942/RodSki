#!/usr/bin/env python3
"""
桌面自动化 - 快捷键组合脚本
使用 pyautogui 执行键盘快捷键

用法: python key_combo.py "Ctrl+A"
支持的组合键: Ctrl+A, Ctrl+C, Ctrl+V, Alt+F4 等
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
        print("用法: python key_combo.py <快捷键>")
        print("示例: python key_combo.py Ctrl+A")
        sys.exit(1)

    combo = sys.argv[1]

    # 等待准备
    time.sleep(0.3)

    # 解析快捷键组合
    keys = combo.split('+')
    keys = [k.strip().lower() for k in keys]

    # 执行快捷键
    try:
        pyautogui.hotkey(*keys)
        print(f"已执行快捷键: {combo}")
    except Exception as e:
        print(f"执行快捷键失败: {e}")
        sys.exit(1)
