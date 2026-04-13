"""DynamicExecutor 单元测试

测试 core/dynamic_executor.py 中的动态执行控制器。
覆盖：条件评估（verify_fail / Return比较 / element_exists / text_contains /
      变量比较 / AND/OR/NOT 组合）、变量管理、循环范围解析。
对应核心设计约束 §12（if/else 条件分支）。
"""
import pytest
from unittest.mock import MagicMock
from core.dynamic_executor import DynamicExecutor


@pytest.fixture
def resolver():
    """创建一个简单的 mock DataResolver"""
    r = MagicMock()
    r.resolve.side_effect = lambda v: v  # 默认原样返回
    return r


@pytest.fixture
def executor(resolver):
    """创建默认的 DynamicExecutor 实例"""
    return DynamicExecutor(data_resolver=resolver)


# =====================================================================
# 变量管理
# =====================================================================
class TestVariableManagement:
    """变量的设置和获取"""

    def test_set_and_get_variable(self, executor):
        """set_variable 后应能 get_variable 取回"""
        executor.set_variable("token", "abc123")
        assert executor.get_variable("token") == "abc123"

    def test_get_undefined_variable_returns_none(self, executor):
        """获取未定义变量应返回 None"""
        assert executor.get_variable("nonexistent") is None

    def test_add_return_value(self, executor):
        """add_return_value 应追加到 _return_values 列表"""
        executor.add_return_value({"status": 200})
        executor.add_return_value({"status": 404})
        assert len(executor._return_values) == 2
        assert executor._return_values[-1]["status"] == 404


# =====================================================================
# verify_fail 条件
# =====================================================================
class TestVerifyFail:
    """verify_fail 原子条件 —— 检查上一步 verify 是否失败"""

    def test_verify_fail_no_return_values(self, executor):
        """无历史返回值时 verify_fail 应返回 False"""
        assert executor.evaluate_condition("verify_fail") is False

    def test_verify_fail_last_passed(self, executor):
        """上一步 passed=True 时 verify_fail 应返回 False"""
        executor.add_return_value({"passed": True})
        assert executor.evaluate_condition("verify_fail") is False

    def test_verify_fail_last_failed(self, executor):
        """上一步 passed=False 时 verify_fail 应返回 True"""
        executor.add_return_value({"passed": False})
        assert executor.evaluate_condition("verify_fail") is True

    def test_verify_fail_with_verify_passed_key(self, executor):
        """使用 _verify_passed 键时也应正确判断"""
        executor.add_return_value({"_verify_passed": False})
        assert executor.evaluate_condition("verify_fail") is True

    def test_verify_fail_last_is_false_literal(self, executor):
        """返回值为 False 字面量时 verify_fail 应返回 True"""
        executor.add_return_value(False)
        assert executor.evaluate_condition("verify_fail") is True


# =====================================================================
# Return 字段比较条件
# =====================================================================
class TestReturnCondition:
    """${Return[N].field op value} 条件评估"""

    def test_return_field_eq(self, executor):
        """Return 字段相等比较"""
        executor.add_return_value({"status": "200", "token": "abc"})
        cond = "${Return[-1].status == 200}"
        assert executor.evaluate_condition(cond) is True

    def test_return_field_contains(self, executor):
        """Return 字段包含文本"""
        executor.add_return_value({"msg": "操作成功，请继续"})
        cond = "${Return[-1].msg contains 成功}"
        assert executor.evaluate_condition(cond) is True

    def test_return_field_not_eq(self, executor):
        """Return 字段不等于比较"""
        executor.add_return_value({"status": "404"})
        cond = "${Return[-1].status != 200}"
        assert executor.evaluate_condition(cond) is True

    def test_return_index_out_of_range(self, executor):
        """Return 索引超出范围应返回 False"""
        cond = "${Return[-1].status == 200}"
        # 没有任何返回值
        assert executor.evaluate_condition(cond) is False

    def test_return_invalid_format(self, executor):
        """格式不正确的 Return 条件应返回 False"""
        executor.add_return_value({"status": 200})
        cond = "${Return[bad].status == 200}"
        assert executor.evaluate_condition(cond) is False


# =====================================================================
# element_exists / element_not_exists 条件
# =====================================================================
class TestElementExists:
    """element_exists(locator) 和 element_not_exists(locator) 条件"""

    def test_element_exists_found(self, executor):
        """元素存在时 element_exists 返回 True"""
        driver = MagicMock()
        driver.locate_element.return_value = (10, 20, 100, 50)  # 返回 bbox
        assert executor.evaluate_condition("element_exists(#login-btn)", driver) is True

    def test_element_exists_not_found(self, executor):
        """元素不存在时 element_exists 返回 False"""
        driver = MagicMock()
        driver.locate_element.return_value = None
        assert executor.evaluate_condition("element_exists(#login-btn)", driver) is False

    def test_element_not_exists_found(self, executor):
        """元素存在时 element_not_exists 返回 False"""
        driver = MagicMock()
        driver.locate_element.return_value = (10, 20, 100, 50)
        assert executor.evaluate_condition("element_not_exists(.error)", driver) is False

    def test_element_not_exists_not_found(self, executor):
        """元素不存在时 element_not_exists 返回 True"""
        driver = MagicMock()
        driver.locate_element.return_value = None
        assert executor.evaluate_condition("element_not_exists(.error)", driver) is True

    def test_element_exists_no_driver(self, executor):
        """没有 driver 时 element_exists 应返回 False"""
        assert executor.evaluate_condition("element_exists(#btn)", None) is False

    def test_element_exists_driver_exception(self, executor):
        """driver 抛异常时 element_exists 应返回 False"""
        driver = MagicMock()
        driver.locate_element.side_effect = RuntimeError("element error")
        assert executor.evaluate_condition("element_exists(#btn)", driver) is False


# =====================================================================
# text_contains / text_not_contains 条件
# =====================================================================
class TestTextContains:
    """text_contains(text) 和 text_not_contains(text) 条件"""

    def test_text_contains_found(self, executor):
        """页面包含指定文字时返回 True"""
        driver = MagicMock()
        driver.get_page_text.return_value = "欢迎登录系统"
        assert executor.evaluate_condition("text_contains('欢迎')", driver) is True

    def test_text_contains_not_found(self, executor):
        """页面不包含指定文字时返回 False"""
        driver = MagicMock()
        driver.get_page_text.return_value = "欢迎登录系统"
        assert executor.evaluate_condition("text_contains('错误')", driver) is False

    def test_text_not_contains_found(self, executor):
        """页面包含文字时 text_not_contains 返回 False
        注意：当前源码有 bug（正则 r'text[_-]?contains' 无法匹配 text_not_contains），
        返回 False 是因为 regex 不匹配直接 return False，而非正确判断页面内容。
        此测试能通过但原因不正确 —— 等源码修复后应观察是否仍通过"""
        driver = MagicMock()
        driver.get_page_text.return_value = "操作失败"
        assert executor.evaluate_condition("text_not_contains('失败')", driver) is False

    @pytest.mark.xfail(
        reason="源码 bug：同上，正则无法匹配 text_not_contains 格式"
    )
    def test_text_not_contains_not_found(self, executor):
        """页面不包含文字时 text_not_contains 返回 True"""
        driver = MagicMock()
        driver.get_page_text.return_value = "操作成功"
        assert executor.evaluate_condition("text_not_contains('失败')", driver) is True

    def test_text_contains_no_driver(self, executor):
        """没有 driver 时 text_contains 应返回 False"""
        assert executor.evaluate_condition("text_contains('test')", None) is False


# =====================================================================
# 变量比较条件
# =====================================================================
class TestVariableComparison:
    """变量比较条件：$var == value / != / > / < / >= / <="""

    def test_variable_eq(self, executor):
        """变量相等比较"""
        executor.set_variable("status", "200")
        assert executor.evaluate_condition("$status == 200") is True

    def test_variable_not_eq(self, executor):
        """变量不等于比较"""
        executor.set_variable("status", "404")
        assert executor.evaluate_condition("$status != 200") is True

    def test_variable_gt(self, executor):
        """变量大于比较"""
        executor.set_variable("count", "5")
        assert executor.evaluate_condition("$count > 3") is True

    def test_variable_lt(self, executor):
        """变量小于比较"""
        executor.set_variable("count", "2")
        assert executor.evaluate_condition("$count < 5") is True

    @pytest.mark.xfail(
        reason="源码 bug：运算符列表 ['==','!=','>','<','>=','<='] 中 '>' 排在 '>=' 前面，"
               "'$count >= 5' 会先匹配到 '>' 并按 '>' 拆分，导致右侧变成 '= 5'。"
               "修复方案：将运算符按长度降序排列（>=,<=,==,!=,>,<）"
    )
    def test_variable_gte(self, executor):
        """变量大于等于比较"""
        executor.set_variable("count", "5")
        assert executor.evaluate_condition("$count >= 5") is True

    @pytest.mark.xfail(
        reason="源码 bug：同 test_variable_gte，'<' 排在 '<=' 前面导致拆分错误"
    )
    def test_variable_lte(self, executor):
        """变量小于等于比较"""
        executor.set_variable("count", "5")
        assert executor.evaluate_condition("$count <= 5") is True


# =====================================================================
# 逻辑组合：AND / OR / NOT
# =====================================================================
class TestLogicalCombination:
    """AND / OR / NOT 逻辑组合条件"""

    def test_and_both_true(self, executor):
        """AND：两个条件都为 True"""
        executor.add_return_value({"passed": False})
        driver = MagicMock()
        driver.locate_element.return_value = (1, 2, 3, 4)
        # verify_fail=True AND element_exists=True → True
        assert executor.evaluate_condition(
            "verify_fail AND element_exists(#dialog)", driver
        ) is True

    def test_and_one_false(self, executor):
        """AND：一个条件为 False → 返回 False"""
        executor.add_return_value({"passed": True})
        driver = MagicMock()
        driver.locate_element.return_value = (1, 2, 3, 4)
        # verify_fail=False AND element_exists=True → False
        assert executor.evaluate_condition(
            "verify_fail AND element_exists(#dialog)", driver
        ) is False

    def test_or_one_true(self, executor):
        """OR：一个条件为 True → 返回 True"""
        executor.add_return_value({"passed": True})
        driver = MagicMock()
        driver.locate_element.return_value = (1, 2, 3, 4)
        # verify_fail=False OR element_exists=True → True
        assert executor.evaluate_condition(
            "verify_fail OR element_exists(#dialog)", driver
        ) is True

    def test_not_condition(self, executor):
        """NOT：取反条件"""
        executor.add_return_value({"passed": True})
        # verify_fail=False → NOT False = True
        assert executor.evaluate_condition("NOT verify_fail") is True


# =====================================================================
# 空条件和未知条件
# =====================================================================
class TestEdgeCases:
    """边界条件和未知条件类型"""

    def test_empty_condition_returns_true(self, executor):
        """空条件应返回 True（始终执行）"""
        assert executor.evaluate_condition("") is True

    def test_whitespace_condition_returns_true(self, executor):
        """纯空白条件应返回 True"""
        assert executor.evaluate_condition("   ") is True

    def test_unknown_condition_returns_false(self, executor):
        """未知条件类型应返回 False"""
        assert executor.evaluate_condition("some_random_gibberish") is False


# =====================================================================
# parse_loop_range 测试
# =====================================================================
class TestParseLoopRange:
    """循环范围解析"""

    def test_comma_separated_list(self, executor):
        """逗号分隔列表：1,2,3"""
        result = executor.parse_loop_range("1,2,3")
        assert result == ["1", "2", "3"]

    def test_range_format(self, executor):
        """范围格式：1-5"""
        result = executor.parse_loop_range("1-5")
        assert result == [1, 2, 3, 4, 5]

    def test_variable_reference_list(self, executor):
        """变量引用：$varname（变量是列表）"""
        executor.set_variable("mylist", ["a", "b", "c"])
        result = executor.parse_loop_range("$mylist")
        assert result == ["a", "b", "c"]

    def test_variable_reference_single_value(self, executor):
        """变量引用：$varname（变量是单值）"""
        executor.set_variable("myval", "hello")
        result = executor.parse_loop_range("$myval")
        assert result == ["hello"]

    def test_table_reference(self, executor):
        """数据表引用：table:tablename"""
        result = executor.parse_loop_range("table:Login")
        assert result == ["table:Login"]

    def test_single_value(self, executor):
        """单个值"""
        result = executor.parse_loop_range("hello")
        assert result == ["hello"]
