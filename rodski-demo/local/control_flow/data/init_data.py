#!/usr/bin/env python3
"""重建 local/control_flow 的 data/data.sqlite（使用 RodSki 公共 SQLite schema）。

用法：python3 rodski-demo/local/control_flow/data/init_data.py

data.sqlite 被 git 跟踪，全量回归结束时会被 git checkout 还原为仓库版本，
因此 run_acceptance.py 每次开头都会调用本脚本重建数据，不依赖手工修改过的 data.sqlite。

当前只写入 case/flow/ 验收用例需要的逻辑表：
  CfQuery          F069 loop 内 `DB CfQuery Q00${i}`：每行一条常量 SELECT（无需建表）
  CfQuery_verify   F069 loop 内 `verify CfQuery V00${i}`：期望 label
同表所有行字段集合一致（CORE §2.4.1 / v6.7.6）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
SCHEMA_FILE = Path(__file__).resolve().parents[4] / "rodski" / "core" / "sqlite_schema.py"

LOOP_VALUES = (1, 2, 3, 5)   # 覆盖 range="1-3"、"1,2,3" 与 "1,5"


def add_table(conn: sqlite3.Connection, *, name: str, model: str, kind: str,
              fields: list[str], rows: list[tuple[str, dict[str, str]]], remark: str) -> None:
    conn.execute(
        "INSERT INTO rs_datatable(table_name,model_name,table_kind,row_mode,remark) "
        "VALUES(?,?,?,'standard',?)", (name, model, kind, remark)
    )
    conn.executemany(
        "INSERT INTO rs_datatable_field(table_name,field_name,field_order) VALUES(?,?,?)",
        [(name, field, index) for index, field in enumerate(fields)],
    )
    for data_id, values in rows:
        if set(values) != set(fields):
            raise ValueError(f"{name}.{data_id}: 行字段集合必须与表字段一致")
        conn.execute("INSERT INTO rs_row(table_name,data_id,remark) VALUES(?,?,?)", (name, data_id, ""))
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

        add_table(conn, name="CfQuery", model="CfQuery", kind="data",
                  fields=["sql", "operation"],
                  rows=[(f"Q00{i}", {"sql": f"SELECT 'iter{i}' AS label", "operation": "query"})
                        for i in LOOP_VALUES],
                  remark="F069 loop：data=Q00${i} 逐轮解析为不同 DataID")
        add_table(conn, name="CfQuery_verify", model="CfQuery", kind="verify",
                  fields=["label"],
                  rows=[(f"V00{i}", {"label": f"iter{i}"}) for i in LOOP_VALUES],
                  remark="F069 loop：verify 期望值与轮次一一对应")
    print(f"已重建 {DB_PATH}")


if __name__ == "__main__":
    main()
