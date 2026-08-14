#!/usr/bin/env python3
"""TC_BAIDU_001 pre_process:
启动真实浏览器（加载 RodSki 插件）并打开百度首页 —— 模拟"用户装了插件后手动
打开百度搜索"的真实场景。

关键发现（诊断记录）：
Google Chrome 品牌版（Stable 渠道）从近期版本起在启动日志中明确输出：
    WARNING: --load-extension is not allowed in Google Chrome, ignoring.
这是 Chrome 官方针对命令行静默注入扩展的反滥用加固，Stable 渠道被硬编码拒绝，
与本项目脚本写法无关，无法通过调整参数绕过。

解决方案：使用 Playwright 自带的开源 Chromium（无品牌限制），
--load-extension 在其上正常生效 —— 已用 CDP 验证 service_worker.js target
真实存在，插件被浏览器真实加载。这也是本机唯一无需用户手动在 GUI 里点击
"加载已解压的扩展程序" 就能自动化验证插件的可行路径。

做法：
1. 复用 Playwright 已下载好的 Chromium 二进制（pip install playwright 后
   playwright install chromium 会下载到 ~/Library/Caches/ms-playwright/）
2. 用独立 --user-data-dir + --load-extension 启动，附加 --remote-debugging-port
   供后续步骤通过 CDP HTTP/WebSocket 操作和截图
3. 记录 PID 和调试端口，供后续步骤和 post_process 清理使用
"""
import os, sys, subprocess, time, pathlib, json
import urllib.request

PLUGIN_DIR = pathlib.Path(__file__).resolve().parents[4] / "rodski-browser-plugin"
PROFILE_DIR = pathlib.Path("/tmp/rodski_chrome_profile_baidu")
PID_FILE = pathlib.Path(__file__).resolve().parent / ".chrome_baidu.pid"
DEBUG_PORT = 9333
BAIDU_URL = "https://www.baidu.com"


def get_chromium_executable():
    """获取 Playwright 托管的 Chromium 可执行文件路径（开源无品牌限制版本）"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        return p.chromium.executable_path


def wait_for_cdp(port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def get_targets(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as r:
        return json.loads(r.read())


def main():
    if not PLUGIN_DIR.is_dir():
        print(f"❌ 插件目录不存在: {PLUGIN_DIR}", file=sys.stderr)
        sys.exit(1)
    if not (PLUGIN_DIR / "manifest.json").exists():
        print(f"❌ 插件目录缺少 manifest.json: {PLUGIN_DIR}", file=sys.stderr)
        sys.exit(1)

    try:
        chromium_path = get_chromium_executable()
    except Exception as e:
        print(f"❌ 无法定位 Playwright Chromium: {e}", file=sys.stderr)
        print("   请先执行: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(chromium_path):
        print(f"❌ Chromium 可执行文件不存在: {chromium_path}", file=sys.stderr)
        sys.exit(1)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    args = [
        chromium_path,
        f"--user-data-dir={PROFILE_DIR}",
        f"--load-extension={PLUGIN_DIR}",
        f"--remote-debugging-port={DEBUG_PORT}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,900",
        "--window-position=0,0",
        BAIDU_URL,
    ]

    print(f"使用 Playwright Chromium: {chromium_path}")
    print(f"加载插件目录: {PLUGIN_DIR}")
    print(f"命令: {' '.join(args)}")

    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    PID_FILE.write_text(str(proc.pid))
    print(f"浏览器已启动，PID={proc.pid}")

    if not wait_for_cdp(DEBUG_PORT, timeout=15):
        print(f"❌ CDP 调试端口 {DEBUG_PORT} 未就绪", file=sys.stderr)
        sys.exit(1)
    print(f"✅ CDP 调试端口 {DEBUG_PORT} 已就绪")

    time.sleep(2)

    targets = get_targets(DEBUG_PORT)
    page_targets = [t for t in targets if t.get("type") == "page"]
    sw_targets = [t for t in targets if t.get("type") == "service_worker"]

    print(f"页面标签数: {len(page_targets)}，扩展 Service Worker 数: {len(sw_targets)}")
    for t in page_targets:
        print(f"  [page] {t.get('title')!r} | {t.get('url')}")
    for t in sw_targets:
        print(f"  [service_worker] {t.get('url')}")

    if not sw_targets:
        print("❌ 未发现插件 Service Worker target，插件可能未被真实加载", file=sys.stderr)
        sys.exit(1)

    rodski_sw = next((t for t in sw_targets if "service_worker.js" in t.get("url", "")), None)
    if not rodski_sw:
        print("❌ Service Worker 存在但不是 RodSki 插件的", file=sys.stderr)
        sys.exit(1)
    print(f"✅ RodSki 插件 Service Worker 已确认加载: {rodski_sw['url']}")

    baidu_tab = next((t for t in page_targets if "baidu" in t.get("url", "").lower()), None)
    if not baidu_tab:
        print("❌ 未找到百度标签页", file=sys.stderr)
        sys.exit(1)

    result = {
        "pid": proc.pid,
        "debug_port": DEBUG_PORT,
        "tab_id": baidu_tab["id"],
        "title": baidu_tab.get("title"),
        "url": baidu_tab.get("url"),
        "extension_id": rodski_sw["url"].split("//")[1].split("/")[0],
        "profile_dir": str(PROFILE_DIR),
        "plugin_dir": str(PLUGIN_DIR),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
