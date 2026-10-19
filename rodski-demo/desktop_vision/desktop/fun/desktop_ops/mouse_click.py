#!/usr/bin/env python3
"""
桌面自动化 - 鼠标点击脚本
使用 pyautogui 在指定坐标点击鼠标

用法: python mouse_click.py <x> <y> [button]
button: left(默认), right, middle
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
    if len(sys.argv) < 3:
        print("用法: python mouse_click.py <x> <y> [button]")
        print("button: left(默认), right, middle")
        sys.exit(1)

    try:
        x = int(sys.argv[1])
        y = int(sys.argv[2])
        button = sys.argv[3] if len(sys.argv) > 3 else 'left'

        # 等待准备
        time.sleep(0.3)

        # 移动并点击
        pyautogui.click(x, y, button=button)
        print(f"已在坐标 ({x}, {y}) 执行 {button} 点击")

    except ValueError:
        print("错误: 坐标必须是整数")
        sys.exit(1)
    except Exception as e:
        print(f"点击失败: {e}")
        sys.exit(1)
