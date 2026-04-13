"""ConditionEvaluator 单元测试

测试 core/condition_evaluator.py 中的安全条件表达式评估器。
覆盖：比较运算符、布尔运算、内置函数调用、变量解析、边界条件。
对应核心设计约束 §12（if/else 条件分支）。
"""
import pytest
from core.condition_evaluator import ConditionEvaluator


class TestConditionEvaluatorBasic:
    """基础条件评估 —— 常量、简单比较、空输入"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()

    # ---- 空/空白条件默认返回 True ----
    def test_empty_string_returns_true(self):
        """空字符串条件应默认返回 True（无条件 = 始终执行）"""
        assert self.evaluator.evaluate("", {}) is True

    def test_whitespace_only_returns_true(self):
        """纯空白字符串应视为空条件，返回 True"""
        assert self.evaluator.evaluate("   ", {}) is True

    def test_none_condition_returns_true(self):
        """None 条件应默认返回 True"""
        assert self.evaluator.evaluate(None, {}) is True

    # ---- 常量表达式 ----
    def test_constant_true(self):
        """常量 True 应评估为 True"""
        assert self.evaluator.evaluate("True", {}) is True

    def test_constant_false(self):
        """常量 False 应评估为 False"""
        assert self.evaluator.evaluate("False", {}) is False

    def test_constant_integer_truthy(self):
        """非零整数应评估为 True"""
        assert self.evaluator.evaluate("1", {}) is True

    def test_constant_zero_falsy(self):
        """整数零应评估为 False"""
        assert self.evaluator.evaluate("0", {}) is False


class TestConditionEvaluatorComparison:
    """比较运算符测试 —— ==, !=, <, <=, >, >=, in, not in"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()
        self.variables = {"status": 200, "name": "admin", "items": [1, 2, 3]}

    def test_eq_true(self):
        """== 运算符：变量等于预期值时返回 True"""
        assert self.evaluator.evaluate("status == 200", self.variables) is True

    def test_eq_false(self):
        """== 运算符：变量不等于预期值时返回 False"""
        assert self.evaluator.evaluate("status == 404", self.variables) is False

    def test_not_eq(self):
        """!= 运算符：变量不等于值时返回 True"""
        assert self.evaluator.evaluate("status != 404", self.variables) is True

    def test_lt(self):
        """< 运算符：小于比较"""
        assert self.evaluator.evaluate("status < 300", self.variables) is True

    def test_lte(self):
        """<= 运算符：小于等于比较"""
        assert self.evaluator.evaluate("status <= 200", self.variables) is True

    def test_gt(self):
        """> 运算符：大于比较"""
        assert self.evaluator.evaluate("status > 100", self.variables) is True

    def test_gte(self):
        """>= 运算符：大于等于比较"""
        assert self.evaluator.evaluate("status >= 200", self.variables) is True

    def test_string_eq(self):
        """字符串相等比较"""
        assert self.evaluator.evaluate("name == 'admin'", self.variables) is True

    def test_in_operator(self):
        """in 运算符：值存在于列表中"""
        assert self.evaluator.evaluate("2 in items", self.variables) is True

    def test_not_in_operator(self):
        """not in 运算符：值不在列表中"""
        assert self.evaluator.evaluate("5 not in items", self.variables) is True

    def test_chained_comparison(self):
        """链式比较：100 < status < 300"""
        assert self.evaluator.evaluate("100 < status < 300", self.variables) is True


class TestConditionEvaluatorBoolOps:
    """布尔运算测试 —— and, or, not"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()
        self.variables = {"a": True, "b": False, "x": 10}

    def test_and_both_true(self):
        """and 运算：两边都为 True 时返回 True"""
        assert self.evaluator.evaluate("a and x > 5", self.variables) is True

    def test_and_one_false(self):
        """and 运算：有一边为 False 时返回 False"""
        assert self.evaluator.evaluate("a and b", self.variables) is False

    def test_or_one_true(self):
        """or 运算：有一边为 True 时返回 True"""
        assert self.evaluator.evaluate("a or b", self.variables) is True

    def test_or_both_false(self):
        """or 运算：两边都为 False 时返回 False"""
        assert self.evaluator.evaluate("b or b", self.variables) is False

    def test_not_true(self):
        """not 运算：取反 True → False"""
        assert self.evaluator.evaluate("not b", self.variables) is True

    def test_not_false(self):
        """not 运算：取反 False → True"""
        assert self.evaluator.evaluate("not a", self.variables) is False


class TestConditionEvaluatorBuiltins:
    """内置函数调用测试 —— len, str, int, float, bool, any, all 等"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()

    def test_len_function(self):
        """len() 函数：检查列表长度"""
        variables = {"items": [1, 2, 3]}
        assert self.evaluator.evaluate("len(items) == 3", variables) is True

    def test_str_function(self):
        """str() 函数：类型转换"""
        variables = {"num": 42}
        assert self.evaluator.evaluate("str(num) == '42'", variables) is True

    def test_int_function(self):
        """int() 函数：字符串转整数"""
        variables = {"val": "100"}
        assert self.evaluator.evaluate("int(val) > 50", variables) is True

    def test_abs_function(self):
        """abs() 函数：绝对值"""
        variables = {"n": -5}
        assert self.evaluator.evaluate("abs(n) == 5", variables) is True

    def test_min_max_function(self):
        """min()/max() 函数"""
        variables = {"a": 3, "b": 7}
        assert self.evaluator.evaluate("max(a, b) == 7", variables) is True


class TestConditionEvaluatorAttribute:
    """属性访问测试 —— obj.attr 格式"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()

    def test_attribute_access(self):
        """对象属性访问：response.status"""
        class Resp:
            status = 200
        variables = {"response": Resp()}
        assert self.evaluator.evaluate("response.status == 200", variables) is True

    def test_attribute_none_obj(self):
        """属性访问时对象为 None，应安全返回 None → False"""
        variables = {"response": None}
        # None.status → None, None == 200 → False
        assert self.evaluator.evaluate("response.status == 200", variables) is False


class TestConditionEvaluatorVariableResolution:
    """变量解析测试 —— 普通变量和 ${} 语法"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()

    def test_simple_variable(self):
        """普通变量名解析"""
        assert self.evaluator.evaluate("count > 0", {"count": 5}) is True

    def test_missing_variable_returns_false(self):
        """变量不存在时，比较结果应安全返回 False"""
        # undefined 变量解析为 None，None > 0 会抛异常，外层 catch 返回 False
        assert self.evaluator.evaluate("undefined_var > 0", {}) is False


class TestConditionEvaluatorEdgeCases:
    """边界条件测试 —— 语法错误、不安全表达式"""

    def setup_method(self):
        self.evaluator = ConditionEvaluator()

    def test_syntax_error_returns_false(self):
        """语法错误的表达式应安全返回 False（不抛异常）"""
        assert self.evaluator.evaluate("if then else", {}) is False

    def test_invalid_expression_returns_false(self):
        """无法解析的表达式应返回 False"""
        assert self.evaluator.evaluate("+++", {}) is False

    def test_unsupported_call_returns_false(self):
        """调用不在 BUILTINS 白名单中的函数应安全失败"""
        # exec/eval/import 不在白名单中
        assert self.evaluator.evaluate("exec('print(1)')", {}) is False

    def test_operators_dict_completeness(self):
        """验证 OPERATORS 字典包含所有必要的运算符"""
        import ast
        required_ops = [ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
                        ast.In, ast.NotIn, ast.And, ast.Or, ast.Not]
        for op in required_ops:
            assert op in ConditionEvaluator.OPERATORS, f"缺少运算符: {op}"

    def test_builtins_dict_completeness(self):
        """验证 BUILTINS 字典包含所有声明的内置函数"""
        expected = {'len', 'str', 'int', 'float', 'bool', 'any', 'all', 'sum', 'abs', 'min', 'max'}
        assert set(ConditionEvaluator.BUILTINS.keys()) == expected
