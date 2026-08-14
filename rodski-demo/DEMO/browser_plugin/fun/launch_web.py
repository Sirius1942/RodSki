#!/usr/bin/env python3
"""启动 rodski-web 用于浏览器截图用例（后台进程）"""
import os, sys, time, subprocess, signal, pathlib

WEB_DIR = pathlib.Path(__file__).resolve().parents[4] / 'web'
PID_FILE = pathlib.Path(__file__).resolve().parent / '.rodski_web.pid'

def is_running():
    try:
        import requests
        r = requests.get('http://localhost:5002/health', timeout=2)
        return r.status_code == 200
    except Exception:
        return False

if is_running():
    print('rodski-web 已在运行，跳过启动')
    # 写 pid=0 表示非本脚本启动
    PID_FILE.write_text('0')
    sys.exit(0)

if not WEB_DIR.is_dir():
    print(f'❌ web 目录不存在: {WEB_DIR}', file=sys.stderr)
    sys.exit(1)

proc = subprocess.Popen(
    [sys.executable, 'src/app.py'],
    cwd=str(WEB_DIR),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
PID_FILE.write_text(str(proc.pid))
print(f'rodski-web 已启动，PID={proc.pid}')

for i in range(20):
    time.sleep(0.5)
    if is_running():
        print(f'rodski-web 就绪（{(i+1)*0.5:.1f}s）')
        sys.exit(0)

print('❌ rodski-web 启动超时', file=sys.stderr)
proc.terminate()
sys.exit(1)
