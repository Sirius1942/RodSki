#!/usr/bin/env python3
"""RodSki mobile demo 的 mock 后端服务。

为真机上的 com.rodski.demo（demo_android_app）提供登录与订单接口，
使 Android 真机 RodSki 验收无需依赖真实业务后端。

接口契约（对齐 demo_android_app/.../ApiService.kt）：
  POST /api/login   body={"username","password"}
      -> {"success":bool,"status":int,"message":str,"data":{...}|null}
  GET  /api/orders
      -> {"success":bool,"data":[{"order_id","customer","amount","status"},...]}

有效账号：demo / demo123

启动：
  python3 rodski-demo/DEMO/mobile_app/scripts/mock_server.py [--host 0.0.0.0] [--port 8000]

真机连通（USB，推荐，免局域网 IP 漂移）：
  adb reverse tcp:8000 tcp:8000
  # APK 的 API_BASE_URL 指向 http://127.0.0.1:8000 即可命中本机服务
"""
from __future__ import annotations

import argparse

from flask import Flask, jsonify, request

app = Flask(__name__)

VALID_USERS = {"demo": "demo123"}

ORDERS = [
    {"order_id": "SO-20260601-001", "customer": "张三", "amount": 1299.00, "status": "已发货"},
    {"order_id": "SO-20260601-002", "customer": "李四", "amount": 458.50, "status": "待付款"},
    {"order_id": "SO-20260601-003", "customer": "王五", "amount": 8800.00, "status": "已完成"},
]


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")
    if VALID_USERS.get(username) == password:
        return jsonify({
            "success": True,
            "status": 200,
            "message": "登录成功",
            "data": {"username": username},
        })
    return jsonify({
        "success": False,
        "status": 401,
        "message": "用户名或密码错误",
        "data": None,
    })


@app.get("/api/orders")
def orders():
    return jsonify({"success": True, "data": ORDERS})


@app.get("/health")
def health():
    return jsonify({"ok": True})


def main() -> None:
    parser = argparse.ArgumentParser(description="RodSki mobile demo mock backend")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    args = parser.parse_args()
    print(f"mock backend 启动: http://{args.host}:{args.port}  有效账号 demo/demo123")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
