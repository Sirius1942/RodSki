"""数据表 XML 解析器 - 从 data/data.xml 加载所有数据表

规则：
- 所有数据表合并到 data/data.xml
- 全局变量独立在 data/globalvalue.xml

XML 格式参见 schemas/data.xsd。
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any


class DataTableParser:
    def __init__(self, data_dir: str):
        """初始化数据表解析器

        Args:
            data_dir: data/ 目录路径，必须包含 data.xml
        """
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "data.xml"
        self.tables: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def parse_all_tables(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """解析 data.xml 中的所有数据表"""
        self.tables = {}

        if not self.data_file.exists():
            return self.tables

        try:
            tree = ET.parse(self.data_file)
        except ET.ParseError:
            return self.tables

        root = tree.getroot()

        # 支持 <datatables> 或 <datatable> 作为根元素
        if root.tag == 'datatables':
            datatable_nodes = root.findall('datatable')
        elif root.tag == 'datatable':
            datatable_nodes = [root]
        else:
            return self.tables

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
                self.tables[table_name] = table_data

        return self.tables

    def get(self, table_name: str, data_id: str = None) -> Any:
        """获取数据表或指定行数据"""
        if table_name not in self.tables:
            return None
        if data_id is None:
            return self.tables[table_name]
        return self.tables[table_name].get(data_id)

    def get_data(self, table_name: str, data_id: str) -> Dict[str, Any]:
        """获取指定数据行（兼容旧接口）"""
        return self.get(table_name, data_id) or {}

    def close(self):
        """清理资源"""
        self.tables.clear()
