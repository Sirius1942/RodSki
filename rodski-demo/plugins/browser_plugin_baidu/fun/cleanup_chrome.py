#!/usr/bin/env python3
"""post_process: 关闭 launch_chrome_with_plugin.py 启动的浏览器进程，清理临时 profile"""
import os, sys, signal, pathlib, shutil, time

PID_FILE = pathlib.Path(__file__).resolve().parent / ".chrome_baidu.pid"
PROFILE_DIR = pathlib.Path("/tmp/rodski_chrome_profile_baidu")


def main():
    if PID_FILE.exists():
        pid_str = PID_FILE.read_text().strip()
        try:
            pid = int(pid_str)
            os.kill(pid, signal.SIGTERM)
            print(f"已发送 SIGTERM 到浏览器进程 PID={pid}")
            time.sleep(1)
        except (ProcessLookupError, ValueError):
            print(f"进程 {pid_str} 已不存在，跳过")
        finally:
            PID_FILE.unlink(missing_ok=True)
    else:
        print("未找到 PID 文件，跳过进程清理")

    # 清理临时 profile（不影响用户真实 Chrome 数据，这个目录是本次测试专用的）
    if PROFILE_DIR.exists():
        try:
            shutil.rmtree(PROFILE_DIR)
            print(f"已清理临时 profile: {PROFILE_DIR}")
        except Exception as e:
            print(f"清理 profile 目录失败（不影响测试结果）: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
