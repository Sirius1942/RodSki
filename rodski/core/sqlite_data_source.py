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

        # v11.9.0：数据驱动表（table_kind='driver'）只存 DataID，不是模型数据表，不加载进数据视图；
        # 由 core.data_driven 在计划编译阶段单独读取（CORE §7.8）
        cur = conn.execute("SELECT table_name FROM rs_datatable WHERE table_kind != 'driver'")
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

    def load_driver_tables(self) -> Dict[str, Dict[str, Any]]:
        """数据驱动表（只读展示用，如 rodski data dump）：{表名: {model_name, remark, columns, rows}}"""
        conn = self._connect()
        out: Dict[str, Dict[str, Any]] = {}
        for name, model_name, remark in conn.execute(
                "SELECT table_name, model_name, COALESCE(remark, '') FROM rs_datatable WHERE table_kind = 'driver'"):
            columns = [r[0] for r in conn.execute(
                "SELECT field_name FROM rs_datatable_field WHERE table_name = ? ORDER BY field_order, field_name",
                (name,))]
            rows: Dict[str, Dict[str, Any]] = {}
            for data_id, row_remark in conn.execute(
                    "SELECT data_id, COALESCE(remark, '') FROM rs_row WHERE table_name = ?", (name,)):
                rows[data_id] = {"remark": row_remark, "cells": {}}
            for data_id, field_name, value in conn.execute(
                    "SELECT data_id, field_name, field_value FROM rs_field WHERE table_name = ?", (name,)):
                if data_id in rows:
                    rows[data_id]["cells"][field_name] = value
            out[name] = {"model_name": model_name, "remark": remark, "columns": columns, "rows": rows}
        return out

    def get_driver_table_names(self) -> List[str]:
        """数据驱动表（table_kind='driver'）名列表"""
        conn = self._connect()
        cur = conn.execute("SELECT table_name FROM rs_datatable WHERE table_kind = 'driver'")
        return [row[0] for row in cur.fetchall()]

    def get_schema(self) -> Dict[str, List[str]]:
        """返回 {table_name: [field_name, ...]}，按 field_order 排序（不含数据驱动表）"""
        conn = self._connect()
        schemas: Dict[str, List[str]] = {}
        cur = conn.execute(
            "SELECT f.table_name, f.field_name FROM rs_datatable_field f "
            "JOIN rs_datatable t ON t.table_name = f.table_name WHERE t.table_kind != 'driver' "
            "ORDER BY f.table_name, f.field_order, f.field_name"
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
