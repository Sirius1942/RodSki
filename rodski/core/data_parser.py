"""数据引用解析器 - 支持 DataTable.DataID.Field 格式"""
# DEPRECATED: 遗留 Excel 解析代码，新代码应使用 data/data_resolver.py
# 保留此模块仅为向后兼容，XML 模式不使用此解析器
# 注意：此模块使用 ${Return[-1]} 格式，而当前标准格式为 Return[-1]（不带 ${}）
import re
from typing import Dict, Any, Optional
from pathlib import Path
from data.excel_parser import ExcelParser


class DataParser:
    def __init__(self, data_dir: Optional[Path] = None, keyword_engine=None):
        self.data_dir = data_dir or Path.cwd() / "data"
        self._cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.keyword_engine = keyword_engine

    def resolve(self, text: str) -> str:
        """解析文本中的数据引用，支持 DataTable.DataID.Field 和 Return[x] 格式"""
        if not isinstance(text, str):
            return str(text) if text is not None else ""

        # 解析 Return[x] 格式
        return_pattern = r'\$\{Return\[(-?\d+)\]\}'

        def return_replacer(match):
            if not self.keyword_engine:
                return match.group(0)
            index = int(match.group(1))
            value = self.keyword_engine.get_return(index)
            return str(value) if value is not None else match.group(0)

        text = re.sub(return_pattern, return_replacer, text)

        # 解析 DataTable.DataID.Field 格式
        pattern = r'\$\{([^.}]+)\.([^.}]+)\.([^}]+)\}'

        def replacer(match):
            table_name = match.group(1)
            data_id = match.group(2)
            field = match.group(3)

            value = self.get_value(table_name, data_id, field)
            return str(value) if value is not None else match.group(0)

        return re.sub(pattern, replacer, text)

    def get_value(self, table_name: str, data_id: str, field: str) -> Optional[Any]:
        """获取指定数据表中的字段值"""
        if table_name not in self._cache:
            self._load_table(table_name)

        if table_name not in self._cache:
            return None

        table_data = self._cache[table_name]
        if data_id not in table_data:
            return None

        return table_data[data_id].get(field)

    def _load_table(self, table_name: str) -> None:
        """加载数据表到缓存"""
        excel_path = self.data_dir / f"{table_name}.xlsx"

        if not excel_path.exists():
            return

        try:
            parser = ExcelParser(str(excel_path))
            rows = parser.parse()
            parser.close()

            table_data = {}
            for row in rows:
                row_id = row.get("id") or row.get("ID")
                if row_id:
                    table_data[str(row_id)] = row

            self._cache[table_name] = table_data
        except Exception:
            pass

    def resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """解析参数字典中的所有数据引用"""
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str):
                resolved[k] = self.resolve(v)
            elif isinstance(v, dict):
                resolved[k] = self.resolve_params(v)
            elif isinstance(v, list):
                resolved[k] = [self.resolve(item) if isinstance(item, str) else item for item in v]
            else:
                resolved[k] = v
        return resolved

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

