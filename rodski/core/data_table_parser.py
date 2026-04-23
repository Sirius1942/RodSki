"""数据表解析器 — SQLite 数据 facade（v6.0.0：data.xml 已废弃）

规则：
- data.sqlite 是 data/ 目录下唯一测试数据文件
- data.xml / data_verify.xml 已废弃；存在时运行时报错，请先执行 `rodski data import`
- SQLite 逻辑表必须有显式 schema，且所有行字段集合完全一致
- globalvalue.xml 由 GlobalValueParser 独立处理，不进入本解析器
"""
from pathlib import Path
from typing import Dict, Any, Optional

from .data_schema_validator import DataSchemaValidator
from .exceptions import DataParseError


class DataTableParser:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.sqlite_file = self.data_dir / "data.sqlite"
        self.tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._sqlite_source = None

    def parse_all_tables(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        self.tables = {}

        for legacy in ("data.xml", "data_verify.xml"):
            if (self.data_dir / legacy).exists():
                raise DataParseError(
                    f"[v6.0.0] 检测到已废弃的 XML 数据文件: {legacy}。"
                    f"请先执行 `rodski data import <module>` 迁移至 data.sqlite，然后删除该文件。"
                )

        if self.sqlite_file.exists():
            from core.sqlite_data_source import SQLiteDataSource
            if self._sqlite_source:
                self._sqlite_source.close()
            self._sqlite_source = SQLiteDataSource(str(self.sqlite_file))
            sqlite_tables = self._sqlite_source.load_tables()
            DataSchemaValidator.check_sqlite_schema(
                sqlite_tables, self._sqlite_source.get_schema()
            )
            self.tables.update(sqlite_tables)

        return self.tables

    def merge_table(
        self, table_name: str, rows: Dict[str, Dict[str, Any]]
    ) -> None:
        """合并临时数据表（用于 insert 步骤注入临时资源）"""
        if table_name in self.tables:
            self.tables[table_name].update(rows)
        else:
            self.tables[table_name] = dict(rows)

    def get(self, table_name: str, data_id: Optional[str] = None) -> Any:
        if table_name not in self.tables:
            return None
        if data_id is None:
            return self.tables[table_name]
        return self.tables[table_name].get(data_id)

    def get_data(self, table_name: str, data_id: str) -> Dict[str, Any]:
        return self.get(table_name, data_id) or {}

    def close(self) -> None:
        self.tables.clear()
        if self._sqlite_source:
            self._sqlite_source.close()
            self._sqlite_source = None
