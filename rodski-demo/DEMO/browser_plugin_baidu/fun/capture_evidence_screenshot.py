#!/usr/bin/env python3
"""TC_BAIDU_004: 对当前百度页面（真实浏览器 + 已加载插件）截图，
作为"插件在真实场景下可用"的视觉证据，存入 rodski 结果目录的 screenshots/。
"""
import sys, os
from cdp_client import get_page_ws_url, CDPSession


def find_latest_result_screenshots_dir():
    result_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "result")
    )
    if not os.path.isdir(result_dir):
        os.makedirs(result_dir, exist_ok=True)
        return result_dir
    subdirs = [d for d in os.listdir(result_dir) if os.path.isdir(os.path.join(result_dir, d))]
    if not subdirs:
        return result_dir
    latest = os.path.join(result_dir, sorted(subdirs)[-1])
    shot_dir = os.path.join(latest, "screenshots")
    os.makedirs(shot_dir, exist_ok=True)
    return shot_dir


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "baidu_search_result"
    ws_url, tab_id = get_page_ws_url()
    session = CDPSession(ws_url)

    try:
        url = session.evaluate("location.href")
        title = session.evaluate("document.title")
        print(f"  📋 截图页面: {title} | {url}")

        png_bytes = session.screenshot_png_bytes()
        out_dir = find_latest_result_screenshots_dir()
        out_path = os.path.join(out_dir, f"TC_BAIDU_{label}.png")
        with open(out_path, "wb") as f:
            f.write(png_bytes)
        print(f"✅ 截图已保存: {out_path} ({len(png_bytes)} bytes)")

        # 同时保存一份到当前 fun 目录旁边，方便直接查看
        local_copy = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "result", f"TC_BAIDU_{label}_latest.png"
        )
        with open(os.path.normpath(local_copy), "wb") as f:
            f.write(png_bytes)
        print(f"   副本: {os.path.normpath(local_copy)}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
