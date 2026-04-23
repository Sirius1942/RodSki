#!/usr/bin/env python3
"""启动 VSCode 并置于前台"""
import subprocess
import time
subprocess.Popen(['open', '-a', 'Visual Studio Code', '/Users/sirius05/Documents/project/RodSki'])
time.sleep(3)
# 确保 VSCode 获得焦点
subprocess.run(['osascript', '-e', 'tell application "Visual Studio Code" to activate'])
time.sleep(1)
print("已启动 VSCode")
