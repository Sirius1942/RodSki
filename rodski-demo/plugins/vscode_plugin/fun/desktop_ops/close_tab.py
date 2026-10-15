#!/usr/bin/env python3
"""按 Cmd+W 关闭当前标签"""
import pyautogui, time
time.sleep(0.3)
pyautogui.hotkey('command', 'w')
print("已执行 Cmd+W")
