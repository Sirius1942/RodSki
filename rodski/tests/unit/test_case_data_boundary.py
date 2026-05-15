"""T42-005: 内置函数边界测试 — Case XML data 属性禁止使用内置函数。

验证:
- Case data 中 ${random(...)} → 报错
- Case data 中 ${date(...)} → 报错
- Case data 中 ${GlobalValue.xxx} → 允许（正常解析）
- Case data 中 ${Return[-1]} → 允许（正常解析）
- SQLite 字段值中 ${random(...)} → 正常解析
"""
import re

import pytest

from data.data_resolver import DataResolver


class TestCaseDataBuiltinFunctionBoundary:
    """Case XML data 属性禁止内置函数"""

    def test_random_in_case_data_raises_error(self):
        """Case data 包含 ${random(...)} 应报错"""
        resolver = DataResolver()
        with pytest.raises(ValueError, match="内置函数.*random.*只能写在 data.sqlite"):
            resolver.resolve_case_data("user_${random(int, 1000, 9999)}")

    def test_date_in_case_data_raises_error(self):
        """Case data 包含 ${date(...)} 应报错"""
        resolver = DataResolver()
        with pytest.raises(ValueError, match="内置函数.*date.*只能写在 data.sqlite"):
            resolver.resolve_case_data("${date(today)}")

    def test_random_str_in_case_data_raises_error(self):
        """Case data 包含 ${random(str, 8)} 应报错"""
        resolver = DataResolver()
        with pytest.raises(ValueError, match="内置函数.*random.*只能写在 data.sqlite"):
            resolver.resolve_case_data("prefix_${random(str, 8)}_suffix")

    def test_globalvalue_in_case_data_allowed(self):
        """Case data 包含 GlobalValue 引用 → 正常解析，不报错"""
        resolver = DataResolver(global_vars={"env": {"url": "https://example.com"}})
        result = resolver.resolve_case_data("GlobalValue.env.url")
        assert result == "https://example.com"

    def test_return_ref_in_case_data_allowed(self):
        """Case data 包含 ${Return[-1]} → 正常解析，不报错"""
        resolver = DataResolver(return_provider=lambda idx: "order_123")
        result = resolver.resolve_case_data("${Return[-1]}")
        assert result == "order_123"

    def test_plain_text_in_case_data_allowed(self):
        """Case data 纯文本 → 原样返回"""
        resolver = DataResolver()
        result = resolver.resolve_case_data("hello world")
        assert result == "hello world"

    def test_named_var_in_case_data_allowed(self):
        """Case data 包含命名变量 ${varName} → 正常解析"""
        resolver = DataResolver(data_source={"username": "test_user"})
        result = resolver.resolve_case_data("${username}")
        assert result == "test_user"


class TestSqliteFieldBuiltinFunctions:
    """SQLite 字段值中内置函数正常解析（通过 resolve_with_return）"""

    def test_random_in_sqlite_field_resolves(self):
        """SQLite 字段值 ${random(int, 100, 200)} → 正常解析为数字"""
        resolver = DataResolver(return_provider=lambda idx: None)
        result = resolver.resolve_with_return("${random(int, 100, 200)}")
        val = int(result)
        assert 100 <= val <= 200

    def test_date_in_sqlite_field_resolves(self):
        """SQLite 字段值 ${date(today)} → 正常解析为日期"""
        resolver = DataResolver(return_provider=lambda idx: None)
        result = resolver.resolve_with_return("${date(today)}")
        # date(today) 返回 YYYY-MM-DD 格式
        assert re.match(r'\d{4}-\d{2}-\d{2}', result)

    def test_resolve_still_supports_functions(self):
        """原 resolve() 方法仍然支持内置函数（向后兼容）"""
        resolver = DataResolver()
        result = resolver.resolve("${random(int, 1, 9)}")
        val = int(result)
        assert 1 <= val <= 9
