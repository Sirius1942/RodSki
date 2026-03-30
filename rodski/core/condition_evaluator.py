"""Safe condition evaluator for dynamic step conditions"""
import ast
import operator
from typing import Dict, Any, Optional


class ConditionEvaluator:
    """Safely evaluate condition expressions"""

    OPERATORS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda x, y: x in y,
        ast.NotIn: lambda x, y: x not in y,
        ast.And: lambda x, y: x and y,
        ast.Or: lambda x, y: x or y,
        ast.Not: operator.not_,
    }

    BUILTINS = {
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'any': any,
        'all': all,
        'sum': sum,
        'abs': abs,
        'min': min,
        'max': max,
    }

    def evaluate(self, condition_str: str, variables: Dict[str, Any]) -> bool:
        """Evaluate condition string with variables"""
        if not condition_str or not condition_str.strip():
            return True

        try:
            tree = ast.parse(condition_str, mode='eval')
            result = self._safe_eval(tree.body, variables)
            return bool(result)
        except Exception:
            return False

    def _safe_eval(self, node: ast.AST, variables: Dict[str, Any]) -> Any:
        """Safely evaluate AST node"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return self._resolve_variable(node.id, variables)
        elif isinstance(node, ast.Attribute):
            obj = self._safe_eval(node.value, variables)
            if obj is None:
                return None
            return getattr(obj, node.attr, None)
        elif isinstance(node, ast.Compare):
            left = self._safe_eval(node.left, variables)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._safe_eval(comparator, variables)
                op_func = self.OPERATORS.get(type(op))
                if op_func is None or not op_func(left, right):
                    return False
                left = right
            return True
        elif isinstance(node, ast.BoolOp):
            op_func = self.OPERATORS.get(type(node.op))
            values = [self._safe_eval(v, variables) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
        elif isinstance(node, ast.UnaryOp):
            operand = self._safe_eval(node.operand, variables)
            op_func = self.OPERATORS.get(type(node.op))
            return op_func(operand) if op_func else None
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in self.BUILTINS:
                args = [self._safe_eval(arg, variables) for arg in node.args]
                return self.BUILTINS[func_name](*args)
        return None

    def _resolve_variable(self, name: str, variables: Dict[str, Any]) -> Any:
        """Resolve variable with ${} syntax support"""
        if name.startswith('${') and name.endswith('}'):
            name = name[2:-1]
        return variables.get(name)
