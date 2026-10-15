#!/usr/bin/env python3
"""Build the business-model demo data using RodSki's ordinary Data/Verify schema."""
from __future__ import annotations

import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
SCHEMA_FILE = Path(__file__).resolve().parents[4] / "rodski" / "core" / "sqlite_schema.py"

def add_table(conn: sqlite3.Connection, *, name: str, kind: str,
              fields: list[str], rows: list[tuple[str, str, dict[str, str]]],
              remark: str) -> None:
    # Follow RodSki's data-import convention: model_name mirrors table_name.
    conn.execute(
        "INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) "
        "VALUES(?,?,?,'standard',?)", (name, name, kind, remark)
    )
    conn.executemany(
        "INSERT INTO rs_datatable_field(table_name,field_name,field_order) VALUES(?,?,?)",
        [(name, field, index) for index, field in enumerate(fields)],
    )
    for data_id, row_remark, values in rows:
        if set(values) != set(fields):
            raise ValueError(f"{name}.{data_id}: row fields must match schema")
        conn.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES(?,?,?)",
                     (name, data_id, row_remark))
        conn.executemany(
            "INSERT INTO rs_field(table_name,data_id,field_name,field_value) VALUES(?,?,?,?)",
            [(name, data_id, field, values[field]) for field in fields],
        )


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as conn:
        # Use the exact DDL owned by RodSki, not a forked demo schema.
        schema_module = SCHEMA_FILE.read_text(encoding="utf-8")
        ddl_start = schema_module.index('SQLITE_DDL = """') + len('SQLITE_DDL = """')
        ddl_end = schema_module.index('"""', ddl_start)
        conn.executescript(schema_module[ddl_start:ddl_end])
        add_table(
            conn, name="login_flow", kind="data",
            fields=["username", "password"],
            rows=[
                ("LOGIN_OK_01", "valid demo credentials", {
                    "username": "admin", "password": "123456"}),
                ("LOGIN_INVALID_01", "invalid password", {
                    "username": "admin", "password": "wrong-password"}),
                ("LOGIN_LOCKED_01", "locked account response", {
                    "username": "locked", "password": "any-password"}),
            ],
            remark="login_flow business-model input rows; ordinary Data table",
        )
        add_table(
            conn, name="login_flow_verify", kind="verify",
            fields=["login_status", "message", "expected_path"],
            rows=[
                ("LOGIN_OK_01", "basic flow expectation", {
                    "login_status": "success", "message": "登录成功",
                    "expected_path": "open_login>submit_login>validate_login>home"}),
                ("LOGIN_INVALID_01", "alternative flow expectation", {
                    "login_status": "invalid_credentials", "message": "用户名或密码错误",
                    "expected_path": "open_login>submit_login>validate_login>error"}),
                ("LOGIN_LOCKED_01", "locked account flow expectation", {
                    "login_status": "locked", "message": "账号已锁定",
                    "expected_path": "open_login>submit_login>validate_login>locked"}),
            ],
            remark="login_flow business-model expected rows; ordinary Verify table",
        )
    print(f"Created {DB_PATH}")
    print("Tables: login_flow (data), login_flow_verify (verify)")


if __name__ == "__main__":
    main()
