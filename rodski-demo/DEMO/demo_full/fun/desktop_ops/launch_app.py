#!/usr/bin/env python3
"""启动桌面应用
用法: python launch_app.py <app_path>
示例: python launch_app.py '/Applications/Visual Studio Code.app'
"""
import sys
import subprocess
import time

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python launch_app.py <app_path>")
        sys.exit(1)

    app_path = sys.argv[1]
    try:
        subprocess.Popen(['open', app_path])
        time.sleep(1)
        print(f"已启动: {app_path}")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)
