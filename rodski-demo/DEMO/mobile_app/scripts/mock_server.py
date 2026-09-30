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

响应延迟（v11.7.0 自动等待验收，让 App 端呈现真实异步）：
  MOCK_DELAY_MS          登录与订单接口在响应前 sleep 的毫秒数（默认 0 = 立即响应，行为不变）
  MOCK_LOGIN_DELAY_MS    仅覆盖 /api/login 的延迟（未设置时取 MOCK_DELAY_MS）
  MOCK_ORDERS_DELAY_MS   仅覆盖 /api/orders 的延迟（未设置时取 MOCK_DELAY_MS）
  注意：App 的 OkHttp 默认 readTimeout=10s，延迟 >10s 时 App 侧表现为请求失败
  （登录页显示"网络错误"、订单列表保持为空），即元素永远不会出现。
"""
from __future__ import annotations

import argparse
import os
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

VALID_USERS = {"demo": "demo123"}

ORDERS = [
    {"order_id": "SO-20260601-001", "customer": "张三", "amount": 1299.00, "status": "已发货"},
    {"order_id": "SO-20260601-002", "customer": "李四", "amount": 458.50, "status": "待付款"},
    {"order_id": "SO-20260601-003", "customer": "王五", "amount": 8800.00, "status": "已完成"},
]


def _delay_ms(specific_env: str) -> int:
    """读取接口延迟（毫秒）：专用变量优先，否则取 MOCK_DELAY_MS，默认 0。"""
    raw = os.environ.get(specific_env)
    if raw is None or raw.strip() == "":
        raw = os.environ.get("MOCK_DELAY_MS", "0")
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _sleep_before_response(specific_env: str) -> None:
    ms = _delay_ms(specific_env)
    if ms > 0:
        time.sleep(ms / 1000.0)


@app.post("/api/login")
def login():
    _sleep_before_response("MOCK_LOGIN_DELAY_MS")
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
    _sleep_before_response("MOCK_ORDERS_DELAY_MS")
    return jsonify({"success": True, "data": ORDERS})


@app.get("/health")
def health():
    return jsonify({"ok": True})


def main() -> None:
    parser = argparse.ArgumentParser(description="RodSki mobile demo mock backend")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    args = parser.parse_args()
    print(
        f"mock backend 启动: http://{args.host}:{args.port}  有效账号 demo/demo123  "
        f"延迟 login={_delay_ms('MOCK_LOGIN_DELAY_MS')}ms orders={_delay_ms('MOCK_ORDERS_DELAY_MS')}ms",
        flush=True,
    )
    # threaded=True：延迟响应期间 /health 等请求不被阻塞
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
