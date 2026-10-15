#!/usr/bin/env python3
"""手动运行被测用例前启动静态页面服务：python3 fun/serve_pages.py

页面地址与 data/globalvalue.xml 的 Site.URL 一致（http://127.0.0.1:18765）。
验收脚本 debug_partial_execution/fun/dbg_harness.py 会自动启动同一服务，无需手动执行。
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 18765
PAGES = Path(__file__).resolve().parent / "pages"

if __name__ == "__main__":
    handler = partial(SimpleHTTPRequestHandler, directory=str(PAGES))
    print(f"serving {PAGES} on http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
