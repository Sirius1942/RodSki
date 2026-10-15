#!/usr/bin/env python3
import subprocess, sys, os

VSCODE_CODE = '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'
code_cli = VSCODE_CODE if os.path.exists(VSCODE_CODE) else 'code'

fun_dir = os.path.dirname(os.path.abspath(__file__))
full_mod = os.path.normpath(os.path.join(fun_dir, '../../../demosite/full'))

if not os.path.isdir(full_mod):
    print(f"demosite/full 目录不存在: {full_mod}", file=sys.stderr)
    sys.exit(1)

proc = subprocess.Popen([code_cli, '--new-window', full_mod])
print(f"已启动新 Cursor 窗口 (pid={proc.pid}): {full_mod}")
