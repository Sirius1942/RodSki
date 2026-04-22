"""init 子命令 — 创建 RodSki 测试模块骨架"""
import sys
import sqlite3
from pathlib import Path


_MODEL_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<models>\n</models>\n'
_DATA_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<datatables>\n</datatables>\n'
_GLOBALVALUE_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<globalvalue>\n</globalvalue>\n'
_DATA_VERIFY_XML = '<?xml version="1.0" encoding="UTF-8"?>\n<datatables>\n</datatables>\n'

_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS rs_datatable (
    table_name TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    table_kind TEXT NOT NULL CHECK (table_kind IN ('data', 'verify')),
    row_mode TEXT NOT NULL CHECK (row_mode IN ('standard', 'db_query', 'db_sql')),
    remark TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rs_datatable_field (
    table_name TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (table_name, field_name),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
CREATE TABLE IF NOT EXISTS rs_row (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    remark TEXT DEFAULT '',
    PRIMARY KEY (table_name, data_id),
    FOREIGN KEY (table_name) REFERENCES rs_datatable(table_name)
);
CREATE TABLE IF NOT EXISTS rs_field (
    table_name TEXT NOT NULL,
    data_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    PRIMARY KEY (table_name, data_id, field_name),
    FOREIGN KEY (table_name, data_id) REFERENCES rs_row(table_name, data_id),
    FOREIGN KEY (table_name, field_name) REFERENCES rs_datatable_field(table_name, field_name)
);
"""


def setup_parser(subparsers):
    p = subparsers.add_parser("init", help="创建 RodSki 测试模块骨架")
    p.add_argument("target", help="目标目录路径")
    p.add_argument("--with-verify", action="store_true", help="创建 data_verify.xml")
    p.add_argument("--with-sqlite", action="store_true", help="创建 testdata.sqlite 并初始化元表")
    p.add_argument("--force", action="store_true", help="覆盖已有模板文件")


def _write(path: Path, content: str, force: bool) -> bool:
    if path.exists() and not force:
        print(f"  跳过 (已存在): {path}")
        return False
    path.write_text(content, encoding="utf-8")
    print(f"  创建: {path}")
    return True


def handle(args):
    target = Path(args.target).expanduser().resolve()

    dirs = ["case", "model", "fun", "data", "result"]
    for d in dirs:
        (target / d).mkdir(parents=True, exist_ok=True)
        print(f"  目录: {target / d}")

    _write(target / "model" / "model.xml", _MODEL_XML, args.force)
    _write(target / "data" / "data.xml", _DATA_XML, args.force)
    _write(target / "data" / "globalvalue.xml", _GLOBALVALUE_XML, args.force)

    if args.with_verify:
        _write(target / "data" / "data_verify.xml", _DATA_VERIFY_XML, args.force)

    if args.with_sqlite:
        db_path = target / "data" / "testdata.sqlite"
        if db_path.exists() and not args.force:
            print(f"  跳过 (已存在): {db_path}")
        else:
            conn = sqlite3.connect(str(db_path))
            conn.executescript(_SQLITE_DDL)
            conn.close()
            print(f"  创建: {db_path}")

    print(f"\n初始化完成: {target}")
    return 0
