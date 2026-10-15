#!/usr/bin/env python3
"""重建 demosite/network 模块的 data/data.sqlite（可重复执行）。

用法（仓库根目录）：python3 rodski-demo/demosite/network/data/init_data.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
SCHEMA_FILE = Path(__file__).resolve().parents[4] / "rodski" / "core" / "sqlite_schema.py"


def add_table(conn, *, name, kind, fields, rows, remark):
    conn.execute(
        "INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) "
        "VALUES(?,?,?,'standard',?)", (name, name, kind, remark))
    conn.executemany(
        "INSERT INTO rs_datatable_field(table_name,field_name,field_order) VALUES(?,?,?)",
        [(name, f, i) for i, f in enumerate(fields)])
    for data_id, values, row_remark in rows:
        if set(values) != set(fields):
            raise ValueError(f"{name}.{data_id}: 字段集合必须与 schema 一致")
        conn.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES(?,?,?)",
                     (name, data_id, row_remark))
        conn.executemany(
            "INSERT INTO rs_field(table_name,data_id,field_name,field_value) VALUES(?,?,?,?)",
            [(name, data_id, f, values[f]) for f in fields])


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    schema_module = SCHEMA_FILE.read_text(encoding="utf-8")
    start = schema_module.index('SQLITE_DDL = """') + len('SQLITE_DDL = """')
    ddl = schema_module[start:schema_module.index('"""', start)]
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(ddl)
        add_table(conn, name="LoginForm", kind="data", fields=["username", "password", "loginBtn"],
                  rows=[("L001", {"username": "admin", "password": "123456", "loginBtn": "click"}, "管理员登录")],
                  remark="demosite 登录")
        add_table(conn, name="NavMenu", kind="data", fields=["dashboard"],
                  rows=[("N_DASH", {"dashboard": "click"}, "点击看板（重新请求 /api/orders）")],
                  remark="导航")
        add_table(conn, name="Dashboard_verify", kind="verify",
                  fields=["totalOrders", "totalAmount", "firstOrderNo", "rows"],
                  rows=[("V_MOCK", {"totalOrders": "1", "totalAmount": "¥66.00",
                                    "firstOrderNo": "MOCK-0001", "rows": '{"$count": 1}'},
                         "mock_route 生效：看板只显示 mock 订单"),
                        ("V_REAL", {"totalOrders": "BLANK", "totalAmount": "BLANK",
                                    "firstOrderNo": '{"$contains": "ORD"}', "rows": '{"$count_gte": 1}'},
                         "clear_routes 后恢复真实订单（ORD 开头）")],
                  remark="看板")
        add_table(conn, name="LoginError_verify", kind="verify", fields=["message"],
                  rows=[("V_MOCK", {"message": "MOCK-拒绝登录"}, "mock 的登录失败消息")],
                  remark="登录错误提示")
        add_table(conn, name="MockResult_verify", kind="verify", fields=["pattern"],
                  rows=[("V_ORDERS", {"pattern": "**/api/orders"}, "mock_route 返回的 pattern")],
                  remark="mock_route 返回值")
        add_table(conn, name="NetResp_verify", kind="verify", fields=["status", "url", "body", "orders"],
                  rows=[("V_REAL", {"status": "200", "url": '{"$contains": "/api/orders"}',
                                    "body": '{"$contains": "ORD"}', "orders": '{"$gte": 1}'},
                         "wait_for_response 拿到真实 /api/orders 响应"),
                        ("V_MOCK", {"status": "200", "url": '{"$contains": "/api/orders"}',
                                    "body": '{"$contains": "MOCK-0001"}', "orders": '{"$lte": 1}'},
                         "wait_for_response 拿到 mock 响应")],
                  remark="wait_for_response 返回值")
        add_table(conn, name="CoverageResult_verify", kind="verify", fields=["output", "files", "avg"],
                  rows=[("V001", {"output": '{"$contains": "net_js_coverage.json"}',
                                  "files": '{"$gte": 1}', "avg": '{"$gt": 0}'},
                         "stop_js_coverage 返回统计")],
                  remark="JS 覆盖率返回值")
    print(f"Created {DB_PATH}")


if __name__ == "__main__":
    main()
