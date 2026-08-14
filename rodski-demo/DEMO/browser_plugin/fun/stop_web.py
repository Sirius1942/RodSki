#!/usr/bin/env python3
"""停止由 launch_web.py 启动的 rodski-web 进程"""
import os, sys, pathlib, signal

PID_FILE = pathlib.Path(__file__).resolve().parent / '.rodski_web.pid'

if not PID_FILE.exists():
    print('未找到 PID 文件，rodski-web 可能不是由 launch_web.py 启动的')
    sys.exit(0)

pid_str = PID_FILE.read_text().strip()
if pid_str == '0':
    print('rodski-web 不是由本测试启动的，跳过停止')
    PID_FILE.unlink(missing_ok=True)
    sys.exit(0)

try:
    pid = int(pid_str)
    os.kill(pid, signal.SIGTERM)
    print(f'rodski-web (PID={pid}) 已停止')
except (ProcessLookupError, ValueError):
    print(f'进程 {pid_str} 已不存在，跳过')
finally:
    PID_FILE.unlink(missing_ok=True)
