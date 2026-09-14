#!/usr/bin/env python3
"""初始化 demo_pause_takeover 的 RodSki 测试数据文件（data/data.sqlite）。

按 RodSki v6.x 起的 schema 直插 rs_datatable / rs_row / rs_field：
  - rs_datatable: 表元数据（table_name / model_name / table_kind: data|verify / row_mode）
  - rs_row:       每张数据表内的行（data_id）
  - rs_field:     行内字段值

本 demo 自带最小数据（不依赖 demo_full 的 data.sqlite）：
  - LoginForm L001   : 登录表单批量数据（type LoginForm L001 在 part1 用）
  - TakeoverForm E001: 探索段用的边界探测数据（用户名留空 + role 选 user 后提交）
  - TakeoverForm_verify V001: 期望值即 Agent 接管后填入表单产生的 formResult 文本
                            （part2 verify 用 match_mode=subset）
  - TakeoverForm_verify V002: 期望值即探索段「空用户名提交」后的 formResult
                            （part3 后置用例严格模式校验）
  - Dashboard_verify V001   : dashboard 卡片期望值（totalOrders=3, completedOrders=2）

幂等：INSERT OR REPLACE，可反复执行。
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data.sqlite"

# 探索段「空用户名提交」后的 formResult：demosite submitForm() 用 innerHTML 拼
# 提交成功！<br>用户名: ${username}<br>角色: ${role}，text_content 读到的是拼接后的
# 纯文本（无换行标签）。用户名留空 → "用户名: " 后面直接跟 "角色: user"。
EXPLORE_EMPTY_USER_FORM_RESULT = "提交成功！用户名: 角色: user"


def _reset(conn: sqlite3.Connection) -> None:
    """删除本 demo 涉及的表行，保证重建幂等（不影响无关表）。"""
    tables = ("LoginForm", "TakeoverForm", "TakeoverForm_verify", "Dashboard_verify")
    placeholders = ",".join("?" for _ in tables)
    conn.execute(f"DELETE FROM rs_field WHERE table_name IN ({placeholders})", tables)
    conn.execute(f"DELETE FROM rs_row WHERE table_name IN ({placeholders})", tables)
    conn.execute(f"DELETE FROM rs_datatable_field WHERE table_name IN ({placeholders})", tables)
    conn.execute(f"DELETE FROM rs_datatable WHERE table_name IN ({placeholders})", tables)


def init_database() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS rs_datatable (
            table_name TEXT PRIMARY KEY,
            model_name TEXT NOT NULL,
            table_kind TEXT NOT NULL,
            row_mode TEXT NOT NULL,
            remark TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS rs_datatable_field (
            table_name TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (table_name, field_name)
        );
        CREATE TABLE IF NOT EXISTS rs_row (
            table_name TEXT NOT NULL,
            data_id TEXT NOT NULL,
            remark TEXT DEFAULT '',
            PRIMARY KEY (table_name, data_id)
        );
        CREATE TABLE IF NOT EXISTS rs_field (
            table_name TEXT NOT NULL,
            data_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT NOT NULL,
            PRIMARY KEY (table_name, data_id, field_name)
        );
        """
    )
    _reset(conn)
    cur = conn.cursor()

    def add_table(table: str, model_name: str, table_kind: str,
                  fields: tuple[str, ...], rows: dict[str, dict[str, str]]) -> None:
        """插入一张数据表 + 字段列 + 行。"""
        cur.execute(
            "INSERT OR REPLACE INTO rs_datatable "
            "(table_name, model_name, table_kind, row_mode, updated_at) "
            "VALUES (?, ?, ?, 'standard', datetime('now'))",
            (table, model_name, table_kind),
        )
        for order, field in enumerate(fields):
            cur.execute(
                "INSERT OR REPLACE INTO rs_datatable_field "
                "(table_name, field_name, field_order) VALUES (?, ?, ?)",
                (table, field, order),
            )
        for data_id, field_values in rows.items():
            cur.execute(
                "INSERT OR REPLACE INTO rs_row (table_name, data_id, remark) VALUES (?, ?, '')",
                (table, data_id),
            )
            for field, value in field_values.items():
                cur.execute(
                    "INSERT OR REPLACE INTO rs_field "
                    "(table_name, data_id, field_name, field_value) VALUES (?, ?, ?, ?)",
                    (table, data_id, field, value),
                )

    add_table(
        "LoginForm", "LoginForm", "data",
        ("username", "password", "loginBtn"),
        {"L001": {"username": "admin", "password": "123456", "loginBtn": "click"}},
    )

    add_table(
        "NavMenu", "NavMenu", "data",
        ("testLink",),
        {"N001": {"testLink": "click"}},
    )

    add_table(
        "TakeoverForm", "TakeoverForm", "data",
        ("username", "role", "submitBtn", "formResult"),
        # 探索段「边界输入」探测：用户名留空 + role 选「用户」后点 #submitBtn。
        # 用于观察页面在缺参数时的实际表现，属探索动作，不是固定用例断言。
        # select 的写法是数据表单元格里的 UI 动作语法：select【选项值】。
        # formResult 填 BLANK 表示本行不驱动该字段（探索关注的是「提交后页面变成
        # 什么样」，由下一个 get 步骤采集，而不是预先断言）。
        {"E001": {"username": "", "role": "select【user】", "submitBtn": "click",
                  "formResult": "BLANK"}},
    )

    add_table(
        "TakeoverForm_verify", "TakeoverForm", "verify",
        ("username", "role", "submitBtn", "formResult"),
        # Agent 接管后填 username=接管人、role=admin、点 #submitBtn →
        # demosite submitForm() 写 #formResult = "提交成功！<br>用户名: 接管人<br>角色: admin"，
        # text_content 读到拼接后的纯文本（不含换行标签）
        {"V001": {"username": "BLANK", "role": "BLANK", "submitBtn": "BLANK",
                  "formResult": "提交成功！用户名: 接管人角色: admin"},
         # 探索段「空用户名提交」后的实际页面表现（后置用例严格模式校验）
         "V002": {"username": "BLANK", "role": "BLANK", "submitBtn": "BLANK",
                  "formResult": EXPLORE_EMPTY_USER_FORM_RESULT}},
    )

    add_table(
        "Dashboard_verify", "Dashboard", "verify",
        ("totalOrders", "completedOrders", "pendingOrders"),
        # 登录后 demosite loadDashboard() 渲染：total=3 / completed=2 / pending=1
        {"V001": {"totalOrders": "3", "completedOrders": "2", "pendingOrders": "1"}},
    )

    conn.commit()
    conn.close()
    print(f"✅ demo_pause_takeover 测试数据已初始化: {DB_PATH}")


if __name__ == "__main__":
    init_database()
