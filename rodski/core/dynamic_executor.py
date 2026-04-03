"""动态执行引擎 - 条件和循环支持

支持功能:
- 条件执行: if 语句基于变量值、页面状态、verify 结果
- 循环执行: loop 语句支持数据驱动
"""
import logging
import re
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.driver_factory import DriverWrapper

logger = logging.getLogger("rodski")


class DynamicExecutor:
    """动态执行控制器"""

    def __init__(self, data_resolver, return_values: Optional[List[Any]] = None):
        self.data_resolver = data_resolver
        self.variables: Dict[str, Any] = {}
        self._return_values = return_values or []  # 历史 verify/Return 结果

    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables[name] = value

    def get_variable(self, name: str) -> Any:
        """获取变量"""
        return self.variables.get(name)

    def add_return_value(self, value: Any) -> None:
        """记录一个 verify/Return 结果（用于 verify_fail 判断）"""
        self._return_values.append(value)

    def evaluate_condition(self, condition: str, driver: Any = None) -> bool:
        """评估条件表达式，支持 AND/OR 组合及多种原子条件类型。

        支持格式:
        - verify_fail                    # 上一步 verify 失败
        - ${Return[N].field == value}    # Return 字段比较
        - ${Return[N].field contains text}  # Return 字段包含
        - element_exists(locator)        # 元素可见
        - element_not_exists(locator)    # 元素不可见
        - text_contains(text)            # 页面含文字
        - text_not_contains(text)       # 页面不含文字
        - var == value / != / > / <      # 变量比较（原有）
        - (expr) AND (expr) / OR / NOT   # 逻辑组合
        """
        condition = condition.strip()
        logger.debug(f"评估条件: {condition}")
        if not condition:
            return True

        # 逻辑组合：AND
        if ' AND ' in condition.upper():
            # 不拆分 contains/contains 内的 AND
            parts = self._split_outside_quotes(condition, ' AND ', case_sensitive=False)
            return all(self.evaluate_condition(p.strip(), driver) for p in parts)

        # 逻辑组合：OR
        if ' OR ' in condition.upper():
            parts = self._split_outside_quotes(condition, ' OR ', case_sensitive=False)
            return any(self.evaluate_condition(p.strip(), driver) for p in parts)

        # 逻辑组合：NOT
        c_lower = condition.lower()
        if c_lower.startswith('not '):
            return not self.evaluate_condition(condition[4:].strip(), driver)

        # === 原子条件类型 ===
        # 1. verify_fail
        if c_lower == 'verify_fail':
            return self._eval_verify_fail()

        # 2. Return 字段比较
        if '${Return[' in condition:
            return self._eval_return_condition(condition)

        # 3. element_exists / element_not_exists
        if 'element_exists' in c_lower or 'element_not_exists' in c_lower:
            return self._eval_element_exists(condition, driver)

        # 4. text_contains / text_not_contains
        if 'text_contains' in c_lower or 'text_not_contains' in c_lower:
            return self._eval_text_contains(condition, driver)

        # 5. 变量比较（原有逻辑）
        for op in ['==', '!=', '>', '<', '>=', '<=']:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = self._resolve_value(parts[0].strip())
                    right = self._resolve_value(parts[1].strip())
                    if op == '==':
                        return str(left) == str(right)
                    elif op == '!=':
                        return str(left) != str(right)
                    elif op == '>':
                        return float(left) > float(right)
                    elif op == '<':
                        return float(left) < float(right)
                    elif op == '>=':
                        return float(left) >= float(right)
                    elif op == '<=':
                        return float(left) <= float(right)

        # 未知条件默认为 False
        logger.warning(f"[IF] 未知条件类型: {condition}")
        return False

    def _split_outside_quotes(
        self, s: str, sep: str, case_sensitive: bool = True
    ) -> List[str]:
        """在 sep 处拆分（忽略引号和括号内的 sep）"""
        parts = []
        depth = 0
        in_str = False
        str_char = None
        i = 0
        while i < len(s):
            c = s[i]
            if not in_str:
                if c in '"\'':
                    in_str = True
                    str_char = c
                elif c in '([{':
                    depth += 1
                elif c in ')]}':
                    depth -= 1
                elif depth == 0:
                    seg = sep if case_sensitive else sep.lower()
                    if not case_sensitive:
                        remaining = s[i:].lower()
                        if remaining.startswith(seg):
                            parts.append(s[:i])
                            s = s[i + len(sep):]
                            i = 0
                            continue
                    elif s[i:i + len(sep)] == sep:
                        parts.append(s[:i])
                        s = s[i + len(sep):]
                        i = 0
                        continue
            else:
                if c == str_char and (i == 0 or s[i - 1] != '\\'):
                    in_str = False
                    str_char = None
            i += 1
        parts.append(s)
        return parts

    # ---- 原子条件实现 ----

    def _eval_verify_fail(self) -> bool:
        """verify_fail — 上一步 verify 是否失败"""
        if not self._return_values:
            return False
        last = self._return_values[-1]
        if isinstance(last, dict):
            # {'passed': bool} 或 {'_verify_passed': bool}
            return last.get('passed', last.get('_verify_passed', True)) is False
        return last is False

    def _eval_return_condition(self, condition: str) -> bool:
        """${Return[N].field ==/contains value}"""
        m = re.search(r'\$\{Return\[(-?\d+)\]\.(\w+)\s*(contains|==|!=|>|<|>=|<=)\s*[\'""]?(.+?)[\'""]?\}', condition)
        if not m:
            return False
        idx_str, field, op, value = m.group(1), m.group(2), m.group(3), m.group(4)
        idx = int(idx_str)
        values = self._return_values
        if not values or abs(idx) > len(values):
            return False
        actual = values[idx]
        if isinstance(actual, dict):
            actual = actual.get(field, '')
        else:
            actual = str(actual)
        value = value.strip().strip('"\'')
        if op == 'contains':
            return value in actual
        elif op == '==':
            return str(actual) == value
        elif op == '!=':
            return str(actual) != value
        elif op == '>':
            return float(actual) > float(value)
        elif op == '<':
            return float(actual) < float(value)
        elif op == '>=':
            return float(actual) >= float(value)
        elif op == '<=':
            return float(actual) <= float(value)
        return False

    def _eval_element_exists(self, condition: str, driver: Any = None) -> bool:
        """element_exists(locator) 或 element_not_exists(locator)"""
        neg = 'element_not_exists' in condition.lower()
        m = re.search(r'element_[a-z_]+\s*\(\s*([^)]+?)\s*\)', condition, re.IGNORECASE)
        if not m:
            return False
        locator = m.group(1).strip()
        if driver is None:
            logger.warning(f"[IF] element_exists 需要 driver，但 driver 为 None")
            return False
        try:
            bbox = driver.locate_element(locator)
            exists = bbox is not None
            return not exists if neg else exists
        except Exception:
            return True if neg else False

    def _eval_text_contains(self, condition: str, driver: Any = None) -> bool:
        """text_contains(text) 或 text_not_contains(text)"""
        neg = 'text_not_contains' in condition.lower()
        m = re.search(r'text[_-]?contains\s*\(\s*[\'"]?(.+?)[\'"]?\s*\)', condition, re.IGNORECASE)
        if not m:
            return False
        text = m.group(1).strip().strip('"\'')
        if driver is None:
            logger.warning(f"[IF] text_contains 需要 driver，但 driver 为 None")
            return False
        try:
            page_text = driver.get_page_text() if hasattr(driver, 'get_page_text') else ''
            found = text in page_text
            return not found if neg else found
        except Exception:
            return False

    def _resolve_value(self, value: str) -> Any:
        """解析值（变量或字面量）"""
        value = value.strip()

        # 检查是否是变量引用
        if value.startswith('$'):
            var_name = value[1:]
            return self.variables.get(var_name, value)

        # 使用数据解析器解析
        resolved = self.data_resolver.resolve(value)
        return resolved

    def parse_loop_range(self, loop_spec: str) -> List[Any]:
        """解析循环范围

        支持格式:
        - 1,2,3 (列表)
        - 1-5 (范围)
        - $varname (变量)
        - table:tablename (数据表)
        """
        loop_spec = loop_spec.strip()

        # 变量引用
        if loop_spec.startswith('$'):
            var_name = loop_spec[1:]
            value = self.variables.get(var_name, [])
            if isinstance(value, list):
                return value
            return [value]

        # 数据表引用
        if loop_spec.startswith('table:'):
            table_name = loop_spec[6:]
            # 返回表名，由调用方处理
            return [f"table:{table_name}"]

        # 范围
        if '-' in loop_spec and loop_spec.replace('-', '').isdigit():
            parts = loop_spec.split('-')
            if len(parts) == 2:
                start = int(parts[0])
                end = int(parts[1])
                return list(range(start, end + 1))

        # 逗号分隔列表
        if ',' in loop_spec:
            return [item.strip() for item in loop_spec.split(',')]

        # 单个值
        return [loop_spec]
