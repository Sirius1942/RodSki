"""数据 schema 校验器 — 跨源冲突检查 + SQLite schema 完整性与行字段一致性校验"""
from typing import Dict, Any, List, Set

from core.exceptions import DataParseError


class DataSchemaValidator:
    @staticmethod
    def check_cross_source_conflict(
        xml_tables: Set[str], sqlite_tables: Set[str]
    ) -> None:
        conflicts = xml_tables & sqlite_tables
        if conflicts:
            raise DataParseError(
                f"逻辑表跨源冲突：以下逻辑表同时存在于 XML 和 SQLite，"
                f"必须只保留一个来源: {sorted(conflicts)}"
            )

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

    @staticmethod
    def check_xml_column_drift(
        tables: Dict[str, Dict[str, Dict[str, Any]]]
    ) -> List[str]:
        """检查 XML 表列漂移（不同行字段集合不一致），返回警告列表（不抛异常）"""
        warnings = []
        for table_name, rows in tables.items():
            if not rows:
                continue
            field_sets = [frozenset(row.keys()) for row in rows.values()]
            if len(set(field_sets)) > 1:
                warnings.append(
                    f"XML 逻辑表 '{table_name}' 存在列漂移：不同行的字段集合不一致"
                )
        return warnings
