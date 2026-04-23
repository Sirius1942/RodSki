"""数据 schema 校验器 — SQLite schema 完整性与行字段一致性校验"""
from typing import Dict, Any, List

from .exceptions import DataParseError


class DataSchemaValidator:
    @staticmethod
    def check_sqlite_schema(
        tables: Dict[str, Dict[str, Dict[str, Any]]],
        schemas: Dict[str, List[str]],
    ) -> None:
        for table_name, rows in tables.items():
            if table_name not in schemas:
                raise DataParseError(
                    f"SQLite 逻辑表 '{table_name}' 缺少 schema 定义 "
                    f"(rs_datatable_field 中无对应记录)"
                )
            expected = set(schemas[table_name])
            for data_id, row_data in rows.items():
                actual = set(row_data.keys())
                if actual != expected:
                    missing = expected - actual
                    extra = actual - expected
                    parts = []
                    if missing:
                        parts.append(f"缺少字段: {sorted(missing)}")
                    if extra:
                        parts.append(f"多余字段: {sorted(extra)}")
                    raise DataParseError(
                        f"SQLite 逻辑表 '{table_name}' 行 '{data_id}' "
                        f"字段集合与 schema 不一致 — {'; '.join(parts)}"
                    )

