#!/usr/bin/env python3
"""data_rules 模块自带的最小 HTTP mock（127.0.0.1:18121，仅标准库）。

用法（被用例的 `run model="" data="mock_server.py ensure"` 调用，也可手动执行）:
    python3 mock_server.py ensure [tag]  # 未运行则后台启动，等待就绪；输出 JSON（带 tag 时附 "tag" 字段）
    python3 mock_server.py stop     # 停止
    python3 mock_server.py serve    # 前台运行（ensure 内部使用）

路由:
    GET  /health                → {"ok": true}
    GET  /pages/<file>          → fun/pages/<file> 静态页
    GET|POST /echo/<tag>        → 记录请求到 .runtime/requests.jsonl，并回显：
                                   {"tag", "keys"(请求体字段名逗号排序), "types"(字段:类型), <请求体字段原样>}
    GET  /fixed/specials        → 固定响应 {"v_empty": "", "v_null": null, "v_other": "xyz", "v_text": "hello"}
    POST /__shutdown            → 停止服务

空闲 600 秒无请求自动退出，避免残留进程。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

HOST, PORT = "127.0.0.1", int(os.environ.get("DATA_RULES_PORT", "18121"))
FUN = Path(__file__).resolve().parent
MODULE = FUN.parent
RUNTIME = MODULE / ".runtime"
LOG = RUNTIME / "requests.jsonl"
IDLE_SECONDS = 600

_last_hit = time.time()
_lock = threading.Lock()


def _type_name(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "str"
    return type(v).__name__


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 安静
        pass

    def _send(self, code: int, payload, ctype: str = "application/json; charset=utf-8") -> None:
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method: str) -> None:
        global _last_hit
        _last_hit = time.time()
        parts = urlsplit(self.path)
        path = parts.path
        if path == "/health":
            return self._send(200, {"ok": True})
        if path == "/__shutdown" and method == "POST":
            self._send(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if path.startswith("/pages/") and method == "GET":
            f = (FUN / "pages" / path[len("/pages/"):]).resolve()
            if f.is_file() and FUN in f.parents:
                return self._send(200, f.read_bytes(), "text/html; charset=utf-8")
            return self._send(404, {"error": "not found"})
        if path == "/fixed/specials":
            return self._send(200, {"v_empty": "", "v_null": None, "v_other": "xyz", "v_text": "hello"})
        if path.startswith("/echo/"):
            tag = path[len("/echo/"):]
            raw = b""
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                raw = self.rfile.read(length)
            body = {}
            if raw:
                try:
                    body = json.loads(raw.decode("utf-8"))
                except ValueError:
                    body = {"_raw": raw.decode("utf-8", "replace")}
            if not isinstance(body, dict):
                body = {"_body": body}
            body.update(dict(parse_qsl(parts.query, keep_blank_values=True)))
            record = {"ts": time.time(), "tag": tag, "method": method, "path": self.path,
                      "raw": raw.decode("utf-8", "replace"), "body": body}
            with _lock:
                RUNTIME.mkdir(exist_ok=True)
                with LOG.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            resp = {"tag": tag,
                    "keys": ",".join(sorted(body)),
                    "types": ",".join(f"{k}:{_type_name(body[k])}" for k in sorted(body))}
            resp.update(body)
            return self._send(200, resp)
        return self._send(404, {"error": "unknown path", "path": path})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def _healthy() -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


def serve() -> None:
    srv = ThreadingHTTPServer((HOST, PORT), Handler)

    def idle_watch():
        while True:
            time.sleep(5)
            if time.time() - _last_hit > IDLE_SECONDS:
                srv.shutdown()
                return

    threading.Thread(target=idle_watch, daemon=True).start()
    srv.serve_forever()


def ensure(tag: str = "") -> int:
    RUNTIME.mkdir(exist_ok=True)
    if not _healthy():
        log = (RUNTIME / "server.log").open("a")
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "serve"],
                         stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                         cwd=str(FUN), start_new_session=True)
        for _ in range(50):
            if _healthy():
                break
            time.sleep(0.2)
    ok = _healthy()
    out = {"server": "up" if ok else "down", "port": PORT}
    if tag:
        out["tag"] = tag  # 供 F055 作为可辨识的步骤返回值
    print(json.dumps(out))
    return 0 if ok else 1


def stop() -> int:
    try:
        req = urllib.request.Request(f"http://{HOST}:{PORT}/__shutdown", data=b"", method="POST")
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        pass
    print(json.dumps({"server": "stopped"}))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ensure"
    if cmd == "serve":
        serve()
    elif cmd == "stop":
        sys.exit(stop())
    else:
        sys.exit(ensure(sys.argv[2] if len(sys.argv) > 2 else ""))
