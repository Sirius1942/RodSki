#!/usr/bin/env python3
"""重建 data_driven 模块的 data/data.sqlite 与被测订单库 orders.db（可重复执行）。

用法：python3 rodski-demo/demosite/data_driven/data/init_data.py

data.sqlite 中有三类逻辑表（CORE §2.1 / §7.8）：
- data / verify：模型数据表，表名 = 模型名 / 模型名_verify，字段集合一致，不关心的字段写 BLANK
- driver：数据驱动表（计划 / 用例 / 步骤对应关系表），model_name = 绑定用例 `case_file::case_id`，
  列 = `表名.基础DataID`，单元格只写 DataID 或 BLANK；表备注必填，行备注即实例标题

被驱动表引用的模型数据行鼓励写备注（所属计划 / 驱动表、用途）。TestForm.T103 / TestForm_verify.V103
故意不写备注，用于验收"缺备注只 WARN 不阻断"（DD-17）。
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
        row("L001", f, "demosite 管理员登录；DD_FORM 各实例共用（不在驱动表中，始终用基础 DataID）",
            username="admin", password="123456", loginBtn="click"),
    ], "demosite 登录"))
    t.append(("NavMenu", "data", ["testLink"], [
        row("N001", ["testLink"], "进入功能测试区", testLink="click"),
    ], "导航"))

    f = ["username", "role", "submitBtn", "formResult"]
    t.append(("TestForm", "data", f, [
        row("T001", f, "基础 DataID：用例单独运行或驱动表单元格为 BLANK 时使用", username="基础输入", submitBtn="click"),
        row("T002", f, "基础 DataID：DD_TWICE / DD_LOOP 第二次提交", username="第二次输入", submitBtn="click"),
        row("T101", f, "data_driven_suite / FormMatrix[alice]：普通用户 alice",
            username="alice", role="select【user】", submitBtn="click"),
        row("T102", f, "data_driven_suite / FormMatrix[bob]：管理员 bob",
            username="bob", role="select【admin】", submitBtn="click"),
        row("T103", f, "", username="carol", role="select【guest】", submitBtn="click"),
        row("T201", f, "data_driven_suite / TwiceMatrix[both]、LoopMatrix[x]：提交 甲", username="甲", submitBtn="click"),
        row("T202", f, "data_driven_suite / TwiceMatrix[both]：第二次提交替换为 乙", username="乙", submitBtn="click"),
    ], "demosite 功能测试表单"))
    t.append(("TestForm_verify", "verify", f, [
        row("V001", f, "基础期望：基础输入", formResult=result_text("基础输入")),
        row("V002", f, "基础期望：第二次输入", formResult=result_text("第二次输入")),
        row("V101", f, "data_driven_suite / FormMatrix[alice]", formResult=result_text("alice", "user")),
        row("V102", f, "data_driven_suite / FormMatrix[bob]", formResult=result_text("bob", "admin")),
        row("V103", f, "", formResult=result_text("carol", "guest")),
        row("V201", f, "data_driven_suite / TwiceMatrix[both]", formResult=result_text("甲")),
        row("V202", f, "data_driven_suite / TwiceMatrix[both]", formResult=result_text("乙")),
        row("V999", f, "failure_isolation_suite / FormMatrixFail[wrong]：故意写错的期望值",
            formResult=result_text("不存在的用户")),
    ], "demosite 功能测试表单期望"))

    f = ["username", "password"]
    t.append(("LoginAPI", "data", f, [
        row("D001", f, "基础 DataID：正确账号；ApiMatrix[ok] / StateMatrix 使用", username="admin", password="123456"),
        row("D002", f, "data_driven_suite / ApiMatrix[bad]：错误密码", username="admin", password="wrong"),
    ], "登录接口请求"))
    t.append(("LoginResp_verify", "verify", ["message"], [
        row("R001", ["message"], "登录成功响应", message="登录成功"),
        row("R002", ["message"], "data_driven_suite / ApiMatrix[bad]：错误密码响应", message="用户名或密码错误"),
        row("R_LEAK", ["message"], "DD_STATE：只有实例间状态泄漏时才会执行，必然失败", message="状态泄漏"),
    ], "登录接口响应期望"))

    f = ["query", "order_no"]
    t.append(("QueryOrder", "data", f, [
        row("Q001", f, "基础 DataID：订单 ORD001", query="get_by_no", order_no="ORD001"),
        row("Q002", f, "data_driven_suite / ApiMatrix[bad]：订单 ORD002", query="get_by_no", order_no="ORD002"),
    ], "订单查询"))
    f = ["order_no", "customer_name"]
    t.append(("QueryOrder_verify", "verify", f, [
        row("C001", f, "ORD001 客户", order_no="ORD001", customer_name="张伟"),
        row("C002", f, "data_driven_suite / ApiMatrix[bad]：ORD002 客户", order_no="ORD002", customer_name="李娜"),
    ], "订单查询期望"))
    return t


def driver_tables():
    """[(表名, 绑定用例, 表备注, 列, 行)]"""
    t = []
    cols = ["TestForm.T001", "TestForm_verify.V001"]
    t.append(("FormMatrix", "form_flow.xml::DD_FORM",
              "表单角色矩阵；计划 data_driven_suite；目的：同一表单流程按不同用户 / 角色各执行一次，登录步骤不替换",
              cols, [
                  drow("alice", cols, "普通用户 alice（role=user）", ["T101", "V101"]),
                  drow("bob", cols, "管理员 bob（role=admin）", ["T102", "V102"]),
                  drow("base", cols, "BLANK：沿用用例基础 DataID", ["BLANK", "BLANK"]),
                  drow("carol", cols, "访客 carol（被引用数据行未写备注 → WARN）", ["T103", "V103"]),
              ]))
    t.append(("FormMatrixFail", "form_flow.xml::DD_FORM",
              "失败隔离；计划 failure_isolation_suite；目的：第 2 个实例期望值错误，第 1、3 个实例照常执行并通过",
              cols, [
                  drow("first", cols, "第 1 个实例：通过", ["T101", "V101"]),
                  drow("wrong", cols, "第 2 个实例：期望值故意写错", ["T102", "V999"]),
                  drow("third", cols, "第 3 个实例：前一个失败后仍执行", ["T103", "V103"]),
              ]))
    cols = ["TestForm.T001", "TestForm_verify.V001", "TestForm.T002", "TestForm_verify.V002"]
    t.append(("TwiceMatrix", "form_flow.xml::DD_TWICE",
              "同一模型两个基础 DataID 分别替换；计划 data_driven_suite",
              cols, [
                  drow("both", cols, "两次提交都替换", ["T201", "V201", "T202", "V202"]),
                  drow("second", cols, "只替换第二次提交", ["BLANK", "BLANK", "T101", "V101"]),
              ]))
    cols = ["TestForm.T001", "TestForm_verify.V001"]
    t.append(("LoopMatrix", "form_flow.xml::DD_LOOP",
              "字面 DataID 替换、loop 中的动态 DataID T00${i} 不替换；计划 data_driven_suite",
              cols, [
                  drow("x", cols, "字面 T001 → T201，loop 第 1 轮仍用 T001", ["T201", "V201"]),
              ]))
    cols = ["LoginAPI.D001", "LoginResp_verify.R001", "QueryOrder.Q001", "QueryOrder_verify.C001"]
    t.append(("ApiMatrix", "api_db.xml::DD_API",
              "接口 + DB 数据驱动；计划 data_driven_suite",
              cols, [
                  drow("ok", cols, "正确密码 + 订单 ORD001", ["D001", "R001", "Q001", "C001"]),
                  drow("bad", cols, "错误密码 + 订单 ORD002", ["D002", "R002", "Q002", "C002"]),
              ]))
    cols = ["LoginAPI.D001"]
    t.append(("StateMatrix", "api_db.xml::DD_STATE",
              "实例间 Return 历史与 set 变量隔离；计划 data_driven_suite；两行引用同一 DataID",
              cols, [
                  drow("s1", cols, "第 1 个实例：写入 set 变量与 Return", ["D001"]),
                  drow("s2", cols, "第 2 个实例：不得看到第 1 个实例的状态", ["D001"]),
              ]))
    return t


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
