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
              remark: str, model_name: str = "") -> None:
    # Follow RodSki's data-import convention: model_name mirrors table_name.
    # Data-driven tables (kind="driver", CORE §7.8) store the bound case uid instead.
    conn.execute(
        "INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) "
        "VALUES(?,?,?,'standard',?)", (name, model_name or name, kind, remark)
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
                ("LOGIN_INVALID_01", "基础 DataID：错误密码；LoginInvalidMatrix[wrong_pwd] 沿用", {
                    "username": "admin", "password": "wrong-password"}),
                ("LOGIN_INVALID_02", "login_invalid_matrix_suite / LoginInvalidMatrix[short_pwd]：密码过短", {
                    "username": "admin", "password": "123"}),
                ("LOGIN_INVALID_03", "login_invalid_matrix_suite / LoginInvalidMatrix[wrong_user]：用户不存在", {
                    "username": "nobody", "password": "123456"}),
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
                ("LOGIN_INVALID_02", "LoginInvalidMatrix[short_pwd] 期望", {
                    "login_status": "invalid_credentials", "message": "用户名或密码错误",
                    "expected_path": "open_login>submit_login>validate_login>error"}),
                ("LOGIN_INVALID_03", "LoginInvalidMatrix[wrong_user] 期望", {
                    "login_status": "invalid_credentials", "message": "用户名或密码错误",
                    "expected_path": "open_login>submit_login>validate_login>error"}),
                ("LOGIN_LOCKED_01", "locked account flow expectation", {
                    "login_status": "locked", "message": "账号已锁定",
                    "expected_path": "open_login>submit_login>validate_login>locked"}),
            ],
            remark="login_flow business-model expected rows; ordinary Verify table",
        )
        # 计划级数据驱动（CORE §7.8）：作用于调用业务模型的用例，只替换 business_call 的 input / expect
        cols = ["login_flow.LOGIN_INVALID_01", "login_flow_verify.LOGIN_INVALID_01"]
        add_table(
            conn, name="LoginInvalidMatrix", kind="driver", fields=cols,
            model_name="login_flows.xml::TC-BM-LOGIN-INVALID",
            rows=[
                ("wrong_pwd", "错误密码（沿用基础 DataID）", dict(zip(cols, ["BLANK", "BLANK"]))),
                ("short_pwd", "密码过短", dict(zip(cols, ["LOGIN_INVALID_02", "LOGIN_INVALID_02"]))),
                ("wrong_user", "用户不存在", dict(zip(cols, ["LOGIN_INVALID_03", "LOGIN_INVALID_03"]))),
            ],
            remark="错误凭据矩阵；计划 login_invalid_matrix_suite；目的：多组错误凭据都应走 F_LOGIN_INVALID 备选流",
        )
        add_table(
            conn, name="LoginPathMismatch", kind="driver", fields=cols,
            model_name="login_flows.xml::TC-BM-LOGIN-INVALID",
            rows=[
                ("still_invalid", "仍是错误凭据：通过", dict(zip(cols, ["BLANK", "BLANK"]))),
                ("actually_ok", "输入换成正确账号：实际路径 home ≠ F_LOGIN_INVALID",
                 dict(zip(cols, ["LOGIN_OK_01", "BLANK"]))),
            ],
            remark="负向：flow 不随数据改变；计划 login_path_mismatch_suite；actually_ok 实例实际走 home，应判失败",
        )
    print(f"Created {DB_PATH}")
    print("Tables: login_flow (data), login_flow_verify (verify), LoginInvalidMatrix / LoginPathMismatch (driver)")


if __name__ == "__main__":
    main()
