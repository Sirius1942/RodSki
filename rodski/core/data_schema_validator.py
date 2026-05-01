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
                # 允许行只包含 schema 的部分字段（缺失字段代表不执行对应操作）
                # 但不允许出现 schema 中不存在的多余字段
                extra = actual - expected
                if extra:
                    raise DataParseError(
                        f"SQLite 逻辑表 '{table_name}' 行 '{data_id}' "
                        f"包含 schema 中未定义的字段: {sorted(extra)}"
                    )

