"""全局变量 XML 解析器 - 解析 globalvalue.xml

从 data/globalvalue.xml 解析全局变量，替代原 Excel GlobalValue Sheet。
XML 格式参见 schemas/globalvalue.xsd。
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict

from core.xml_schema_validator import RodskiXmlValidator


class GlobalValueParser:
    def __init__(self, globalvalue_path: str):
        """初始化全局变量解析器

        Args:
            globalvalue_path: globalvalue.xml 文件路径
        """
        self.globalvalue_path = Path(globalvalue_path)

    def parse(self) -> Dict[str, Dict[str, str]]:
        """解析全局变量，返回 {分组名: {变量名: 值}}"""
        if not self.globalvalue_path.exists():
            return {}

        RodskiXmlValidator.validate_file(
            self.globalvalue_path, RodskiXmlValidator.KIND_GLOBALVALUE
        )
        tree = ET.parse(self.globalvalue_path)
        root = tree.getroot()
        global_vars: Dict[str, Dict[str, str]] = {}

        for group_node in root.findall('group'):
            group_name = (group_node.get('name') or '').strip()
            if not group_name:
                continue

            group_vars: Dict[str, str] = {}
            for var_node in group_node.findall('var'):
                var_name = (var_node.get('name') or '').strip()
                var_value = (var_node.get('value') or '').strip()
                if var_name:
                    group_vars[var_name] = var_value

            if group_vars:
                global_vars[group_name] = group_vars

        return global_vars

    def close(self):
        pass
