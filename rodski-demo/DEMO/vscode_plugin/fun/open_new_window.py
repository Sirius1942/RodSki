#!/usr/bin/env python3
import subprocess, sys, os

VSCODE_CODE = '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'
code_cli = VSCODE_CODE if os.path.exists(VSCODE_CODE) else 'code'

fun_dir = os.path.dirname(os.path.abspath(__file__))
demo_full = os.path.normpath(os.path.join(fun_dir, '../../demo_full'))

if not os.path.isdir(demo_full):
    print(f"demo_full 目录不存在: {demo_full}", file=sys.stderr)
    sys.exit(1)

proc = subprocess.Popen([code_cli, '--new-window', demo_full])
print(f"已启动新 Cursor 窗口 (pid={proc.pid}): {demo_full}")
