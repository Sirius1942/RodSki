#!/usr/bin/env python3
"""重建 plan_suites 模块的 data/data.sqlite 与被测订单库 orders.db（可重复执行）。

用法：python3 rodski-demo/demosite/plan_suites/data/init_data.py

数据表规则同 demosite/data_driven（CORE §2.1 / §7.8）。驱动表 OrderMatrix 绑定 order/create.xml::PS_ORDER_1，
用于验收"数据驱动实例跟随模板用例所在的测试套、按行顺序执行、不拆分"（PS-19）。
case/mixed/ 引用的 Android / iOS / Windows / mobile 模型只做编译验收，这里仍给出数据行，保证引用完整。
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
ORDERS_DB = MODULE_DIR / "orders.db"
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from rodski.core.sqlite_schema import SQLITE_DDL  # noqa: E402

Row = Tuple[str, Dict[str, str], str]


def row(data_id: str, fields: List[str], remark: str = "", **values: str) -> Row:
    unknown = set(values) - set(fields)
    if unknown:
        raise ValueError(f"{data_id}: 未知字段 {sorted(unknown)}")
    return data_id, {f: values.get(f, "BLANK") for f in fields}, remark


def drow(data_id: str, columns: List[str], remark: str, cells: List[str]) -> Row:
    """驱动表行：cells 与 columns 一一对应（DataID 或 BLANK）。"""
    if len(cells) != len(columns):
        raise ValueError(f"{data_id}: 单元格数 {len(cells)} 与列数 {len(columns)} 不一致")
    return data_id, dict(zip(columns, cells)), remark


def add_table(conn: sqlite3.Connection, name: str, kind: str, fields: List[str], rows: List[Row],
              remark: str, model_name: str = "") -> None:
    conn.execute(
        "INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) VALUES(?,?,?,'standard',?)",
        (name, model_name or name, kind, remark),
    )
    conn.executemany(
        "INSERT INTO rs_datatable_field(table_name,field_name,field_order) VALUES(?,?,?)",
        [(name, f, i) for i, f in enumerate(fields)],
    )
    for data_id, values, row_remark in rows:
        if set(values) != set(fields):
            raise ValueError(f"{name}.{data_id}: 行字段集合必须与 schema 一致")
        conn.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES(?,?,?)", (name, data_id, row_remark))
        conn.executemany(
            "INSERT INTO rs_field(table_name,data_id,field_name,field_value) VALUES(?,?,?,?)",
            [(name, data_id, f, values[f]) for f in fields],
        )


def result_text(username: str, role: str = "") -> str:
    """demosite 表单提交后 #formResult 的文本。"""
    return f"提交成功！用户名: {username}角色: {role}"


def model_tables():
    t = []
    f = ["username", "password", "loginBtn"]
    t.append(("LoginForm", "data", f, [
        row("L001", f, "demosite 管理员登录", username="admin", password="123456", loginBtn="click"),
    ], "demosite 登录"))
    t.append(("NavMenu", "data", ["testLink"], [
        row("N001", ["testLink"], "进入功能测试区", testLink="click"),
    ], "导航"))
    f = ["username", "submitBtn", "formResult"]
    t.append(("TestForm", "data", f, [
        row("T001", f, "后台表单提交", username="后台管理员", submitBtn="click"),
    ], "demosite 功能测试表单"))
    t.append(("TestForm_verify", "verify", f, [
        row("V001", f, "后台表单提交结果", formResult=result_text("后台管理员")),
    ], "demosite 功能测试表单期望"))

    f = ["username", "password"]
    t.append(("LoginAPI", "data", f, [
        row("D001", f, "正确账号；OrderMatrix[r1] 使用", username="admin", password="123456"),
        row("D002", f, "错误密码；PS_SPECIAL 与 OrderMatrix[r2] 使用", username="admin", password="wrong"),
    ], "登录接口请求"))
    t.append(("LoginResp_verify", "verify", ["message"], [
        row("R001", ["message"], "登录成功响应", message="登录成功"),
        row("R002", ["message"], "错误密码响应", message="用户名或密码错误"),
    ], "登录接口响应期望"))

    f = ["query", "order_no"]
    t.append(("QueryOrder", "data", f, [
        row("Q001", f, "订单 ORD001", query="get_by_no", order_no="ORD001"),
        row("Q002", f, "订单 ORD002", query="get_by_no", order_no="ORD002"),
    ], "订单查询"))
    f = ["order_no", "customer_name"]
    t.append(("QueryOrder_verify", "verify", f, [
        row("C001", f, "ORD001 客户", order_no="ORD001", customer_name="张伟"),
        row("C002", f, "ORD002 客户", order_no="ORD002", customer_name="李娜"),
    ], "订单查询期望"))

    # 只编译的模型（case/mixed/）
    f = ["username", "loginBtn"]
    t.append(("AppLogin", "data", f, [
        row("A001", f, "Android 登录（只编译）", username="admin", loginBtn="click"),
    ], "Android 登录"))
    t.append(("IosHome_verify", "verify", ["title"], [
        row("I001", ["title"], "iOS 首页标题（只编译）", title="首页"),
    ], "iOS 首页期望"))
    t.append(("WinCalc_verify", "verify", ["display"], [
        row("W001", ["display"], "计算器初始显示（只编译）", display="0"),
    ], "Windows 计算器期望"))
    t.append(("AnyMobile_verify", "verify", ["title"], [
        row("M001", ["title"], "未指定平台（只编译）", title="首页"),
    ], "移动端期望"))
    return t


def driver_tables():
    """[(表名, 绑定用例, 表备注, 列, 行)]"""
    cols = ["LoginAPI.D001", "LoginResp_verify.R001"]
    return [("OrderMatrix", "order/create.xml::PS_ORDER_1",
             "登录矩阵；计划 shop_full / shop_wide 的 order 套；目的：实例跟随模板用例所在的套、按行顺序执行",
             cols, [
                 drow("r1", cols, "正确密码", ["D001", "R001"]),
                 drow("r2", cols, "错误密码", ["D002", "R002"]),
             ])]


def build_orders_db() -> None:
    if ORDERS_DB.exists():
        ORDERS_DB.unlink()
    conn = sqlite3.connect(ORDERS_DB)
    conn.execute("CREATE TABLE orders(order_no TEXT PRIMARY KEY, customer_name TEXT NOT NULL)")
    conn.executemany("INSERT INTO orders VALUES(?,?)",
                     [("ORD001", "张伟"), ("ORD002", "李娜"), ("ORD003", "王强")])
    conn.commit()
    conn.close()


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SQLITE_DDL)
    for name, kind, fields, rows, remark in model_tables():
        add_table(conn, name, kind, fields, rows, remark)
    for name, case_uid, remark, columns, rows in driver_tables():
        add_table(conn, name, "driver", columns, rows, remark, model_name=case_uid)
    conn.commit()
    conn.close()
    build_orders_db()
    print(f"已重建 {DB_PATH.relative_to(REPO)} 与 {ORDERS_DB.relative_to(REPO)}")


if __name__ == "__main__":
    main()
