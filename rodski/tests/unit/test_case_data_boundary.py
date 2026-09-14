"""内置函数边界测试 — 哪些能写在 Case XML data 属性里。

分两类：
- **数据生成类**（random / date / timestamp*）每次求值都不同 → 写在 Case XML
  会让用例不可复现（loop 每轮重新解析、重跑重新解析），**报错**。
- **纯函数类**（encodeURI / decodeURI / toUpperCase / ...）同输入同输出 → 用例
  层必须能用，`set` 的分步表达式就靠它，**允许**。

验证:
- Case data 中 ${random(...)} / ${date(...)} → 报错
- Case data 中 ${encodeURI(...)} 等纯函数 → 允许
- Case data 中 ${GlobalValue.xxx} / ${Return[-1]} / ${命名变量} → 允许
- SQLite 字段值中 ${random(...)} → 正常解析（数据行本就是"执行时现取"）
"""
import re

import pytest

from data.data_resolver import DataResolver


class TestCaseDataBuiltinFunctionBoundary:
    """Case XML data 属性：数据生成类内置函数禁止，纯函数类允许"""

    @pytest.mark.parametrize("text,func", [
        ("user_${random(int, 1000, 9999)}", "random"),
        ("${date(today)}", "date"),
        ("prefix_${random(str, 8)}_suffix", "random"),
        ("unique=${timestamp36()}", "timestamp36"),
        ("t=${timestamp()}", "timestamp"),
    ])
    def test_nondeterministic_function_in_case_data_raises_error(self, text, func):
        """数据生成类内置函数写在 Case data → 报错（用例会不可复现）"""
        resolver = DataResolver()
        with pytest.raises(ValueError, match=rf"内置函数.*{func}.*只能写在 data.sqlite"):
            resolver.resolve_case_data(text)

    @pytest.mark.parametrize("text,expected", [
        ("${encodeURI(hello world)}", "hello%20world"),
        ("${toUpperCase(abc)}", "ABC"),
        ("${toString36(1234567890)}", "KF12OI"),
        ("${decodeURI(hello%20world)}", "hello world"),
    ])
    def test_pure_function_in_case_data_allowed(self, text, expected):
        """纯函数类内置函数写在 Case data → 允许（v11.0.0 §4.4.4 的 set 写法）"""
        resolver = DataResolver()
        assert resolver.resolve_case_data(text) == expected

    def test_escaped_function_is_not_rejected(self):
        """`$${random(1)}` 是要发给被测系统的字面量，不是调用 → 不报错"""
        resolver = DataResolver()
        assert resolver.resolve_case_data("$${random(int, 1, 9)}") == "${random(int, 1, 9)}"

    def test_unregistered_function_name_is_not_rejected(self):
        """未注册的名字是普通文本，不是越界调用 → 不报错（保持既有行为）"""
        resolver = DataResolver()
        assert resolver.resolve_case_data("${randomm(int, 1, 9)}") == "${randomm(int, 1, 9)}"

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
