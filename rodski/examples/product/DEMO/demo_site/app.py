#!/usr/bin/env python3
"""RodSki DEMO：本地登录演示站点（与 model.xml / Login.xml / HomePage_verify 对齐）

启动（在 rodski 目录下）::

    python examples/product/DEMO/demo_site/app.py

默认监听 http://127.0.0.1:5555
"""
from __future__ import annotations

import sqlite3
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORT = 5555

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "demo.db"

# 与 examples/product/DEMO/demo_site/data/Login.xml 一致
_USERS = {
    "admin": "admin123",
    "testuser": "test123",
}


def _init_sqlite() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)"
        )
        cur = conn.execute("SELECT COUNT(*) FROM items")
        if cur.fetchone()[0] == 0:
            conn.execute("INSERT INTO items (name) VALUES ('demo')")
        conn.commit()
    finally:
        conn.close()


def _html_login(msg: str = "") -> bytes:
    tip = f'<p style="color:#c00">{msg}</p>' if msg else ""
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"/><title>Demo Login</title></head>
<body>
<h1>登录</h1>
{tip}
<form method="post" action="/login">
  <div><label>用户名 <input id="username" name="username" type="text" autocomplete="username"/></label></div>
  <div><label>密码 <input id="password" name="password" type="password" autocomplete="current-password"/></label></div>
  <button type="submit" id="login-btn">登录</button>
</form>
</body>
</html>"""
    return page.encode("utf-8")


def _html_home(username: str) -> bytes:
    welcome = f"欢迎, {username}"
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"/><title>首页</title></head>
<body>
<div id="welcome">{welcome}</div>
<p><a href="/logout">Logout</a></p>
</body>
</html>"""
    return page.encode("utf-8")


class _Handler(BaseHTTPRequestHandler):
    server_version = "RodSkiDemo/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _get_cookie(self, name: str) -> str | None:
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        c = SimpleCookie()
        c.load(raw)
        m = c.get(name)
        return m.value if m else None

    def _send(self, code: int, body: bytes, headers: list[tuple[str, str]]) -> None:
        self.send_response(code)
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/login":
            body = _html_login()
            self._send(
                200,
                body,
                [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
            )
            return
        if path == "/home":
            user = self._get_cookie("demo_user")
            if not user:
                self._send(
                    302,
                    b"",
                    [("Location", "/login"), ("Content-Length", "0")],
                )
                return
            body = _html_home(user)
            self._send(
                200,
                body,
                [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
            )
            return
        if path == "/logout":
            self._send(
                302,
                b"",
                [
                    ("Location", "/login"),
                    ("Set-Cookie", "demo_user=; Path=/; Max-Age=0"),
                    ("Content-Length", "0"),
                ],
            )
            return
        if path == "/":
            self._send(302, b"", [("Location", "/login"), ("Content-Length", "0")])
            return
        self._send(404, b"Not Found", [("Content-Type", "text/plain"), ("Content-Length", "9")])

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/login":
            self._send(404, b"Not Found", [("Content-Type", "text/plain"), ("Content-Length", "9")])
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        data = parse_qs(body, keep_blank_values=True)
        user = (data.get("username") or [""])[0].strip()
        pwd = (data.get("password") or [""])[0]
        if user in _USERS and _USERS[user] == pwd:
            cookie = f"demo_user={user}; Path=/; HttpOnly; SameSite=Lax"
            self._send(
                302,
                b"",
                [
                    ("Location", "/home"),
                    ("Set-Cookie", cookie),
                    ("Content-Length", "0"),
                ],
            )
            return
        err = _html_login("用户名或密码错误")
        self._send(
            401,
            err,
            [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(err)))],
        )


def main() -> None:
    _init_sqlite()
    httpd = HTTPServer((HOST, PORT), _Handler)
    print(f"RodSki DEMO 站点: http://{HOST}:{PORT}/login （Ctrl+C 停止）")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
