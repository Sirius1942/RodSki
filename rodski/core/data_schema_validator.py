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
                missing = expected - actual
                extra = actual - expected
                if missing or extra:
                    parts = []
                    if missing:
                        parts.append(f"missing={sorted(missing)}")
                    if extra:
                        parts.append(f"extra={sorted(extra)}")
                    raise DataParseError(
                        f"{table_name}.{data_id}: {', '.join(parts)}。"
                        f"缺字段必须显式填 BLANK/NULL/NONE，不能省略"
                    )
