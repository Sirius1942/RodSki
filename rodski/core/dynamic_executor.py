"""动态执行引擎 - 条件和循环支持

支持功能:
- 条件执行: if 语句基于变量值
- 循环执行: loop 语句支持数据驱动
"""
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("rodski")


class DynamicExecutor:
    """动态执行控制器"""

    def __init__(self, data_resolver):
        self.data_resolver = data_resolver
        self.variables: Dict[str, Any] = {}

    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables[name] = value

    def get_variable(self, name: str) -> Any:
        """获取变量"""
        return self.variables.get(name)

    def evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式

        支持格式:
        - var==value
        - var!=value
        - var>value
        - var<value
        """
        condition = condition.strip()

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
