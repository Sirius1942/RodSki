"""数据表 XML 解析器 - 从 data/ 目录加载多个 XML 数据文件

每个 XML 文件对应原 Excel 中的一个数据表 Sheet。
XML 格式参见 schemas/data.xsd。
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional

from core.xml_schema_validator import RodskiXmlValidator


SKIP_FILES = {'globalvalue.xml'}


class DataTableParser:
    def __init__(self, data_dir: str):
        """初始化数据表解析器

        Args:
            data_dir: data/ 目录路径，包含所有数据 XML 文件
        """
        self.data_dir = Path(data_dir)
        self.tables: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def parse_all_tables(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """解析 data/ 目录下所有 XML 数据文件（跳过 globalvalue.xml）"""
        self.tables = {}

        if not self.data_dir.is_dir():
            return self.tables

        for xml_file in sorted(self.data_dir.glob("*.xml")):
            if xml_file.name.lower() in SKIP_FILES:
                continue
            table_name, table_data = self._parse_file(xml_file)
            if table_name and table_data:
                self.tables[table_name] = table_data

        return self.tables

    def _parse_file(self, xml_path: Path) -> tuple:
        """解析单个数据 XML 文件，返回 (表名, {data_id: {field: value}})"""
        try:
            RodskiXmlValidator.validate_file(xml_path, RodskiXmlValidator.KIND_DATA)
            tree = ET.parse(xml_path)
        except ET.ParseError:
            return (None, None)

        root = tree.getroot()
        table_name = root.get('name', xml_path.stem)
        table_data = {}

        for row_node in root.findall('row'):
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

        return (table_name, table_data)

    def load_single_table(self, table_name: str) -> Dict[str, Dict[str, Any]]:
        """按需加载单个数据表（在 data/ 目录中查找 {table_name}.xml）"""
        xml_path = self.data_dir / f"{table_name}.xml"
        if not xml_path.exists():
            return {}
        name, data = self._parse_file(xml_path)
        if name and data:
            self.tables[name] = data
            return data
        return {}

    def get_data(self, table_name: str, data_id: str) -> Dict[str, Any]:
        """获取指定数据行，如果表未加载则尝试按需加载"""
        if table_name not in self.tables:
            self.load_single_table(table_name)
        return self.tables.get(table_name, {}).get(data_id, {})

    def close(self):
        pass
