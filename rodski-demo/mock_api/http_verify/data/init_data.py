#!/usr/bin/env python3
"""重建 http_verify 模块的 data/data.sqlite 与被测 SQLite 库 verify_ops.db（可重复执行）。

用法（仓库根目录）：python3 rodski-demo/mock_api/http_verify/data/init_data.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
BIZ_DB_PATH = MODULE_DIR / "verify_ops.db"
SCHEMA_FILE = Path(__file__).resolve().parents[4] / "rodski" / "core" / "sqlite_schema.py"
BASE = "http://127.0.0.1:18150"

OPS = {  # F041 正向基准行
    "count": '{"$gte": 3}',
    "price": '{"$gt": 99}',
    "title": '{"$contains": "/order/"}',
    "names": '{"$contains": "banana"}',
    "ids": '{"$contains": 2}',
    "items_len": '{"$lte": 3}',
}


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


def build_biz_db() -> None:
    if BIZ_DB_PATH.exists():
        BIZ_DB_PATH.unlink()
    with sqlite3.connect(BIZ_DB_PATH) as conn:
        conn.execute("CREATE TABLE orders (order_no TEXT PRIMARY KEY, qty INTEGER, amount REAL, remark TEXT)")
        conn.executemany("INSERT INTO orders VALUES (?,?,?,?)", [
            ("ORD-2001", 8, 520.5, "加急订单"),
            ("ORD-2002", 1, 9.9, "普通订单"),
        ])


def build_data() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    schema_module = SCHEMA_FILE.read_text(encoding="utf-8")
    start = schema_module.index('SQLITE_DDL = """') + len('SQLITE_DDL = """')
    ddl = schema_module[start:schema_module.index('"""', start)]
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(ddl)

        # ── F044：文档 §8.2 示例照写 ──
        add_table(conn, name="LoginAPI", kind="data", fields=["username", "password"],
                  rows=[("D001", {"username": "admin", "password": "admin123"}, "管理员登录")],
                  remark="GUIDE §8.2 示例数据表")
        add_table(conn, name="LoginAPI_verify", kind="verify", fields=["status", "username"],
                  rows=[("V001", {"status": "200", "username": "admin"}, "GUIDE §8.2 示例验证表"),
                        ("V_BAD_STATUS", {"status": "500", "username": "admin"},
                         "status 列写错（实际 200），按 CORE §3.3 必须失败")],
                  remark="GUIDE §8.2 示例验证表：status=HTTP 状态码 + 响应字段")

        add_table(conn, name="HttpGet", kind="data", fields=["_url"],
                  rows=[(k, {"_url": f"{BASE}{p}"}, p) for k, p in (
                      ("PROFILE", "/api/profile"), ("MISSING", "/api/missing"),
                      ("ORDER", "/api/order"), ("ITEMS", "/api/items"), ("FIELDS", "/api/fields"))],
                  remark="GET 请求地址")

        prof = {"status": "200", "name": "Alice", "age": "30", "score": "88.5",
                "email": "alice@example.com", "city": "Shanghai"}
        add_table(conn, name="ProfileResp_verify", kind="verify",
                  fields=["status", "name", "age", "score", "email", "city"],
                  rows=[("V_OK", dict(prof), "状态码 + 字面值全部匹配"),
                        ("N_STATUS", {**prof, "status": "201"}, "状态码不匹配，必须失败"),
                        ("N_NAME", {**prof, "name": "Bob"}, "字段值不匹配，必须失败")],
                  remark="/api/profile 响应校验")
        add_table(conn, name="ProfileSubset_verify", kind="verify", fields=["name", "ghost"],
                  rows=[("V_GHOST", {"name": "Alice", "ghost": "no-such-field-in-model"},
                         "subset：只校验 name；模型未定义字段 ghost 跳过（CORE §4.7.4-3）"),
                        ("N_NAME", {"name": "Bob", "ghost": "no-such-field-in-model"},
                         "subset：声明字段 name 不匹配必须失败")],
                  remark="match_mode=subset 验证")

        add_table(conn, name="MissingResp_verify", kind="verify", fields=["status", "error", "message"],
                  rows=[("V404", {"status": "404", "error": "not_found", "message": "user not found"}, "404 响应")],
                  remark="/api/missing 响应校验")

        add_table(conn, name="OrderResp_verify", kind="verify", fields=["status", "order_no"],
                  rows=[("V_HTTP", {"status": "200", "order_no": "ORD-1001"},
                         "status 列 = HTTP 状态码（CORE §3.3）"),
                        ("N_BODY", {"status": "shipped", "order_no": "ORD-1001"},
                         "status 列写成响应体同名字段值，按文档应失败")],
                  remark="/api/order：响应体自带 status 字段")

        items = [("V_OPS", dict(OPS), "$gte/$gt/$contains(串)/$contains(数组)/$lte 全部满足"),
                 ("V_OPS2", {"count": '{"$lt": 4}', "price": '{"$lte": 100}',
                             "title": '{"$contains": "Order"}', "names": '{"$contains": "apple"}',
                             "ids": '{"$contains": 3}', "items_len": '{"$gte": 3}'},
                  "$lt/$lte 边界相等/$contains 全部满足")]
        for data_id, field, value, remark in (
                ("N_GT", "price", '{"$gt": 100}', "$gt 边界相等应失败"),
                ("N_GTE", "count", '{"$gte": 4}', "$gte 应失败"),
                ("N_LT", "count", '{"$lt": 3}', "$lt 边界相等应失败"),
                ("N_LTE", "price", '{"$lte": 99}', "$lte 应失败"),
                ("N_CONTAINS_STR", "title", '{"$contains": "/user/"}', "字符串不包含应失败"),
                ("N_CONTAINS_ARR", "names", '{"$contains": "durian"}', "数组不包含应失败")):
            items.append((data_id, {**OPS, field: value}, remark))
        add_table(conn, name="ItemsResp_verify", kind="verify",
                  fields=["count", "price", "title", "names", "ids", "items_len"], rows=items,
                  remark="F041 接口断言操作符")

        add_table(conn, name="FieldsResp_verify", kind="verify",
                  fields=["empty_field", "null_field", "text_field"],
                  rows=[("V_SPECIAL", {"empty_field": "BLANK", "null_field": "NULL", "text_field": "hello"},
                         "BLANK=期望空串，NULL=期望 null"),
                        ("V_NONE_SKIP", {"empty_field": "BLANK", "null_field": "NULL", "text_field": "NONE"},
                         "NONE=跳过验证（CORE §4.1）"),
                        ("N_BLANK", {"empty_field": "BLANK", "null_field": "NULL", "text_field": "BLANK"},
                         "text_field 实际 hello，BLANK 期望空串应失败"),
                        ("N_NULL", {"empty_field": "BLANK", "null_field": "NULL", "text_field": "NULL"},
                         "text_field 实际 hello，NULL 期望 null 应失败")],
                  remark="verify 侧控制值")

        add_table(conn, name="EchoAPI", kind="data", fields=["nickname", "remark", "memo", "name"],
                  rows=[("E_BLANK", {"nickname": "BLANK", "remark": "r1", "memo": "m1", "name": "n1"}, "BLANK"),
                        ("E_NULL", {"nickname": "NULL", "remark": "r1", "memo": "m1", "name": "n1"}, "NULL"),
                        ("E_NONE", {"nickname": "NONE", "remark": "r1", "memo": "m1", "name": "n1"}, "NONE"),
                        ("E_MIX", {"nickname": "BLANK", "remark": "NULL", "memo": "NONE", "name": "mix"},
                         "同一行三种控制值")],
                  remark="F026 发送侧控制值")
        add_table(conn, name="EchoResp_verify", kind="verify",
                  fields=["nickname_kind", "remark_kind", "memo_kind", "raw_keys"],
                  rows=[("V_BLANK", {"nickname_kind": "empty_string", "remark_kind": "value",
                                     "memo_kind": "value", "raw_keys": "memo,name,nickname,remark"}, "空串"),
                        ("V_NULL", {"nickname_kind": "null", "remark_kind": "value",
                                    "memo_kind": "value", "raw_keys": "memo,name,nickname,remark"}, "null"),
                        ("V_NONE", {"nickname_kind": "absent", "remark_kind": "value",
                                    "memo_kind": "value", "raw_keys": "memo,name,remark"}, "不发送"),
                        ("V_MIX", {"nickname_kind": "empty_string", "remark_kind": "null",
                                   "memo_kind": "absent", "raw_keys": "name,nickname,remark"}, "混合")],
                  remark="server 回显的字段形态")

        add_table(conn, name="OrderDB", kind="data", fields=["query", "sql", "operation", "order_no"],
                  rows=[("Q1", {"query": "by_no", "sql": "BLANK", "operation": "BLANK", "order_no": "ORD-2001"},
                         "查询 ORD-2001")],
                  remark="F052 DB 查询")
        lit = {"order_no": "ORD-2001", "qty": "8", "amount": "520.5", "remark": "加急订单"}
        add_table(conn, name="OrderDB_verify", kind="verify", fields=["order_no", "qty", "amount", "remark"],
                  rows=[("V_LIT", dict(lit), "字面值（对照组）"),
                        ("V_OPS", {"order_no": '{"$contains": "ORD"}', "qty": '{"$gte": 5}',
                                   "amount": '{"$lt": 1000}', "remark": '{"$contains": "加急"}'},
                         "$contains/$gte/$lt"),
                        ("V_OPS2", {"order_no": "ORD-2001", "qty": '{"$gt": 7}',
                                    "amount": '{"$lte": 520.5}', "remark": "BLANK"},
                         "$gt/$lte + 字面值 + BLANK 跳过"),
                        ("N_OPS", {**lit, "qty": '{"$gt": 100}'}, "$gt 不满足应失败")],
                  remark="F052 DB verify 操作符")


def main() -> None:
    build_biz_db()
    build_data()
    print(f"Created {DB_PATH}\nCreated {BIZ_DB_PATH}")


if __name__ == "__main__":
    main()
