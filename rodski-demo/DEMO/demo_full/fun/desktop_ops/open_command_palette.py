#!/usr/bin/env python3
"""按 Cmd+Shift+P 打开命令面板"""
import subprocess, pyautogui, time
subprocess.run(['osascript', '-e', 'tell application "Visual Studio Code" to activate'])
time.sleep(0.5)
pyautogui.hotkey('command', 'shift', 'p')
print("已打开命令面板")
