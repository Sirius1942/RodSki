"""data import 子命令 — 将 data.xml / data_verify.xml 迁移至 data.sqlite"""
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any

from core.sqlite_schema import SQLITE_DDL


def run_import(module: str, overwrite: bool = False) -> int:
    data_dir = Path(module) / "data"
    xml_tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for fname in ("data.xml", "data_verify.xml"):
        _parse_xml_into(data_dir / fname, xml_tables)

    if not xml_tables:
        print("未找到 data.xml / data_verify.xml，无需迁移。")
        return 0

    db_path = data_dir / "data.sqlite"
    _ensure_sqlite(db_path)

    conn = sqlite3.connect(str(db_path))
    imported, skipped = 0, 0
    for table_name, rows in xml_tables.items():
        exists = conn.execute(
            "SELECT 1 FROM rs_datatable WHERE table_name=?", (table_name,)
        ).fetchone()
        if exists:
            if not overwrite:
                print(f"  [SKIP] {table_name}")
                skipped += 1
                continue
            for t in ("rs_field", "rs_row", "rs_datatable_field", "rs_datatable"):
                conn.execute(f"DELETE FROM {t} WHERE table_name=?", (table_name,))

        table_kind = "verify" if table_name.endswith("_verify") else "data"
        conn.execute(
            "INSERT INTO rs_datatable VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)",
            (table_name, table_name, table_kind, "standard", ""),
        )
        all_fields = sorted({f for row in rows.values() for f in row})
        for i, field in enumerate(all_fields):
            conn.execute(
                "INSERT INTO rs_datatable_field VALUES (?,?,?)", (table_name, field, i)
            )
        for data_id, row_data in rows.items():
            conn.execute("INSERT INTO rs_row VALUES (?,?,?)", (table_name, data_id, ""))
            for field_name, field_value in row_data.items():
                conn.execute(
                    "INSERT INTO rs_field VALUES (?,?,?,?)",
                    (table_name, data_id, field_name, field_value),
                )
        imported += 1
        print(f"  [OK] {table_name} ({len(rows)} 行)")

    conn.commit()
    conn.close()
    print(f"\n导入完成: {imported} 张表导入，{skipped} 张表跳过。")
    return 0


def _parse_xml_into(path: Path, target: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
    if not path.exists():
        return
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return
    nodes = (
        root.findall("datatable") if root.tag == "datatables"
        else ([root] if root.tag == "datatable" else [])
    )
    for dt in nodes:
        name = dt.get("name", "").strip()
        if not name:
            continue
        rows = {}
        for row in dt.findall("row"):
            rid = (row.get("id") or "").strip()
            if not rid:
                continue
            fields = {
                f.get("name", "").strip(): (f.text or "").strip()
                for f in row.findall("field")
                if f.get("name", "").strip()
            }
            if fields:
                rows[rid] = fields
        if rows:
            target[name] = rows


def _ensure_sqlite(db_path: Path) -> None:
    if db_path.exists():
        return
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SQLITE_DDL)
    conn.close()
