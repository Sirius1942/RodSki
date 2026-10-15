#!/usr/bin/env python3
"""生成 session_shared 模块的 data/data.sqlite（F073 SessionMode）。

data.sqlite 是唯一测试数据文件（CORE §2.1）；本脚本只是可复现的生成器。
同一逻辑表所有行字段集合一致（缺字段显式 BLANK，CORE §2.4.1）。

用法: python3 rodski-demo/local/session_shared/fun/build_data.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE = HERE.parent
REPO = MODULE.parent.parent.parent

try:
    from rodski.core.sqlite_schema import SQLITE_DDL
except ImportError:  # 源码树直接运行
    sys.path.insert(0, str(REPO / "rodski"))
    from core.sqlite_schema import SQLITE_DDL  # type: ignore

B = "BLANK"
FIELDS = ["markBtn", "storageVal", "cookieVal"]
TABLES = {
    "SessionPage": {
        "D_MARK": ("点击写入标记 S1", {"markBtn": "click", "storageVal": B, "cookieVal": B}),
    },
    "SessionPage_verify": {
        "V_MARKED": ("localStorage 与 cookie 都是 S1", {"markBtn": B, "storageVal": "S1", "cookieVal": "S1"}),
        "V_EMPTY": ("全新会话：没有标记", {"markBtn": B, "storageVal": "none", "cookieVal": "none"}),
    },
}


def build(quiet: bool = False) -> None:
    db = MODULE / "data" / "data.sqlite"
    db.unlink(missing_ok=True)
    conn = sqlite3.connect(str(db))
    conn.executescript(SQLITE_DDL)
    for name, rows in TABLES.items():
        kind = "verify" if name.endswith("_verify") else "data"
        model = name[: -len("_verify")] if kind == "verify" else name
        conn.execute("INSERT INTO rs_datatable (table_name, model_name, table_kind, row_mode, remark) "
                     "VALUES (?,?,?,?,?)", (name, model, kind, "standard", ""))
        for i, f in enumerate(FIELDS):
            conn.execute("INSERT INTO rs_datatable_field VALUES (?,?,?)", (name, f, i))
        for data_id, (remark, values) in rows.items():
            assert set(values) == set(FIELDS), data_id
            conn.execute("INSERT INTO rs_row VALUES (?,?,?)", (name, data_id, remark))
            for f in FIELDS:
                conn.execute("INSERT INTO rs_field VALUES (?,?,?,?)", (name, data_id, f, values[f]))
    conn.commit()
    conn.close()
    if not quiet:
        print(f"[OK] {db.relative_to(REPO)}: {len(TABLES)} 张表")


if __name__ == "__main__":
    build()
