#!/usr/bin/env python3
"""在命令面板输入 RodSki: Refresh 并执行"""
import pyautogui, time
time.sleep(0.3)
pyautogui.typewrite('RodSki: Refresh', interval=0.05)
time.sleep(0.3)
pyautogui.press('return')
print("已执行 RodSki: Refresh")
