#!/usr/bin/env python3
import subprocess, sys, os

VSCODE_CODE = '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'
code_cli = VSCODE_CODE if os.path.exists(VSCODE_CODE) else 'code'

result = subprocess.run([code_cli, '--list-extensions'], capture_output=True, text=True)
if result.returncode != 0:
    print(f"CLI 调用失败: {result.stderr}", file=sys.stderr)
    sys.exit(1)

ext_id = 'undefined_publisher.rodski-vscode'
if ext_id not in result.stdout:
    print(f"插件未安装。已安装列表:\n{result.stdout}", file=sys.stderr)
    sys.exit(1)

print(f"插件已安装: {ext_id}")
