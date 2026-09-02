"""v11.0.0 断言引擎单元测试"""

import pytest
from rodski.core.assertion_engine import AssertionEngine, AssertionError


class TestAssertionEngine:
    """测试断言操作符功能"""

    def test_is_operator_dict_valid(self):
        """测试识别有效的操作符字典"""
        assert AssertionEngine.is_operator_dict({"$gt": 100}) is True
        assert AssertionEngine.is_operator_dict({"$contains": "text"}) is True
        assert AssertionEngine.is_operator_dict({"$lte": 50}) is True

    def test_is_operator_dict_invalid(self):
        """测试识别无效的操作符字典"""
        assert AssertionEngine.is_operator_dict({"gt": 100}) is False  # 缺少 $
        assert AssertionEngine.is_operator_dict({"$unknown": 100}) is False  # 不支持的操作符
        assert AssertionEngine.is_operator_dict({"$gt": 100, "$lt": 200}) is False  # 多键
        assert AssertionEngine.is_operator_dict("not_a_dict") is False
        assert AssertionEngine.is_operator_dict({}) is False

    # ========== $gt 测试 ==========

    def test_gt_pass_int(self):
        """测试 $gt 通过（整数）"""
        assert AssertionEngine.evaluate(100, {"$gt": 50}) is True
        assert AssertionEngine.evaluate(1, {"$gt": 0}) is True

    def test_gt_pass_float(self):
        """测试 $gt 通过（浮点数）"""
        assert AssertionEngine.evaluate(3.14, {"$gt": 3.0}) is True
        assert AssertionEngine.evaluate(100.1, {"$gt": 100}) is True

    def test_gt_pass_string_number(self):
        """测试 $gt 通过（字符串数字）"""
        assert AssertionEngine.evaluate("100", {"$gt": 50}) is True
        assert AssertionEngine.evaluate(100, {"$gt": "50"}) is True

    def test_gt_fail(self):
        """测试 $gt 失败"""
        with pytest.raises(AssertionError, match="不大于"):
            AssertionEngine.evaluate(50, {"$gt": 100})

        with pytest.raises(AssertionError, match="不大于"):
            AssertionEngine.evaluate(100, {"$gt": 100})  # 相等也失败

    def test_gt_invalid_type(self):
        """测试 $gt 类型错误"""
        with pytest.raises(AssertionError, match="需要数值类型"):
            AssertionEngine.evaluate("not_a_number", {"$gt": 10})

    # ========== $gte 测试 ==========

    def test_gte_pass(self):
        """测试 $gte 通过"""
        assert AssertionEngine.evaluate(100, {"$gte": 100}) is True
        assert AssertionEngine.evaluate(101, {"$gte": 100}) is True

    def test_gte_fail(self):
        """测试 $gte 失败"""
        with pytest.raises(AssertionError, match="不大于等于"):
            AssertionEngine.evaluate(99, {"$gte": 100})

    # ========== $lt 测试 ==========

    def test_lt_pass(self):
        """测试 $lt 通过"""
        assert AssertionEngine.evaluate(50, {"$lt": 100}) is True
        assert AssertionEngine.evaluate(0, {"$lt": 1}) is True

    def test_lt_fail(self):
        """测试 $lt 失败"""
        with pytest.raises(AssertionError, match="不小于"):
            AssertionEngine.evaluate(100, {"$lt": 50})

        with pytest.raises(AssertionError, match="不小于"):
            AssertionEngine.evaluate(100, {"$lt": 100})  # 相等也失败

    # ========== $lte 测试 ==========

    def test_lte_pass(self):
        """测试 $lte 通过"""
        assert AssertionEngine.evaluate(100, {"$lte": 100}) is True
        assert AssertionEngine.evaluate(99, {"$lte": 100}) is True

    def test_lte_fail(self):
        """测试 $lte 失败"""
        with pytest.raises(AssertionError, match="不小于等于"):
            AssertionEngine.evaluate(101, {"$lte": 100})

    # ========== $contains 测试 ==========

    def test_contains_string_pass(self):
        """测试 $contains 字符串包含通过"""
        assert AssertionEngine.evaluate("hello world", {"$contains": "world"}) is True
        assert AssertionEngine.evaluate("test", {"$contains": "test"}) is True
        assert AssertionEngine.evaluate("品牌名称", {"$contains": "品牌"}) is True

    def test_contains_string_fail(self):
        """测试 $contains 字符串包含失败"""
        with pytest.raises(AssertionError, match="不包含"):
            AssertionEngine.evaluate("hello", {"$contains": "world"})

    def test_contains_array_pass(self):
        """测试 $contains 数组包含通过"""
        assert AssertionEngine.evaluate([1, 2, 3], {"$contains": 2}) is True
        assert AssertionEngine.evaluate(["a", "b", "c"], {"$contains": "b"}) is True

    def test_contains_array_fail(self):
        """测试 $contains 数组包含失败"""
        with pytest.raises(AssertionError, match="不包含"):
            AssertionEngine.evaluate([1, 2, 3], {"$contains": 4})

    def test_contains_invalid_type(self):
        """测试 $contains 类型错误"""
        with pytest.raises(AssertionError, match="需要字符串或数组"):
            AssertionEngine.evaluate(123, {"$contains": 1})

    def test_contains_tuple_support(self):
        """测试 $contains 支持 tuple"""
        assert AssertionEngine.evaluate((1, 2, 3), {"$contains": 2}) is True

    # ========== 边界情况测试 ==========

    def test_negative_numbers(self):
        """测试负数比较"""
        assert AssertionEngine.evaluate(-10, {"$gt": -20}) is True
        assert AssertionEngine.evaluate(-10, {"$lt": 0}) is True

    def test_zero_boundary(self):
        """测试零边界"""
        assert AssertionEngine.evaluate(0, {"$gte": 0}) is True
        assert AssertionEngine.evaluate(0, {"$lte": 0}) is True
        assert AssertionEngine.evaluate(1, {"$gt": 0}) is True

    def test_empty_string_contains(self):
        """测试空字符串包含"""
        assert AssertionEngine.evaluate("hello", {"$contains": ""}) is True

    def test_unsupported_operator(self):
        """测试不支持的操作符"""
        with pytest.raises(ValueError, match="不支持的操作符"):
            AssertionEngine.evaluate(100, {"$eq": 100})

    def test_multi_key_dict(self):
        """测试多键字典"""
        with pytest.raises(ValueError, match="单键字典"):
            AssertionEngine.evaluate(100, {"$gt": 50, "$lt": 200})

    def test_float_comparison_precision(self):
        """测试浮点数比较精度"""
        assert AssertionEngine.evaluate(0.1 + 0.2, {"$gt": 0.3}) is True  # Python 浮点精度问题
        assert AssertionEngine.evaluate(3.14159, {"$gte": 3.14}) is True
