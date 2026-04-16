"""Builtins 模块单元测试

测试 builtins 包中的注册表机制和 network_ops 函数。
覆盖：内置函数注册/查找/列表、函数调用解析、
keyword_engine 集成（优先查 builtin 再走 fun/ 逻辑）、
network_ops 在非 PlaywrightDriver 下的错误处理。
"""
import pytest
from unittest.mock import MagicMock, patch
from core.keyword_engine import KeywordEngine, _add_parsed_arg, _coerce_value


class TestBuiltinRegistry:
    """内置函数注册表测试"""

    def test_register_and_get(self):
        """测试注册和获取内置函数"""
        from builtin_ops import BUILTIN_REGISTRY, register_builtin, get_builtin

        # 注册一个测试函数
        register_builtin("_test_func", "builtin_ops.network_ops", "mock_route")
        assert "_test_func" in BUILTIN_REGISTRY

        fn = get_builtin("_test_func")
        assert fn is not None
        assert callable(fn)

        # 清理
        BUILTIN_REGISTRY.pop("_test_func", None)

    def test_get_nonexistent(self):
        """测试查找不存在的函数返回 None"""
        from builtin_ops import get_builtin
        assert get_builtin("__nonexistent_function__") is None

    def test_list_builtins(self):
        """测试列出所有已注册的函数"""
        from builtin_ops import list_builtins
        names = list_builtins()
        assert "mock_route" in names
        assert "wait_for_response" in names
        assert "clear_routes" in names

    def test_auto_registration(self):
        """测试 network_ops 函数自动注册"""
        from builtin_ops import BUILTIN_REGISTRY
        assert "mock_route" in BUILTIN_REGISTRY
        assert "wait_for_response" in BUILTIN_REGISTRY
        assert "clear_routes" in BUILTIN_REGISTRY

    def test_get_builtin_import_failure(self):
        """测试模块导入失败时返回 None"""
        from builtin_ops import BUILTIN_REGISTRY, get_builtin
        BUILTIN_REGISTRY["_bad_func"] = ("nonexistent.module.xxx", "func")
        result = get_builtin("_bad_func")
        assert result is None
        BUILTIN_REGISTRY.pop("_bad_func", None)

    def test_get_builtin_missing_func(self):
        """测试模块存在但函数不存在时返回 None"""
        from builtin_ops import BUILTIN_REGISTRY, get_builtin
        BUILTIN_REGISTRY["_bad_func2"] = ("builtin_ops.network_ops", "__nonexistent__")
        result = get_builtin("_bad_func2")
        assert result is None
        BUILTIN_REGISTRY.pop("_bad_func2", None)


class TestParseBuiltinCall:
    """解析内置函数调用表达式测试"""

    def test_simple_call_no_args(self):
        """测试无参数的函数调用解析"""
        result = KeywordEngine._parse_builtin_call("clear_routes()")
        assert result == ("clear_routes", [], {})

    def test_call_with_positional_args(self):
        """测试带位置参数的函数调用解析"""
        result = KeywordEngine._parse_builtin_call("mock_route('/api/users')")
        assert result is not None
        name, args, kwargs = result
        assert name == "mock_route"
        assert args == ["/api/users"]

    def test_call_with_keyword_args(self):
        """测试带关键字参数的函数调用解析"""
        result = KeywordEngine._parse_builtin_call("mock_route('/api', status=200, body='[]')")
        assert result is not None
        name, args, kwargs = result
        assert name == "mock_route"
        assert args == ["/api"]
        assert kwargs["status"] == 200
        assert kwargs["body"] == "[]"

    def test_not_function_call(self):
        """测试非函数调用格式返回 None"""
        assert KeywordEngine._parse_builtin_call("just_a_path.py") is None
        assert KeywordEngine._parse_builtin_call("") is None
        assert KeywordEngine._parse_builtin_call("no_parens") is None

    def test_invalid_function_name(self):
        """测试无效函数名返回 None"""
        assert KeywordEngine._parse_builtin_call("123invalid()") is None
        assert KeywordEngine._parse_builtin_call("has space()") is None

    def test_nested_quotes(self):
        """测试包含引号的参数解析"""
        result = KeywordEngine._parse_builtin_call(
            "mock_route('/api/users', body='{\"name\": \"test\"}')"
        )
        assert result is not None
        name, args, kwargs = result
        assert name == "mock_route"
        assert kwargs["body"] == '{"name": "test"}'

    def test_integer_arg(self):
        """测试整数参数自动转换"""
        result = KeywordEngine._parse_builtin_call("func(42)")
        assert result is not None
        _, args, _ = result
        assert args[0] == 42

    def test_boolean_arg(self):
        """测试布尔参数自动转换"""
        result = KeywordEngine._parse_builtin_call("func(flag=true)")
        assert result is not None
        _, _, kwargs = result
        assert kwargs["flag"] is True


class TestCoerceValue:
    """值类型转换测试"""

    def test_integer(self):
        """测试整数转换"""
        assert _coerce_value("42") == 42

    def test_float(self):
        """测试浮点数转换"""
        assert _coerce_value("3.14") == pytest.approx(3.14)

    def test_string_single_quotes(self):
        """测试单引号字符串"""
        assert _coerce_value("'hello'") == "hello"

    def test_string_double_quotes(self):
        """测试双引号字符串"""
        assert _coerce_value('"world"') == "world"

    def test_boolean_true(self):
        """测试布尔值 true"""
        assert _coerce_value("true") is True

    def test_boolean_false(self):
        """测试布尔值 false"""
        assert _coerce_value("false") is False

    def test_plain_string(self):
        """测试不带引号的普通字符串"""
        assert _coerce_value("/api/users") == "/api/users"

    def test_empty_string(self):
        """测试空字符串"""
        assert _coerce_value("") == ""


class TestAddParsedArg:
    """参数添加辅助函数测试"""

    def test_positional(self):
        """测试位置参数添加"""
        args, kwargs = [], {}
        _add_parsed_arg("42", args, kwargs)
        assert args == [42]
        assert kwargs == {}

    def test_keyword(self):
        """测试关键字参数添加"""
        args, kwargs = [], {}
        _add_parsed_arg("status=200", args, kwargs)
        assert args == []
        assert kwargs == {"status": 200}

    def test_empty_token(self):
        """测试空 token 忽略"""
        args, kwargs = [], {}
        _add_parsed_arg("", args, kwargs)
        assert args == []
        assert kwargs == {}


class TestKeywordEngineBuiltinIntegration:
    """keyword_engine 集成测试 - 内置函数调用"""

    def _make_engine(self, driver=None):
        """创建测试用的 KeywordEngine"""
        d = driver or MagicMock()
        d.click.return_value = True
        d.wait.return_value = None
        return KeywordEngine(d)

    def test_try_builtin_call_success(self):
        """测试通过 run 调用内置函数"""
        engine = self._make_engine()

        # 注册一个简单的测试函数
        from builtin_ops import BUILTIN_REGISTRY
        def fake_func(_context=None, **kwargs):
            return {"success": True}

        BUILTIN_REGISTRY["_test_run_func"] = ("builtin_ops", "_test_run_func")

        with patch("builtin_ops.get_builtin", return_value=fake_func):
            result = engine._try_builtin_call("_test_run_func()")
            assert result is True

        BUILTIN_REGISTRY.pop("_test_run_func", None)

    def test_try_builtin_not_found(self):
        """测试未注册的函数返回 None（走 fun/ 逻辑）"""
        engine = self._make_engine()
        result = engine._try_builtin_call("unknown_function()")
        assert result is None

    def test_try_builtin_not_call_format(self):
        """测试非函数调用格式返回 None"""
        engine = self._make_engine()
        result = engine._try_builtin_call("script.py")
        assert result is None

    def test_builtin_context_injection(self):
        """测试内置函数调用时注入运行时上下文"""
        mock_driver = MagicMock()
        engine = self._make_engine(mock_driver)

        received_context = {}

        def capture_context(_context=None, **kwargs):
            received_context.update(_context or {})
            return True

        with patch("builtin_ops.get_builtin", return_value=capture_context):
            engine._try_builtin_call("capture_context()")

        assert received_context.get("driver") is mock_driver

    def test_builtin_result_stored(self):
        """测试内置函数返回值写入 history"""
        engine = self._make_engine()
        expected_result = {"data": [1, 2, 3]}

        def returning_func(_context=None, **kwargs):
            return expected_result

        with patch("builtin_ops.get_builtin", return_value=returning_func):
            engine._try_builtin_call("returning_func()")

        assert engine.get_return(-1) == expected_result

    def test_builtin_exception_propagates(self):
        """测试内置函数异常正确传播"""
        engine = self._make_engine()

        def failing_func(_context=None, **kwargs):
            raise RuntimeError("mock error")

        with patch("builtin_ops.get_builtin", return_value=failing_func):
            with pytest.raises(RuntimeError, match="mock error"):
                engine._try_builtin_call("failing_func()")


class TestNetworkOpsValidation:
    """network_ops 参数验证测试"""

    def test_mock_route_no_context(self):
        """测试 mock_route 无上下文时报错"""
        from builtin_ops.network_ops import mock_route
        with pytest.raises(RuntimeError, match="运行时上下文"):
            mock_route("/api/users")

    def test_mock_route_no_driver(self):
        """测试 mock_route 上下文无 driver 时报错"""
        from builtin_ops.network_ops import mock_route
        with pytest.raises(RuntimeError, match="未找到 driver"):
            mock_route("/api/users", _context={})

    def test_mock_route_non_playwright(self):
        """测试 mock_route 非 PlaywrightDriver 时报错"""
        from builtin_ops.network_ops import mock_route

        class DesktopDriver:
            pass

        mock_driver = DesktopDriver()

        with pytest.raises(RuntimeError, match="仅支持 PlaywrightDriver"):
            mock_route("/api/users", _context={"driver": mock_driver})

    def test_wait_for_response_no_context(self):
        """测试 wait_for_response 无上下文时报错"""
        from builtin_ops.network_ops import wait_for_response
        with pytest.raises(RuntimeError, match="运行时上下文"):
            wait_for_response("/api/users")

    def test_clear_routes_no_context(self):
        """测试 clear_routes 无上下文时报错"""
        from builtin_ops.network_ops import clear_routes
        with pytest.raises(RuntimeError, match="运行时上下文"):
            clear_routes()

    def test_mock_route_with_playwright(self):
        """测试 mock_route 在 PlaywrightDriver 下正常工作"""
        from builtin_ops.network_ops import mock_route

        mock_page = MagicMock()
        mock_driver = self._make_playwright_mock(mock_page)

        result = mock_route(
            "/api/users",
            status=200,
            body='[]',
            _context={"driver": mock_driver},
        )
        assert result["success"] is True
        assert result["pattern"] == "/api/users"
        mock_page.route.assert_called_once()

    def test_mock_route_regex_pattern(self):
        """测试 mock_route 正则表达式模式"""
        from builtin_ops.network_ops import mock_route

        mock_page = MagicMock()
        mock_driver = self._make_playwright_mock(mock_page)

        result = mock_route(
            "re:.*\\/api\\/.*",
            status=404,
            _context={"driver": mock_driver},
        )
        assert result["success"] is True
        mock_page.route.assert_called_once()

    def test_clear_routes_with_unroute_all(self):
        """测试 clear_routes 在支持 unroute_all 的 Playwright 下工作"""
        from builtin_ops.network_ops import clear_routes

        mock_page = MagicMock()
        mock_page.unroute_all = MagicMock()
        mock_driver = self._make_playwright_mock(mock_page)

        result = clear_routes(_context={"driver": mock_driver})
        assert result is True
        mock_page.unroute_all.assert_called_once()

    def test_clear_routes_without_unroute_all(self):
        """测试 clear_routes 在不支持 unroute_all 的 Playwright 下降级"""
        from builtin_ops.network_ops import clear_routes

        mock_page = MagicMock(spec=[])  # 没有 unroute_all 属性
        mock_driver = self._make_playwright_mock(mock_page)

        result = clear_routes(_context={"driver": mock_driver})
        assert result is False

    @staticmethod
    def _make_playwright_mock(mock_page=None):
        """创建一个 type().__name__ == 'PlaywrightDriver' 的 mock driver"""
        PlaywrightDriver = type("PlaywrightDriver", (), {})
        driver = PlaywrightDriver()
        driver.page = mock_page or MagicMock()
        return driver
