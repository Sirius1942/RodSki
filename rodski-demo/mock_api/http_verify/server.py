#!/usr/bin/env python3
"""http_verify 模块自带的无依赖 HTTP Mock（端口 18150~18159，默认 18150）。

用法（仓库根目录）：
    python3 rodski-demo/mock_api/http_verify/server.py [--port 18150]

接口：
    GET  /health              → 200 {"ok": true}
    GET  /api/profile         → 200 用户资料（响应体不含 status 字段）
    GET  /api/missing         → 404 {"error": "not_found", ...}
    GET  /api/order           → 200，响应体自带业务字段 "status": "shipped"（与 HTTP 状态码同名冲突）
    GET  /api/items           → 200 数值/字符串/数组字段（用于 $gt/$gte/$lt/$lte/$contains）
    GET  /api/fields          → 200 含空串、null、普通值字段（用于 verify 侧 BLANK/NULL/NONE）
    POST /api/login           → 200 {"username": ..., "token": "demo_token"}（文档 §8.2 示例接口）
    POST /api/echo            → 200 回显请求体，并对 nickname/remark/memo 字段给出
                                 <字段>_kind = empty_string / null / absent / value
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

ECHO_FIELDS = ("nickname", "remark", "memo")


def _kind(body: dict, key: str) -> str:
    if key not in body:
        return "absent"
    value = body[key]
    if value is None:
        return "null"
    if value == "":
        return "empty_string"
    return "value"


class Handler(BaseHTTPRequestHandler):
    server_version = "RodskiHttpVerify/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:  # 静默
        pass

    def _send(self, status: int, payload: Any) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send(200, {"ok": True})
        elif path == "/api/profile":
            self._send(200, {"id": 1, "name": "Alice", "age": 30, "score": 88.5,
                             "email": "alice@example.com", "profile": {"city": "Shanghai"}})
        elif path == "/api/missing":
            self._send(404, {"error": "not_found", "message": "user not found"})
        elif path == "/api/order":
            self._send(200, {"order_no": "ORD-1001", "status": "shipped"})
        elif path == "/api/items":
            self._send(200, {"count": 3, "price": 100, "title": "Order list /order/2026",
                             "names": ["apple", "banana", "cherry"], "ids": [1, 2, 3],
                             "items": [{"sku": "A"}, {"sku": "B"}, {"sku": "C"}]})
        elif path == "/api/fields":
            self._send(200, {"empty_field": "", "null_field": None, "text_field": "hello"})
        else:
            self._send(404, {"error": "no_route", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            self._send(400, {"error": "bad_json", "raw": raw.decode("utf-8", "replace")})
            return
        if not isinstance(body, dict):
            body = {"_non_object_body": body}
        if path == "/api/echo":
            payload = {f"{key}_kind": _kind(body, key) for key in ECHO_FIELDS}
            payload["raw_keys"] = ",".join(sorted(body.keys()))
            payload["received"] = body
            self._send(200, payload)
        elif path == "/api/login":
            if body.get("username") == "admin" and body.get("password") == "admin123":
                self._send(200, {"username": "admin", "token": "demo_token"})
            else:
                self._send(401, {"error": "bad_credentials"})
        else:
            self._send(404, {"error": "no_route", "path": path})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18150)
    args = parser.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"http_verify mock listening on http://{args.host}:{args.port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
