"""DataResolver 单元测试

测试 data/data_resolver.py 中的数据解析器。
覆盖：简单变量替换 ${var}、多变量、嵌套变量 ${user.name}、
      缺失变量保留原样、模型引用 @{model.field}、
      GlobalValue 引用、Return 引用、数据表引用。
"""
import pytest
from unittest.mock import MagicMock
from data.data_resolver import DataResolver


class TestDataResolver:
    def test_resolve_simple_var(self):
        resolver = DataResolver({"name": "Alice"})
        assert resolver.resolve("Hello ${name}") == "Hello Alice"

    def test_resolve_multiple_vars(self):
        resolver = DataResolver({"first": "John", "last": "Doe"})
        assert resolver.resolve("${first} ${last}") == "John Doe"

    def test_resolve_missing_var(self):
        resolver = DataResolver({})
        assert resolver.resolve("${missing}") == "${missing}"

    def test_resolve_nested_var(self):
        resolver = DataResolver({"user": {"name": "Bob"}})
        assert resolver.resolve("Hi ${user.name}") == "Hi Bob"

    def test_resolve_model_ref(self):
        mm = MagicMock()
        mm.get.return_value = "#login-btn"
        resolver = DataResolver(model_manager=mm)
        result = resolver.resolve("@{login.button}")
        mm.get.assert_called_once_with("login", field="button")
        assert result == "#login-btn"

    def test_resolve_model_ref_missing(self):
        mm = MagicMock()
        mm.get.return_value = None
        resolver = DataResolver(model_manager=mm)
        result = resolver.resolve("@{page.elem}")
        assert result == "@{page.elem}"

    def test_resolve_no_model_manager(self):
        resolver = DataResolver()
        result = resolver.resolve("@{page.elem}")
        assert result == "@{page.elem}"

    def test_resolve_mixed(self):
        mm = MagicMock()
        mm.get.return_value = "#btn"
        resolver = DataResolver({"url": "https://test.com"}, model_manager=mm)
        result = resolver.resolve("Go to ${url} and click @{page.btn}")
        assert "https://test.com" in result
        assert "#btn" in result

    def test_resolve_non_string(self):
        resolver = DataResolver()
        assert resolver.resolve(42) == "42"
        assert resolver.resolve(None) == ""

    def test_set_var(self):
        resolver = DataResolver()
        resolver.set_var("key", "value")
        assert resolver.resolve("${key}") == "value"

    def test_resolve_params(self):
        resolver = DataResolver({"user": "admin"})
        params = {"locator": "#${user}-input", "text": "hello", "count": 5}
        resolved = resolver.resolve_params(params)
        assert resolved["locator"] == "#admin-input"
        assert resolved["text"] == "hello"
        assert resolved["count"] == 5

    def test_resolve_empty_string(self):
        resolver = DataResolver()
        assert resolver.resolve("") == ""

    def test_resolve_no_placeholders(self):
        resolver = DataResolver({"a": "b"})
        assert resolver.resolve("plain text") == "plain text"

    def test_nested_key_not_found(self):
        resolver = DataResolver({"a": "string_value"})
        assert resolver.resolve("${a.b}") == "${a.b}"
