#!/usr/bin/env python3
"""重建 local/plan_selector 的 data/data.sqlite（只建 RodSki 公共元表，无业务逻辑表）。

用法：python3 rodski-demo/local/plan_selector/data/init_data.py

本模块的用例只用 run 关键字记录执行轨迹，不读数据表；data.sqlite 仍按 CORE §7.3 作为模块唯一数据文件存在。
run_acceptance.py 每次开头调用本脚本，保证文件存在且 schema 正确（回归结束时被跟踪文件可能被 git 还原）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = MODULE_DIR / "data" / "data.sqlite"
SCHEMA_FILE = Path(__file__).resolve().parents[4] / "rodski" / "core" / "sqlite_schema.py"


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    schema_module = SCHEMA_FILE.read_text(encoding="utf-8")
    ddl_start = schema_module.index('SQLITE_DDL = """') + len('SQLITE_DDL = """')
    ddl_end = schema_module.index('"""', ddl_start)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema_module[ddl_start:ddl_end])
    print(f"已重建 {DB_PATH}")


if __name__ == "__main__":
    main()
