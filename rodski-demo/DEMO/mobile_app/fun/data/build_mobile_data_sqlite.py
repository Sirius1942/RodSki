#!/usr/bin/env python3
"""Build the RodSki mobile demo SQLite data file.

This script creates data/data.sqlite as the only test data file for the
mobile_app demo module. It intentionally does not generate data.xml or
data_verify.xml.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"


SCHEMA = """
CREATE TABLE rs_datatable (
    table_name TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    table_kind TEXT NOT NULL,
    row_mode TEXT NOT NULL,
    remark TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rs_datatable_field (
    table_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (table_name, field_name)
);

CREATE TABLE rs_row (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    remark TEXT DEFAULT '',
    PRIMARY KEY (table_name, data_id)
);

CREATE TABLE rs_field (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    PRIMARY KEY (table_name, data_id, field_name)
);
"""


def add_table(
    conn: sqlite3.Connection,
    table_name: str,
    model_name: str,
    table_kind: str,
    fields: list[str],
    rows: list[tuple[str, str, dict[str, str]]],
    remark: str,
) -> None:
    conn.execute(
        """
        INSERT INTO rs_datatable(table_name, model_name, table_kind, row_mode, remark)
        VALUES (?, ?, ?, 'standard', ?)
        """,
        (table_name, model_name, table_kind, remark),
    )

    for order, field_name in enumerate(fields):
        conn.execute(
            """
            INSERT INTO rs_datatable_field(table_name, field_name, field_order)
            VALUES (?, ?, ?)
            """,
            (table_name, field_name, order),
        )

    expected = set(fields)
    for data_id, row_remark, values in rows:
        missing = expected - set(values)
        extra = set(values) - expected
        if missing or extra:
            raise ValueError(
                f"{table_name}.{data_id} field mismatch: "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )

        conn.execute(
            "INSERT INTO rs_row(table_name, data_id, remark) VALUES (?, ?, ?)",
            (table_name, data_id, row_remark),
        )
        for field_name in fields:
            conn.execute(
                """
                INSERT INTO rs_field(table_name, data_id, field_name, field_value)
                VALUES (?, ?, ?, ?)
                """,
                (table_name, data_id, field_name, values[field_name]),
            )


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)

        # 登录输入数据：成功账号 demo/demo123（对齐 mock_server）
        # 注：LoginScreen 模型含 errorMsg 元素（验证用），type 批量会遍历所有模型元素，
        # 故输入行需显式给 errorMsg=BLANK 让 type 跳过它。
        add_table(
            conn,
            table_name="LoginScreen",
            model_name="LoginScreen",
            table_kind="data",
            fields=["username", "password", "loginBtn", "errorMsg"],
            rows=[
                (
                    "L001",
                    "正常登录",
                    {"username": "demo", "password": "demo123", "loginBtn": "click", "errorMsg": "BLANK"},
                ),
                (
                    "L002",
                    "错误密码",
                    {"username": "demo", "password": "wrong_pwd", "loginBtn": "click", "errorMsg": "BLANK"},
                ),
            ],
            remark="Mobile demo 登录输入数据",
        )

        # 登录失败验证：errorMsg 文案（其余模型元素 BLANK 跳过验证）
        add_table(
            conn,
            table_name="LoginScreen_verify",
            model_name="LoginScreen",
            table_kind="verify",
            fields=["username", "password", "loginBtn", "errorMsg"],
            rows=[
                (
                    "V002",
                    "登录失败验证",
                    {"username": "BLANK", "password": "BLANK", "loginBtn": "BLANK",
                     "errorMsg": "用户名或密码错误"},
                ),
            ],
            remark="Mobile demo 登录失败验证数据",
        )

        # 主页验证：欢迎文案（orderListBtn BLANK 跳过验证）
        add_table(
            conn,
            table_name="HomeScreen_verify",
            model_name="HomeScreen",
            table_kind="verify",
            fields=["welcomeText", "orderListBtn"],
            rows=[
                ("VH001", "登录成功验证", {"welcomeText": "欢迎，demo", "orderListBtn": "BLANK"}),
            ],
            remark="Mobile demo 主页验证数据",
        )

        # 主页操作：点击"查看订单"（HomeScreen 模型含 welcomeText，type 需给它 BLANK）
        add_table(
            conn,
            table_name="HomeScreen",
            model_name="HomeScreen",
            table_kind="data",
            fields=["welcomeText", "orderListBtn"],
            rows=[
                ("H001", "进入订单列表", {"welcomeText": "BLANK", "orderListBtn": "click"}),
            ],
            remark="Mobile demo 主页操作数据",
        )

        # 订单列表操作：点击第一条订单（OrderListScreen 模型含 orderList，type 需给它 BLANK）
        add_table(
            conn,
            table_name="OrderListScreen",
            model_name="OrderListScreen",
            table_kind="data",
            fields=["orderList", "firstOrderItem"],
            rows=[
                ("O001", "打开第一条订单", {"orderList": "BLANK", "firstOrderItem": "click"}),
            ],
            remark="Mobile demo 订单列表操作数据",
        )

        # 订单详情验证：第一条订单字段（对齐 mock_server ORDERS[0]）
        # amount 在 App 端可能带格式化，BLANK 跳过避免脆弱断言
        add_table(
            conn,
            table_name="OrderDetailScreen_verify",
            model_name="OrderDetailScreen",
            table_kind="verify",
            fields=["orderNo", "customerName", "amount", "status"],
            rows=[
                (
                    "VD001",
                    "订单详情验证",
                    {
                        "orderNo": "SO-20260601-001",
                        "customerName": "张三",
                        "amount": "BLANK",
                        "status": "已发货",
                    },
                ),
            ],
            remark="Mobile demo 订单详情验证数据",
        )

        conn.commit()

    print(f"created {DB_PATH}")


if __name__ == "__main__":
    main()
