"""KeywordEngine 单元测试"""
import pytest
import tempfile
import openpyxl
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock
from core.keyword_engine import KeywordEngine
from core.exceptions import (
    UnknownKeywordError, 
    InvalidParameterError,
    RetryExhaustedError,
)


def make_mock_driver():
    driver = MagicMock()
    driver.click.return_value = True
    driver.type.return_value = True
    driver.check.return_value = True
    driver.wait.return_value = None
    driver.navigate.return_value = True
    driver.screenshot.return_value = True
    driver.select.return_value = True
    driver.hover.return_value = True
    driver.drag.return_value = True
    driver.scroll.return_value = True
    driver.assert_element = MagicMock(return_value=True)
    driver.upload_file.return_value = True
    driver.clear.return_value = True
    driver.double_click.return_value = True
    driver.right_click.return_value = True
    driver.key_press.return_value = True
    driver.get_text.return_value = "sample text"
    return driver


@pytest.fixture
def mock_driver():
    return make_mock_driver()


@pytest.fixture
def engine(mock_driver):
    return KeywordEngine(mock_driver)


class TestKeywordEngine:
    def test_click(self, engine, mock_driver):
        result = engine.execute("click", {"locator": "#btn"})
        assert result is True
        mock_driver.click.assert_called_once_with("#btn")

    def test_type(self, engine, mock_driver):
        result = engine.execute("type", {"locator": "#input", "text": "hello"})
        assert result is True
        mock_driver.type.assert_called_once_with("#input", "hello")

    def test_check_routes_to_verify(self, engine, mock_driver):
        """check 关键字内部走 verify 逻辑"""
        mock_driver.check.return_value = True
        result = engine.execute("check", {"data": "#elem"})
        assert result is True

    def test_wait(self, engine, mock_driver):
        result = engine.execute("wait", {"seconds": 2})
        assert result is True
        mock_driver.wait.assert_called_once_with(2.0)

    def test_navigate(self, engine, mock_driver):
        result = engine.execute("navigate", {"url": "https://example.com"})
        assert result is True
        mock_driver.navigate.assert_called_once_with("https://example.com")

    def test_screenshot(self, engine, mock_driver):
        result = engine.execute("screenshot", {"path": "test.png"})
        assert result is True
        mock_driver.screenshot.assert_called_once_with("test.png")

    def test_select(self, engine, mock_driver):
        result = engine.execute("select", {"locator": "#sel", "value": "opt1"})
        assert result is True
        mock_driver.select.assert_called_once_with("#sel", "opt1")

    def test_hover(self, engine, mock_driver):
        result = engine.execute("hover", {"locator": "#menu"})
        assert result is True
        mock_driver.hover.assert_called_once_with("#menu")

    def test_drag(self, engine, mock_driver):
        result = engine.execute("drag", {"from": "#a", "to": "#b"})
        assert result is True
        mock_driver.drag.assert_called_once_with("#a", "#b")

    def test_scroll(self, engine, mock_driver):
        result = engine.execute("scroll", {"x": 0, "y": 500})
        assert result is True
        mock_driver.scroll.assert_called_once_with(0, 500)

    def test_assert(self, engine, mock_driver):
        result = engine.execute("assert", {"locator": "#title", "expected": "Hello"})
        assert result is True
        mock_driver.assert_element.assert_called_once_with("#title", "Hello")

    def test_unknown_keyword(self, engine):
        with pytest.raises(UnknownKeywordError, match="未知关键字"):
            engine.execute("unknown", {})

    def test_case_insensitive(self, engine, mock_driver):
        engine.execute("CLICK", {"locator": "#btn"})
        mock_driver.click.assert_called_once()

    def test_get_keywords(self, engine):
        keywords = engine.get_keywords()
        assert len(keywords) == 30
        assert "click" in keywords
        assert "verify" in keywords
        assert "check" not in keywords
        assert "get" in keywords
        assert "assert" in keywords
        assert "http_get" in keywords
        assert "get_text" in keywords
        assert "send" in keywords
        assert "set" in keywords
        assert "run" in keywords
        assert "DB" in keywords

    def test_click_failure(self, engine, mock_driver):
        from core.exceptions import DriverError, RetryExhaustedError
        mock_driver.click.return_value = False
        with pytest.raises((DriverError, RetryExhaustedError)):
            engine.execute("click", {"locator": "#missing"})

    def test_default_params(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="locator"):
            engine.execute("click", {})

    def test_wait_default_seconds(self, engine, mock_driver):
        engine.execute("wait", {})
        mock_driver.wait.assert_called_once_with(1.0)

    def test_screenshot_default_path(self, engine, mock_driver):
        engine.execute("screenshot", {})
        mock_driver.screenshot.assert_called_once_with("screenshot.png")


class TestHTTPKeywords:
    """HTTP 关键字测试 - HTTP 请求通过 RestHelper 发送，不经过 UI 驱动"""

    @pytest.fixture(autouse=True)
    def mock_rest_helper(self, monkeypatch):
        """Mock RestHelper.send_request"""
        self.mock_send = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"ok": true}'
        self.mock_send.return_value = mock_resp
        self.default_resp = mock_resp
        monkeypatch.setattr("core.keyword_engine.RestHelper.send_request", self.mock_send)

    def test_http_get(self, engine, mock_driver):
        result = engine.execute("http_get", {"url": "https://api.example.com/users"})
        assert result is True
        self.mock_send.assert_called_once_with(
            method="GET", url="https://api.example.com/users", body=None, headers=None
        )

    def test_http_get_with_headers(self, engine, mock_driver):
        headers = {"Authorization": "Bearer token123"}
        engine.execute("http_get", {"url": "https://api.example.com", "headers": headers})
        self.mock_send.assert_called_once_with(
            method="GET", url="https://api.example.com", body=None, headers=headers
        )

    def test_http_get_stores_response(self, engine, mock_driver):
        engine.execute("http_get", {"url": "https://api.example.com"})
        assert engine._last_response is self.default_resp

    def test_http_get_status_check(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = 'Not Found'
        self.mock_send.return_value = mock_resp
        result = engine.execute(
            "http_get", {"url": "https://api.example.com", "expected_status": 200}
        )
        assert result is False

    def test_http_post(self, engine, mock_driver):
        body = {"name": "test"}
        result = engine.execute(
            "http_post", {"url": "https://api.example.com/users", "body": body}
        )
        assert result is True
        self.mock_send.assert_called_once_with(
            method="POST", url="https://api.example.com/users", body=body, headers=None
        )

    def test_http_post_with_expected_status(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.text = '{}'
        self.mock_send.return_value = mock_resp
        result = engine.execute(
            "http_post",
            {"url": "https://api.example.com", "body": {}, "expected_status": 201},
        )
        assert result is True

    def test_http_put(self, engine, mock_driver):
        body = {"name": "updated"}
        result = engine.execute(
            "http_put", {"url": "https://api.example.com/users/1", "body": body}
        )
        assert result is True
        self.mock_send.assert_called_once_with(
            method="PUT", url="https://api.example.com/users/1", body=body, headers=None
        )

    def test_http_put_stores_response(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"updated": true}'
        self.mock_send.return_value = mock_resp
        result = engine.execute(
            "http_put", {"url": "https://api.example.com/users/1", "body": {}}
        )
        assert result is True
        assert engine.get_return(-1) == '{"updated": true}'

    def test_http_delete(self, engine, mock_driver):
        result = engine.execute(
            "http_delete", {"url": "https://api.example.com/users/1"}
        )
        assert result is True
        self.mock_send.assert_called_once_with(
            method="DELETE", url="https://api.example.com/users/1", body=None, headers=None
        )

    def test_http_delete_stores_response(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.text = ''
        self.mock_send.return_value = mock_resp
        result = engine.execute(
            "http_delete", {"url": "https://api.example.com/users/1", "expected_status": 204}
        )
        assert result is True
        assert engine.get_return(-1) == ''


class TestAssertionKeywords:
    """断言关键字测试"""

    def test_assert_json_success(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"user": {"name": "Alice"}}
        engine._last_response = mock_resp
        result = engine.execute(
            "assert_json", {"path": "$.user.name", "expected": "Alice"}
        )
        assert result is True

    def test_assert_json_failure(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"user": {"name": "Bob"}}
        engine._last_response = mock_resp
        result = engine.execute(
            "assert_json", {"path": "$.user.name", "expected": "Alice"}
        )
        assert result is False

    def test_assert_json_with_dict_response(self, engine, mock_driver):
        engine._last_response = {"status": "ok", "code": 0}
        result = engine.execute("assert_json", {"path": "$.status", "expected": "ok"})
        assert result is True

    def test_assert_json_no_response_raises(self, engine, mock_driver):
        with pytest.raises(RuntimeError, match="无可用的 HTTP 响应"):
            engine.execute("assert_json", {"path": "$.x", "expected": 1})

    def test_assert_status_success(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        engine._last_response = mock_resp
        result = engine.execute("assert_status", {"expected": 200})
        assert result is True

    def test_assert_status_failure(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        engine._last_response = mock_resp
        result = engine.execute("assert_status", {"expected": 200})
        assert result is False

    def test_assert_status_no_response_raises(self, engine, mock_driver):
        with pytest.raises(RuntimeError, match="无可用的 HTTP 响应"):
            engine.execute("assert_status", {"expected": 200})


class TestUIKeywords:
    """UI 交互关键字测试"""

    def test_upload_file(self, engine, mock_driver):
        result = engine.execute(
            "upload_file", {"locator": "#file-input", "file_path": "/tmp/test.pdf"}
        )
        assert result is True
        mock_driver.upload_file.assert_called_once_with("#file-input", "/tmp/test.pdf")

    def test_clear(self, engine, mock_driver):
        result = engine.execute("clear", {"locator": "#search"})
        assert result is True
        mock_driver.clear.assert_called_once_with("#search")

    def test_double_click(self, engine, mock_driver):
        result = engine.execute("double_click", {"locator": "#item"})
        assert result is True
        mock_driver.double_click.assert_called_once_with("#item")

    def test_right_click(self, engine, mock_driver):
        result = engine.execute("right_click", {"locator": "#context-menu"})
        assert result is True
        mock_driver.right_click.assert_called_once_with("#context-menu")

    def test_key_press(self, engine, mock_driver):
        result = engine.execute("key_press", {"key": "Enter"})
        assert result is True
        mock_driver.key_press.assert_called_once_with("Enter")

    def test_key_press_tab(self, engine, mock_driver):
        result = engine.execute("key_press", {"key": "Tab"})
        assert result is True
        mock_driver.key_press.assert_called_once_with("Tab")

    def test_get_text(self, engine, mock_driver):
        result = engine.execute("get_text", {"locator": "#title", "var_name": "page_title"})
        assert result is True
        mock_driver.get_text.assert_called_once_with("#title")
        assert engine._variables["page_title"] == "sample text"

    def test_get_text_stores_variable(self, engine, mock_driver):
        mock_driver.get_text.return_value = "Hello World"
        engine.execute("get_text", {"locator": "#heading", "var_name": "heading_text"})
        assert engine._variables["heading_text"] == "Hello World"

    def test_get_text_returns_false_on_none(self, engine, mock_driver):
        mock_driver.get_text.return_value = None
        result = engine.execute("get_text", {"locator": "#missing", "var_name": "v"})
        assert result is False

    def test_upload_file_failure(self, engine, mock_driver):
        from core.exceptions import DriverError, RetryExhaustedError
        mock_driver.upload_file.return_value = False
        with pytest.raises((DriverError, RetryExhaustedError)):
            engine.execute(
                "upload_file", {"locator": "#file", "file_path": "/nonexistent"}
            )


class TestDataReferenceIntegration:
    """数据引用集成测试"""

    @pytest.fixture
    def temp_data_dir(self):
        """创建临时数据目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_data_file(self, temp_data_dir):
        """创建示例数据文件"""
        excel_path = temp_data_dir / "TestData.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["id", "username", "password", "url"])
        ws.append(["T001", "testuser", "pass123", "https://example.com"])
        ws.append(["T002", "admin", "admin456", "https://admin.example.com"])
        wb.save(excel_path)
        wb.close()
        return excel_path

    @pytest.fixture
    def engine_with_data(self, temp_data_dir, sample_data_file):
        """创建带数据目录的引擎"""
        driver = make_mock_driver()
        return KeywordEngine(driver, data_dir=temp_data_dir)

    def test_resolve_data_reference_in_type(self, engine_with_data):
        """测试在type关键字中解析数据引用"""
        result = engine_with_data.execute(
            "type", {"locator": "#username", "text": "${TestData.T001.username}"}
        )
        assert result is True
        engine_with_data.driver.type.assert_called_once_with("#username", "testuser")

    def test_resolve_multiple_data_references(self, engine_with_data):
        """测试解析多个数据引用"""
        result = engine_with_data.execute(
            "navigate", {"url": "${TestData.T001.url}"}
        )
        assert result is True
        engine_with_data.driver.navigate.assert_called_once_with("https://example.com")

    def test_resolve_data_reference_in_nested_params(self, engine_with_data, monkeypatch):
        """测试嵌套参数中的数据引用"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{}'
        mock_send = MagicMock(return_value=mock_resp)
        monkeypatch.setattr("core.keyword_engine.RestHelper.send_request", mock_send)

        result = engine_with_data.execute(
            "http_post",
            {
                "url": "${TestData.T002.url}",
                "body": {"username": "${TestData.T002.username}"}
            }
        )
        assert result is True
        call_args = mock_send.call_args
        assert call_args[1]["body"]["username"] == "admin"

    def test_unresolved_data_reference(self, engine_with_data):
        """测试无法解析的数据引用"""
        result = engine_with_data.execute(
            "type", {"locator": "#field", "text": "${InvalidTable.ID.field}"}
        )
        assert result is True
        # 无法解析的引用保持原样
        engine_with_data.driver.type.assert_called_once_with(
            "#field", "${InvalidTable.ID.field}"
        )


class TestAdvancedKeywords:
    """高级关键字测试"""

    @pytest.fixture(autouse=True)
    def mock_rest_helper(self, monkeypatch):
        """Mock RestHelper.send_request for send keyword tests"""
        self.mock_send = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{}'
        self.mock_send.return_value = mock_resp
        monkeypatch.setattr("core.keyword_engine.RestHelper.send_request", self.mock_send)

    def test_send_post(self, engine, mock_driver):
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "POST", "body": {"key": "value"}}
        )
        assert result is True
        self.mock_send.assert_called_once()
        assert self.mock_send.call_args[1]["method"] == "POST"

    def test_send_get(self, engine, mock_driver):
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "GET"}
        )
        assert result is True
        self.mock_send.assert_called_once()
        assert self.mock_send.call_args[1]["method"] == "GET"

    def test_send_put(self, engine, mock_driver):
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "PUT", "body": {}}
        )
        assert result is True
        self.mock_send.assert_called_once()
        assert self.mock_send.call_args[1]["method"] == "PUT"

    def test_send_delete(self, engine, mock_driver):
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "DELETE"}
        )
        assert result is True
        self.mock_send.assert_called_once()
        assert self.mock_send.call_args[1]["method"] == "DELETE"

    def test_send_invalid_method(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="不支持的 HTTP 方法"):
            engine.execute("send", {"url": "https://api.example.com", "method": "PATCH"})

    def test_send_missing_url(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="缺少必需参数"):
            engine.execute("send", {"method": "POST"})

    def test_send_with_expected_status(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.text = '{}'
        self.mock_send.return_value = mock_resp
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "POST", "expected_status": 201}
        )
        assert result is True

    def test_set_variable(self, engine, mock_driver):
        result = engine.execute("set", {"var_name": "test_var", "value": "test_value"})
        assert result is True
        assert engine._variables["test_var"] == "test_value"

    def test_set_missing_var_name(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="缺少必需参数"):
            engine.execute("set", {"value": "test"})

    def test_set_numeric_value(self, engine, mock_driver):
        result = engine.execute("set", {"var_name": "count", "value": 42})
        assert result is True
        assert engine._variables["count"] == 42

    def test_run_case(self, engine, mock_driver):
        result = engine.execute("run", {"case_name": "LoginTest"})
        assert result is True

    def test_run_missing_case_name(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="缺少必需参数"):
            engine.execute("run", {})

    def test_db_with_sqlite(self, mock_driver, tmp_path):
        """DB 关键字: 使用 SQLite 执行查询"""
        import sqlite3
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO users VALUES (1, 'alice')")
        conn.commit()
        conn.close()

        engine = KeywordEngine(
            mock_driver,
            global_vars={'testdb': {'type': 'sqlite', 'database': db_path}}
        )
        result = engine.execute("DB", {"model": "testdb", "data": "SELECT * FROM users"})
        assert result is True
        ret = engine.get_return(-1)
        assert len(ret) == 1
        assert ret[0]['name'] == 'alice'

    def test_db_execute(self, mock_driver, tmp_path):
        """DB 关键字: 执行 INSERT"""
        import sqlite3
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE logs (msg TEXT)")
        conn.commit()
        conn.close()

        engine = KeywordEngine(
            mock_driver,
            global_vars={'testdb': {'type': 'sqlite', 'database': db_path}}
        )
        result = engine.execute("DB", {"model": "testdb", "data": "INSERT INTO logs VALUES ('hello')"})
        assert result is True
        ret = engine.get_return(-1)
        assert ret['affected_rows'] == 1

    def test_db_missing_data(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="SQL"):
            engine.execute("DB", {"model": "testdb"})

    def test_db_missing_connection(self, engine, mock_driver):
        """连接变量不存在时应报错"""
        from core.exceptions import DriverError, RetryExhaustedError
        with pytest.raises((DriverError, RetryExhaustedError)):
            engine.execute("DB", {"model": "nonexistent", "data": "SELECT 1"})

    def test_db_with_data_table(self, mock_driver, tmp_path):
        """DB 关键字: 从数据表读取 SQL"""
        import sqlite3
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE items (id INTEGER, price TEXT)")
        conn.execute("INSERT INTO items VALUES (1, '10元')")
        conn.commit()
        conn.close()

        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {
            'sql': "SELECT price FROM items WHERE id=1",
            'operation': 'query',
            'var_name': 'item_price',
        }

        engine = KeywordEngine(
            mock_driver,
            data_manager=mock_data_manager,
            global_vars={'testdb': {'type': 'sqlite', 'database': db_path}}
        )
        result = engine.execute("DB", {"model": "testdb", "data": "ItemSQL.Q001"})
        assert result is True
        assert engine._variables['item_price'][0]['price'] == '10元'


class TestRetryMechanism:
    """重试机制测试"""

    def test_retry_success_on_second_attempt(self, mock_driver):
        """测试第二次尝试成功"""
        engine = KeywordEngine(
            mock_driver, 
            retry_config={"max_retries": 2, "retry_delay": 0.01}
        )
        
        call_count = [0]
        def flaky_click(locator):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("ElementNotFound: #btn")
            return True
        
        mock_driver.click = flaky_click
        result = engine.execute("click", {"locator": "#btn"})
        
        assert result is True
        assert call_count[0] == 2
        assert engine.get_retry_stats()["click"] == [1]

    def test_retry_exhausted(self, mock_driver):
        """测试重试次数耗尽"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={"max_retries": 2, "retry_delay": 0.01}
        )
        
        def always_fail(locator):
            raise RuntimeError("ElementNotFound: #btn")
        
        mock_driver.click = always_fail
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            engine.execute("click", {"locator": "#btn"})

        assert exc_info.value.details.get("keyword") == "click"
        assert exc_info.value.attempts == 3  # 1 original + 2 retries
        assert "ElementNotFound" in str(exc_info.value.last_error)

    def test_no_retry_on_invalid_parameter(self, mock_driver):
        """测试参数错误不重试"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={"max_retries": 3, "retry_delay": 0.01}
        )
        
        call_count = [0]
        def fail_with_invalid_param(locator):
            call_count[0] += 1
            raise InvalidParameterError(
                keyword="click", 
                param_name="locator", 
                reason="测试参数错误"
            )
        
        mock_driver.click = fail_with_invalid_param
        
        with pytest.raises(InvalidParameterError):
            engine.execute("click", {"locator": "#btn"})
        
        # InvalidParameterError 不应该触发重试
        assert call_count[0] == 1

    def test_no_retry_when_disabled(self, mock_driver):
        """测试禁用重试 - max_retries=0 时仍执行一次，失败后抛出 RetryExhaustedError"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={"max_retries": 0}  # 禁用重试
        )

        call_count = [0]
        def fail_once(locator):
            call_count[0] += 1
            raise RuntimeError("ElementNotFound: #btn")

        mock_driver.click = fail_once

        with pytest.raises(RetryExhaustedError):
            engine.execute("click", {"locator": "#btn"})

        # 禁用重试时只执行一次
        assert call_count[0] == 1

    def test_retry_only_on_configured_errors(self, mock_driver):
        """测试只在配置的错误类型上重试"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={
                "max_retries": 2, 
                "retry_delay": 0.01,
                "retry_on_errors": ["Timeout"]  # 只重试 Timeout 错误
            }
        )
        
        call_count = [0]
        def fail_with_element_not_found(locator):
            call_count[0] += 1
            raise RuntimeError("ElementNotFound: #btn")
        
        mock_driver.click = fail_with_element_not_found
        
        with pytest.raises(RuntimeError):
            engine.execute("click", {"locator": "#btn"})
        
        # ElementNotFound 不在重试列表中，只执行一次
        assert call_count[0] == 1

    def test_set_retry_config(self, mock_driver):
        """测试动态设置重试配置"""
        engine = KeywordEngine(mock_driver)
        
        # 默认不重试
        assert engine._retry_config["max_retries"] == 0
        
        # 动态设置
        engine.set_retry_config({"max_retries": 3, "retry_delay": 0.5})
        assert engine._retry_config["max_retries"] == 3
        assert engine._retry_config["retry_delay"] == 0.5

    def test_retry_stats_tracking(self, mock_driver):
        """测试重试统计追踪"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={"max_retries": 3, "retry_delay": 0.01}
        )
        
        call_count = [0]
        def flaky_click(locator):
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("ElementNotFound: #btn")
            return True
        
        mock_driver.click = flaky_click
        engine.execute("click", {"locator": "#btn"})
        
        stats = engine.get_retry_stats()
        assert "click" in stats
        assert stats["click"][0] == 2  # 重试了2次才成功


class TestVerifyKeyword:
    """verify 关键字测试"""

    def test_verify_element_visible(self, engine, mock_driver):
        mock_driver.check.return_value = True
        result = engine.execute("verify", {"data": "#login-form"})
        assert result is True

    def test_verify_element_not_visible(self, engine, mock_driver):
        mock_driver.check.return_value = False
        result = engine.execute("verify", {"data": "#missing"})
        assert result is False

    def test_verify_element_text_match(self, engine, mock_driver):
        """简单模式: data=定位器, model=期望文本 (非批量，因为 model_parser 为 None)"""
        mock_driver.get_text.return_value = "欢迎来到首页"
        result = engine.execute("verify", {"data": "#title", "model": "首页"})
        assert result is True

    def test_verify_element_text_mismatch(self, engine, mock_driver):
        mock_driver.get_text.return_value = "登录页面"
        result = engine.execute("verify", {"data": "#title", "model": "首页"})
        assert result is False

    def test_verify_value_equal(self, engine, mock_driver):
        """值比较模式: data 不像定位器"""
        result = engine.execute("verify", {"data": "order-123", "model": "order-123"})
        assert result is True

    def test_verify_value_not_equal(self, engine, mock_driver):
        result = engine.execute("verify", {"data": "order-123", "model": "order-456"})
        assert result is False

    def test_verify_stores_return(self, engine, mock_driver):
        mock_driver.get_text.return_value = "实际文本"
        engine.execute("verify", {"data": "#elem", "model": "实际文本"})
        assert engine.get_return(-1) == "实际文本"

    def test_verify_missing_target(self, engine, mock_driver):
        from core.exceptions import InvalidParameterError
        with pytest.raises(InvalidParameterError, match="验证目标"):
            engine.execute("verify", {})

    def test_batch_verify_all_match(self, mock_driver):
        """批量验证: 模型+数据表, 全部匹配"""
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            'username': {'type': 'id', 'value': 'userName', 'driver_type': 'web'},
            'amount': {'type': 'id', 'value': 'orderAmount', 'driver_type': 'web'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {
            'username': 'testuser',
            'amount': '10元',
        }
        mock_driver.get_text.side_effect = lambda loc: {
            'id=userName': 'testuser',
            'id=orderAmount': '10元',
        }.get(loc, '')

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)
        result = engine.execute("verify", {"model": "Order", "data": "OrderData.V001"})
        assert result is True

    def test_batch_verify_mismatch(self, mock_driver):
        """批量验证: 某字段不匹配 → False"""
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            'amount': {'type': 'id', 'value': 'orderAmount', 'driver_type': 'web'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {'amount': '10元'}
        mock_driver.get_text.return_value = '20元'

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)
        result = engine.execute("verify", {"model": "Order", "data": "OrderData.V001"})
        assert result is False

    def test_batch_verify_stores_actual_values(self, mock_driver):
        """批量验证结果通过 store_return 保存"""
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            'status': {'type': 'id', 'value': 'status', 'driver_type': 'web'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {'status': '已完成'}
        mock_driver.get_text.return_value = '已完成'

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)
        engine.execute("verify", {"model": "Order", "data": "OrderData.V001"})
        ret = engine.get_return(-1)
        assert ret == {'status': '已完成'}


class TestReturnMechanism:
    """Return 机制测试"""

    def test_return_values_stored_by_get_text(self, engine, mock_driver):
        mock_driver.get_text.return_value = "order-001"
        engine.execute("get_text", {"locator": "#order-id"})
        assert engine.get_return(-1) == "order-001"

    def test_return_values_stored_by_verify(self, engine, mock_driver):
        mock_driver.check.return_value = True
        engine.execute("verify", {"data": "#element"})
        assert engine.get_return(-1) is True

    def test_return_multiple_steps(self, engine, mock_driver):
        mock_driver.get_text.return_value = "step1"
        engine.execute("get_text", {"locator": "#a"})
        mock_driver.get_text.return_value = "step2"
        engine.execute("get_text", {"locator": "#b"})
        mock_driver.get_text.return_value = "step3"
        engine.execute("get_text", {"locator": "#c"})
        assert engine.get_return(-1) == "step3"
        assert engine.get_return(-2) == "step2"
        assert engine.get_return(-3) == "step1"
        assert engine.get_return(0) == "step1"

    def test_data_resolver_with_return_provider(self):
        from data.data_resolver import DataResolver

        values = ["order-001", "user-42", "token-xyz"]
        def mock_provider(index):
            try:
                return values[index]
            except IndexError:
                return None

        resolver = DataResolver(return_provider=mock_provider)
        assert resolver.resolve("Return[-1]") == "token-xyz"
        assert resolver.resolve("Return[-2]") == "user-42"
        assert resolver.resolve("Return[0]") == "order-001"
        assert resolver.resolve("订单号: Return[-1]") == "订单号: token-xyz"

    def test_data_resolver_unresolved_return(self):
        from data.data_resolver import DataResolver
        resolver = DataResolver()
        assert resolver.resolve("Return[-1]") == "Return[-1]"

    def test_get_keyword_alias(self, engine, mock_driver):
        """get 是 get_text 的别名"""
        mock_driver.get_text.return_value = "hello"
        result = engine.execute("get", {"locator": "#elem"})
        assert result is True
        assert engine.get_return(-1) == "hello"

