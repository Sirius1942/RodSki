#!/usr/bin/env python3
"""重建 REQ-012 被测模块的 data.sqlite（使用 RodSki 公共 SQLite schema）。

用法：python3 rodski-demo/local/debug_partial_execution_targets/data/init_data.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
SCHEMA_FILE = Path(__file__).resolve().parents[4] / "rodski" / "core" / "sqlite_schema.py"


def add_table(conn: sqlite3.Connection, *, name: str, kind: str,
              fields: list[str], rows: list[tuple[str, dict[str, str]]], remark: str) -> None:
    conn.execute(
        "INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) "
        "VALUES(?,?,?,'standard',?)", (name, name, kind, remark)
    )
    conn.executemany(
        "INSERT INTO rs_datatable_field(table_name,field_name,field_order) VALUES(?,?,?)",
        [(name, field, index) for index, field in enumerate(fields)],
    )
    for data_id, values in rows:
        if set(values) != set(fields):
            raise ValueError(f"{name}.{data_id}: row fields must match schema")
        conn.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES(?,?,?)",
                     (name, data_id, ""))
        conn.executemany(
            "INSERT INTO rs_field(table_name,data_id,field_name,field_value) VALUES(?,?,?,?)",
            [(name, data_id, field, values[field]) for field in fields],
        )


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as conn:
        schema_module = SCHEMA_FILE.read_text(encoding="utf-8")
        ddl_start = schema_module.index('SQLITE_DDL = """') + len('SQLITE_DDL = """')
        ddl_end = schema_module.index('"""', ddl_start)
        conn.executescript(schema_module[ddl_start:ddl_end])

        users = range(1, 6)
        add_table(conn, name="LoginForm", kind="data",
                  fields=["username", "password", "loginBtn"],
                  rows=[(f"USER00{i}", {"username": f"user{i}", "password": f"pass{i}",
                                         "loginBtn": "click"}) for i in users],
                  remark="form.html 输入行；USER001~005 同时是 DBG_ROWS 的数据行")
        add_table(conn, name="LoginResult_verify", kind="verify",
                  fields=["result"],
                  rows=[(f"USER00{i}", {"result": f"OK:user{i}"}) for i in users],
                  remark="form.html 点击登录后的结果文本")
        add_table(conn, name="BrokenForm", kind="data",
                  fields=["missingBtn"],
                  rows=[("D001", {"missingBtn": "click"})],
                  remark="AC-025：定位不存在的 missing_button")
        add_table(conn, name="BuyerForm", kind="data",
                  fields=["msg", "sendBtn"],
                  rows=[("B001", {"msg": "hello-seller", "sendBtn": "click"})],
                  remark="AC-029 买家浏览器输入")
        add_table(conn, name="BuyerResult_verify", kind="verify",
                  fields=["status"],
                  rows=[("B001", {"status": "SENT:hello-seller"})],
                  remark="AC-029 买家浏览器结果")
        add_table(conn, name="SellerPage_verify", kind="verify",
                  fields=["title", "inbox"],
                  rows=[("S001", {"title": "Seller Console", "inbox": "empty"})],
                  remark="AC-029 卖家浏览器不受买家操作影响")
        add_table(conn, name="debug_flow", kind="data",
                  fields=["vin"],
                  rows=[("BIZ001", {"vin": "LSVAA4182E2000001"})],
                  remark="debug_flow 业务模型输入")
        add_table(conn, name="debug_flow_verify", kind="verify",
                  fields=["expected_path"],
                  rows=[("BIZ001", {"expected_path": "open>fill_vin>submit>confirm"})],
                  remark="debug_flow 业务模型期望路径")
        add_table(conn, name="invoice_flow", kind="data",
                  fields=["invoice_type"],
                  rows=[("INV001", {"invoice_type": "platform"})],
                  remark="invoice_flow 业务模型输入")
        add_table(conn, name="invoice_flow_verify", kind="verify",
                  fields=["expected_path"],
                  rows=[("INV001", {"expected_path": "inv_start>inv_platform"})],
                  remark="invoice_flow 业务模型期望路径")
    print(f"Created {DB_PATH}")


if __name__ == "__main__":
    main()
