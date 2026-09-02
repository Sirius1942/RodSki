"""v11.0.0 路径解析单元测试"""

import pytest
from rodski.data.data_resolver import _nav_path


class TestPathResolverV11:
    """测试 v11.0.0 新增的数组访问语法"""

    def test_array_index_basic(self):
        """测试数组下标访问（已有功能）"""
        data = {"items": [1, 2, 3]}
        result = _nav_path(data, ".items[0]")
        assert result == 1

        result = _nav_path(data, ".items[2]")
        assert result == 3

    def test_array_index_negative(self):
        """测试负索引"""
        data = {"items": [1, 2, 3]}
        result = _nav_path(data, ".items[-1]")
        assert result == 3

        result = _nav_path(data, ".items[-2]")
        assert result == 2

    def test_array_first(self):
        """测试 .first() 方法"""
        data = {"items": [1, 2, 3]}
        result = _nav_path(data, ".items.first()")
        assert result == 1

    def test_array_first_empty(self):
        """测试 .first() 空数组"""
        data = {"items": []}
        result = _nav_path(data, ".items.first()")
        assert result is None

    def test_array_last(self):
        """测试 .last() 方法"""
        data = {"items": [1, 2, 3]}
        result = _nav_path(data, ".items.last()")
        assert result == 3

    def test_array_last_empty(self):
        """测试 .last() 空数组"""
        data = {"items": []}
        result = _nav_path(data, ".items.last()")
        assert result is None

    def test_array_length(self):
        """测试 .length 属性"""
        data = {"items": [1, 2, 3]}
        result = _nav_path(data, ".items.length")
        assert result == 3

    def test_array_length_empty(self):
        """测试 .length 空数组"""
        data = {"items": []}
        result = _nav_path(data, ".items.length")
        assert result == 0

    def test_nested_array_first(self):
        """测试嵌套数组 .first()"""
        data = {
            "data": {
                "items": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"}
                ]
            }
        }
        result = _nav_path(data, ".data.items.first().name")
        assert result == "Alice"

    def test_nested_array_last(self):
        """测试嵌套数组 .last()"""
        data = {
            "data": {
                "items": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"}
                ]
            }
        }
        result = _nav_path(data, ".data.items.last().id")
        assert result == 2

    def test_array_index_then_property(self):
        """测试混合：[n] 后接 .property"""
        data = {
            "orders": [
                {"items": [{"productId": "A"}]},
                {"items": [{"productId": "B"}]}
            ]
        }
        result = _nav_path(data, ".orders[0].items[0].productId")
        assert result == "A"

    def test_array_first_then_array_index(self):
        """测试混合：.first() 后接 [n]"""
        data = {
            "orders": [
                {"items": ["A", "B"]},
                {"items": ["C", "D"]}
            ]
        }
        result = _nav_path(data, ".orders.first().items[1]")
        assert result == "B"

    def test_array_index_out_of_bounds(self):
        """测试索引越界返回 None"""
        data = {"items": [1, 2, 3]}
        result = _nav_path(data, ".items[10]")
        assert result is None

    def test_non_array_first(self):
        """测试非数组使用 .first() 返回 None"""
        data = {"value": "not_an_array"}
        result = _nav_path(data, ".value.first()")
        assert result is None

    def test_non_array_length(self):
        """测试非数组使用 .length 返回 None"""
        data = {"value": "not_an_array"}
        result = _nav_path(data, ".value.length")
        assert result is None

    def test_bare_path_without_leading_dot(self):
        """测试不带前导点的路径（自动补全）"""
        data = {"data": {"items": [1, 2, 3]}}
        result = _nav_path(data, "data.items.first()")
        assert result == 1

    def test_complex_nested_path(self):
        """测试复杂嵌套路径"""
        data = {
            "response": {
                "data": {
                    "users": [
                        {"name": "Alice", "orders": [{"id": 1}, {"id": 2}]},
                        {"name": "Bob", "orders": [{"id": 3}]}
                    ]
                }
            }
        }
        result = _nav_path(data, ".response.data.users[0].orders.last().id")
        assert result == 2

    def test_tuple_support(self):
        """测试 tuple 也支持数组操作"""
        data = {"items": (1, 2, 3)}
        assert _nav_path(data, ".items.first()") == 1
        assert _nav_path(data, ".items.last()") == 3
        assert _nav_path(data, ".items.length") == 3
