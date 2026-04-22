"""数据表解析器 — 统一 XML + SQLite 数据 facade

规则：
- data.xml 是唯一 XML 输入数据文件
- data_verify.xml 是唯一验证 XML 文件（可选）
- testdata.sqlite 是可选的推荐主数据存储
- 同一逻辑表不能同时由 XML 和 SQLite 拥有；跨源同名必须报错
- SQLite 逻辑表必须有显式 schema，且所有行字段集合完全一致
- globalvalue.xml 由 GlobalValueParser 独立处理，不进入本解析器
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional

from core.data_schema_validator import DataSchemaValidator


class DataTableParser:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "data.xml"
        self.verify_file = self.data_dir / "data_verify.xml"
        self.sqlite_file = self.data_dir / "testdata.sqlite"
        self.tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._sqlite_source = None

    def parse_all_tables(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """解析 data 目录中的所有数据表（XML + SQLite）"""
        self.tables = {}

        # 1. 加载 XML
        xml_tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._parse_file(self.data_file, xml_tables)
        self._parse_file(self.verify_file, xml_tables)

        # 2. 加载 SQLite（如存在）
        sqlite_tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
        if self.sqlite_file.exists():
            from core.sqlite_data_source import SQLiteDataSource
            if self._sqlite_source:
                self._sqlite_source.close()
            self._sqlite_source = SQLiteDataSource(str(self.sqlite_file))
            sqlite_tables = self._sqlite_source.load_tables()
            schemas = self._sqlite_source.get_schema()
            DataSchemaValidator.check_sqlite_schema(sqlite_tables, schemas)

        # 3. 跨源冲突检查（基于 rs_datatable 注册的所有表名，不只是有数据的表）
        sqlite_registered = (
            set(self._sqlite_source.get_table_names()) if self._sqlite_source else set()
        )
        DataSchemaValidator.check_cross_source_conflict(
            set(xml_tables.keys()), sqlite_registered
        )

        # 4. 合并到统一索引
        self.tables.update(xml_tables)
        self.tables.update(sqlite_tables)

        return self.tables

    def _parse_file(
        self,
        file_path: Path,
        target: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> None:
        if not file_path.exists():
            return
        try:
            tree = ET.parse(file_path)
        except ET.ParseError:
            return
        root = tree.getroot()
        if root.tag == 'datatables':
            datatable_nodes = root.findall('datatable')
        elif root.tag == 'datatable':
            datatable_nodes = [root]
        else:
            return
        for datatable_node in datatable_nodes:
            table_name = datatable_node.get('name', '').strip()
            if not table_name:
                continue
            table_data = {}
            for row_node in datatable_node.findall('row'):
                data_id = (row_node.get('id') or '').strip()
                if not data_id:
                    continue
                row_data = {}
                for field_node in row_node.findall('field'):
                    field_name = field_node.get('name', '').strip()
                    field_value = (field_node.text or '').strip()
                    if field_name and field_value:
                        row_data[field_name] = field_value
                if row_data:
                    table_data[data_id] = row_data
            if table_data:
                target[table_name] = table_data

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
