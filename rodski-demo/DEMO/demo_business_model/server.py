#!/usr/bin/env python3
"""Dependency-free local HTTP mock for the demo_business_model login flow.

Run from the repository root with:
    python3 rodski-demo/DEMO/demo_business_model/server.py

POST /api/login accepts JSON {"username": ..., "password": ...} and returns
one of the three login_status values consumed by model/model.xml.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RodSki 登录业务流 Demo</title>
  <style>
    body { max-width: 34rem; margin: 3rem auto; padding: 0 1rem;
           font: 16px/1.5 system-ui, sans-serif; color: #172033; }
    label { display: block; margin: 1rem 0 .25rem; }
    input, button { box-sizing: border-box; width: 100%; padding: .65rem; }
    button { margin-top: 1rem; cursor: pointer; }
    pre { padding: 1rem; background: #f2f4f8; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>登录业务流 Mock</h1>
  <p>成功账号：admin / 123456；锁定账号：locked / 任意密码。</p>
  <form id="login-form">
    <label for="username">用户名</label>
    <input id="username" name="username" value="admin" autocomplete="username">
    <label for="password">密码</label>
    <input id="password" name="password" type="password" value="123456"
           autocomplete="current-password">
    <button type="submit">调用 POST /api/login</button>
  </form>
  <pre id="result" aria-live="polite">等待提交</pre>
  <script>
    document.querySelector('#login-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const response = await fetch('/api/login', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: form.get('username'), password: form.get('password')})
      });
      const body = await response.json();
      document.querySelector('#result').textContent =
        `HTTP ${response.status}\\n${JSON.stringify(body, null, 2)}`;
    });
  </script>
</body>
</html>
"""


class LoginMockHandler(BaseHTTPRequestHandler):
    server_version = "RodSkiBusinessModelMock/1.0"

    def _send_json(self, http_status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(http_status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/health":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"success": False, "status": 404, "message": "Not found", "data": None})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/api/login":
            self._send_json(404, {"success": False, "status": 404, "message": "Not found", "data": None})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length <= 0 or content_length > 1_048_576:
            self._send_json(400, {
                "success": False, "status": 400,
                "message": "Expected a non-empty JSON request body", "data": None,
            })
            return
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {
                "success": False, "status": 400,
                "message": "Malformed JSON request body", "data": None,
            })
            return
        if not isinstance(payload, dict):
            self._send_json(400, {
                "success": False, "status": 400,
                "message": "JSON body must be an object", "data": None,
            })
            return

        username = payload.get("username")
        password = payload.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            self._send_json(400, {
                "success": False, "status": 400,
                "message": "username and password must be strings", "data": None,
            })
            return

        if username == "locked":
            self._send_json(423, {
                "success": False,
                "status": 423,
                "message": "账号已锁定",
                "data": {"login_status": "locked"},
            })
        elif username == "admin" and password == "123456":
            self._send_json(200, {
                "success": True,
                "status": 200,
                "message": "登录成功",
                "data": {"login_status": "success"},
            })
        else:
            self._send_json(401, {
                "success": False,
                "status": 401,
                "message": "用户名或密码错误",
                "data": {"login_status": "invalid_credentials"},
            })

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep the useful request/status line while avoiding the default noisy format.
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="demo_business_model 本地登录 Mock API")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="监听端口 (默认: 8000)")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), LoginMockHandler)
    print(f"登录 Mock API 已启动: http://{args.host}:{args.port} (Ctrl+C 退出)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭登录 Mock API")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
