"""数据引用解析 - 支持 ${var}、表名.DataID.字段名、Return[-1] 等引用格式"""
import re
from typing import Any, Callable, Dict, Optional
from pathlib import Path


class DataResolver:
    def __init__(self, data_source: Optional[Dict[str, Any]] = None,
                 model_manager=None, data_manager=None,
                 global_vars: Optional[Dict[str, Dict[str, str]]] = None,
                 base_path=None,
                 return_provider: Optional[Callable[[int], Any]] = None):
        """
        Args:
            return_provider: 回调函数，接收 index 参数，返回对应步骤的返回值。
                            用于解析 Return[-1]、Return[0] 等引用。
                            典型实现: keyword_engine.get_return
        """
        self.data_source = data_source or {}
        self.model_manager = model_manager
        self.data_manager = data_manager
        self.global_vars = global_vars or {}
        self.base_path = Path(base_path) if base_path else None
        self.return_provider = return_provider

    def resolve(self, text: str) -> str:
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        text = self._resolve_returns(text)
        text = self._resolve_vars(text)
        text = self._resolve_models(text)
        text = self._resolve_ski_refs(text)
        return text

    def _resolve_returns(self, text: str) -> str:
        """解析 Return[index] 引用
        
        支持格式:
        - Return[-1]  → 上一个步骤的返回值
        - Return[-2]  → 上上个步骤的返回值
        - Return[0]   → 第一个步骤的返回值
        """
        if not self.return_provider:
            return text
        pattern = r'Return\[(-?\d+)\]'
        def replacer(match):
            index = int(match.group(1))
            value = self.return_provider(index)
            return str(value) if value is not None else match.group(0)
        return re.sub(pattern, replacer, text)

    def _resolve_vars(self, text: str) -> str:
        pattern = r'\$\{([^}]+)\}'
        def replacer(match):
            key = match.group(1)
            value = self._get_nested(self.data_source, key)
            return str(value) if value is not None else match.group(0)
        return re.sub(pattern, replacer, text)

    def _resolve_models(self, text: str) -> str:
        if not self.model_manager:
            return text
        pattern = r'@\{([^.}]+)\.([^}]+)\}'
        def replacer(match):
            model_name, field = match.group(1), match.group(2)
            value = self.model_manager.get(model_name, field=field)
            return str(value) if value is not None else match.group(0)
        return re.sub(pattern, replacer, text)

    def _resolve_ski_refs(self, text: str) -> str:
        pattern = r'([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z0-9_]+)\.([A-Za-z_][A-Za-z0-9_]*)'
        def replacer(match):
            table_name, data_id, field = match.group(1), match.group(2), match.group(3)
            if table_name == 'GlobalValue':
                return self.global_vars.get(data_id, {}).get(field, match.group(0))
            if self.data_manager:
                value = self.data_manager.get_data(table_name, data_id).get(field)
                return str(value) if value is not None else match.group(0)
            return match.group(0)
        return re.sub(pattern, replacer, text)

    def _get_nested(self, data: Dict, key: str) -> Any:
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def set_var(self, key: str, value: Any) -> None:
        self.data_source[key] = value

    def resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str):
                resolved[k] = self.resolve(v)
            else:
                resolved[k] = v
        return resolved

    def resolve_json(self, json_str: str) -> Dict[str, Any]:
        import json
        if isinstance(json_str, str) and json_str.startswith("@file:"):
            file_path = self.base_path / json_str[6:] if self.base_path else Path(json_str[6:])
            json_str = file_path.read_text()
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        return self._resolve_dict(data)

    def _resolve_dict(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self._resolve_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_dict(item) for item in data]
        elif isinstance(data, str):
            return self.resolve(data)
        return data
