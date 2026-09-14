"""数据引用解析 - 支持 ${var}、表名.DataID.字段名、${Return[-1]} 等引用格式"""
import re
from typing import Any, Callable, Dict, Optional
from pathlib import Path

try:
    from rodski.data.builtin_functions import call_function, is_nondeterministic
except ImportError:
    from rodski.data.builtin_functions import call_function, is_nondeterministic

_FUNC_PATTERN = re.compile(r'\$\{(\w+)\(([^)]*)\)\}')
_ESCAPE_PATTERN = re.compile(r'\$\$\{')


# Path navigation supporting dotted keys (.key), array indices ([idx]), and v11 array helpers
# v11.0.0: Added .first(), .last(), .length support
_PATH_TOKEN = re.compile(r'(?:(?:\.([A-Za-z0-9_$]+)(?:\(\))?)|(?:\[(-?\d+)\]))')


def _nav_path(value, path):
    """Navigate `value` along a path string supporting .key, [idx], and array helpers.

    v11.0.0 新增数组辅助方法:
    - .first() - 取第一个元素 (等价于 [0])
    - .last() - 取最后一个元素 (等价于 [-1])
    - .length - 数组长度 (返回 int)

    Args:
        value: 待导航的值 (dict/list/tuple 或其他)
        path: 路径字符串，如 '.data.items[0].name' 或 '.data.first().id'

    Returns:
        解析后的值，如果任何路径段无法解析则返回 None

    Examples:
        _nav_path({'data': [1, 2, 3]}, '.data[0]') → 1
        _nav_path({'data': [1, 2, 3]}, '.data.first()') → 1
        _nav_path({'data': [1, 2, 3]}, '.data.last()') → 3
        _nav_path({'data': [1, 2, 3]}, '.data.length') → 3
    """
    if value is None:
        return None
    # tolerate bare paths (no leading dot), e.g. 'data.data[0].name'
    if path and path[0] not in ('.', '['):
        path = '.' + path
    pos = 0
    cur = value
    while pos < len(path):
        m = _PATH_TOKEN.match(path, pos)
        if not m:
            return None
        if m.group(1) is not None:  # .key or .method()
            key = m.group(1)
            # v11.0.0: 数组辅助方法
            if key == 'first' and isinstance(cur, (list, tuple)):
                cur = cur[0] if len(cur) > 0 else None
            elif key == 'last' and isinstance(cur, (list, tuple)):
                cur = cur[-1] if len(cur) > 0 else None
            elif key == 'length' and isinstance(cur, (list, tuple)):
                return len(cur)  # length 是终端值，直接返回 int
            elif isinstance(cur, dict):
                cur = cur.get(key)
            else:
                return None
        else:  # [idx]
            idx = int(m.group(2))
            if isinstance(cur, (list, tuple)):
                try:
                    cur = cur[idx]
                except IndexError:
                    return None
            else:
                return None
        if cur is None:
            return None
        pos = m.end()
    return cur


class DataResolver:
    def __init__(self, data_source: Optional[Dict[str, Any]] = None,
                 model_manager=None, data_manager=None,
                 global_vars: Optional[Dict[str, Dict[str, str]]] = None,
                 base_path=None,
                 return_provider: Optional[Callable[[int], Any]] = None):
        """
        Args:
            return_provider: 回调函数，接收 index 参数，返回对应步骤的返回值。
                            用于解析 ${Return[-1]}、${Return[0]} 等引用。
                            典型实现: keyword_engine.get_return
        """
        self.data_source = data_source or {}
        self.model_manager = model_manager
        self.data_manager = data_manager
        self.global_vars = global_vars or {}
        self.base_path = Path(base_path) if base_path else None
        self.return_provider = return_provider

    def resolve(self, text: str) -> str:
        """解析数据引用（Case Sheet 层面，不含 Return）"""
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        text = self._resolve_functions(text)
        text = self._resolve_vars(text)
        text = self._resolve_models(text)
        text = self._resolve_ski_refs(text)
        return text

    def resolve_case_data(self, text: str) -> str:
        """解析 Case XML `data` 属性。

        **纯函数类内置函数允许**（`encodeURI` / `decodeURI` / `toUpperCase` /
        `toLowerCase` / `toString36` / `upper` / `lower` / `concat`）—— 同输入
        同输出，用例可复现。`set` 是它们的主要用武之地：`set` 的表达式只能来自
        Case XML 的 data 属性，这正是 v11.0.0 §4.4.4 示例的写法。

        **数据生成类内置函数禁止**（`random` / `date` / `timestamp*`）—— 每次求值
        都不同。写在 Case XML 里会让用例不可复现：loop 每轮重新解析、失败重跑
        重新解析，两次跑出的值不一样；而 result.xml 不记录解析后的值，事后无从
        对账。它们只能写在 data.sqlite 字段值中（数据行本就是"执行时现取"的语义）。

        见 CORE_DESIGN_CONSTRAINTS.md §4.4.6 规则 5。
        """
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        self._reject_nondeterministic_functions(text)
        text = self._resolve_returns(text)
        text = self._resolve_functions(text)
        text = self._resolve_vars(text)
        text = self._resolve_models(text)
        text = self._resolve_ski_refs(text)
        return text

    def resolve_with_return(self, text: str) -> str:
        """解析数据引用 + Return 引用（数据表字段值使用）"""
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        text = self._resolve_returns(text)
        text = self._resolve_functions(text)
        text = self._resolve_vars(text)
        text = self._resolve_models(text)
        text = self._resolve_ski_refs(text)
        return text

    def _resolve_returns(self, text: str) -> str:
        """解析 ${Return[index]} 和 ${Return[index].field.subfield} 引用

        支持格式:
        - ${Return[-1]}               → 上一个步骤的返回值（整体）
        - ${Return[-1].code}          → 上一步返回值中的 code 字段
        - ${Return[-1].data.inquiryId} → 上一步返回值中的嵌套字段
        - ${Return[0]}                → 第一个步骤的返回值
        """
        if not self.return_provider:
            return text
        # path supports both .key and [idx] segments, e.g. .data.data[0].name
        # v11.0.0: also supports array helpers .first(), .last(), .length
        pattern = r'\$\{Return\[(-?\d+)\]((?:(?:\.\w+(?:\(\))?)|(?:\[-?\d+\]))*)\}'

        def replacer(match):
            index = int(match.group(1))
            path = match.group(2)  # e.g. ".data.inquiryId" or ""
            value = self.return_provider(index)
            if value is None:
                return match.group(0)
            # Navigate nested fields via dot path / array indices
            if path:
                value = _nav_path(value, path)
                if value is None:
                    return match.group(0)
            return str(value) if value is not None else match.group(0)

        return re.sub(pattern, replacer, text)

    def _resolve_function_arg(self, arg: str) -> str:
        """Resolve a single builtin-function argument before passing it to the function.

        Handles:
        - full reference: ``${var}`` / ``${Return[-1].field}``
        - bare ``Return[...]`` path (e.g. ``Return[-1].data.id``)
        - bare variable / dotted path in data_source (e.g. ``inquiryId``, ``created.inquiryId``)
        - literals (numbers, strings with spaces, etc.) -> unchanged
        """
        arg = arg.strip()
        if not arg:
            return arg
        if arg.startswith('${'):
            return self.resolve_with_return(arg)
        # bare Return[...] path
        if re.fullmatch(r'Return\[-?\d+\](?:(?:\.\w+)|(?:\[-?\d+\]))*', arg):
            wrapped = '${' + arg + '}'
            resolved = self._resolve_returns(wrapped)
            if resolved != wrapped:
                return resolved
            return arg
        # bare variable / dotted path
        if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$.\[\]]*', arg):
            val = self._get_nested(self.data_source, arg)
            if val is not None:
                return str(val)
        return arg

    def _reject_nondeterministic_functions(self, text: str) -> None:
        """Case XML data 属性中出现数据生成类内置函数时抛错。

        先剥掉 `$${` 转义（`$${random(1)}` 是要发给被测系统的字面量，不是调用），
        再找 `${name(...)}`；只对**已注册**的函数报错 —— `${undefined(` 之类是
        普通文本，不该拦。
        """
        _ESCAPE_PLACEHOLDER = '\x00ESCAPE\x00'
        scrubbed = _ESCAPE_PATTERN.sub(_ESCAPE_PLACEHOLDER, text)
        for match in _FUNC_PATTERN.finditer(scrubbed):
            func_name = match.group(1)
            if is_nondeterministic(func_name):
                raise ValueError(
                    f"内置函数 ${{{func_name}(...)}} 只能写在 data.sqlite 字段值中，"
                    f"不能写在 Case XML data 属性中"
                )

    def _resolve_functions(self, text: str) -> str:
        """解析内置函数引用 ${func(args...)}"""
        _ESCAPE_PLACEHOLDER = '\x00ESCAPE\x00'
        text = _ESCAPE_PATTERN.sub(_ESCAPE_PLACEHOLDER, text)

        def replacer(match):
            func_name = match.group(1)
            args_str = match.group(2)
            args = [self._resolve_function_arg(a) for a in args_str.split(',') if a.strip()]
            try:
                return str(call_function(func_name, args))
            except ValueError:
                return match.group(0)

        text = _FUNC_PATTERN.sub(replacer, text)
        text = text.replace(_ESCAPE_PLACEHOLDER, '${')
        return text

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
        # Support both dotted keys and array indices in a single segment/nested path.
        if _PATH_TOKEN.search(key):
            return _nav_path(data, key)
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
