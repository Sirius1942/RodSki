"""SQLite 测试数据源 — 从 rs_datatable/rs_datatable_field/rs_row/rs_field 读取逻辑表数据"""
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional


class SQLiteDataSource:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
        return self._conn

    def load_tables(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """返回 {table_name: {data_id: {field_name: field_value}}}"""
        conn = self._connect()
        tables: Dict[str, Dict[str, Dict[str, Any]]] = {}

        cur = conn.execute("SELECT table_name FROM rs_datatable")
        table_names = [row[0] for row in cur.fetchall()]

        for table_name in table_names:
            cur = conn.execute(
                "SELECT data_id FROM rs_row WHERE table_name = ?", (table_name,)
            )
            data_ids = [row[0] for row in cur.fetchall()]

            rows: Dict[str, Dict[str, Any]] = {}
            for data_id in data_ids:
                cur = conn.execute(
                    "SELECT field_name, field_value FROM rs_field "
                    "WHERE table_name = ? AND data_id = ?",
                    (table_name, data_id),
                )
                row_data = {r[0]: r[1] for r in cur.fetchall()}
                if row_data:
                    rows[data_id] = row_data

            if rows:
                tables[table_name] = rows

        return tables

    def get_schema(self) -> Dict[str, List[str]]:
        """返回 {table_name: [field_name, ...]}，按 field_order 排序"""
        conn = self._connect()
        schemas: Dict[str, List[str]] = {}
        cur = conn.execute(
            "SELECT table_name, field_name FROM rs_datatable_field "
            "ORDER BY table_name, field_order, field_name"
        )
        for row in cur.fetchall():
            schemas.setdefault(row[0], []).append(row[1])
        return schemas

    def get_table_names(self) -> List[str]:
        conn = self._connect()
        cur = conn.execute("SELECT table_name FROM rs_datatable")
        return [row[0] for row in cur.fetchall()]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
