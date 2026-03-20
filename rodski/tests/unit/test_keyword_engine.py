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
    # assert_element conflicts with MagicMock's assert_ pattern
    driver.assert_element = MagicMock(return_value=True)
    # New UI keywords
    driver.upload_file.return_value = True
    driver.clear.return_value = True
    driver.double_click.return_value = True
    driver.right_click.return_value = True
    driver.key_press.return_value = True
    driver.get_text.return_value = "sample text"
    # New HTTP keywords
    driver.http_get.return_value = True
    driver.http_post.return_value = True
    driver.http_put.return_value = True
    driver.http_delete.return_value = True
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

    def test_check(self, engine, mock_driver):
        result = engine.execute("check", {"locator": "#elem"})
        assert result is True
        mock_driver.check.assert_called_once_with("#elem")

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
        assert len(keywords) == 29
        assert "click" in keywords
        assert "assert" in keywords
        assert "http_get" in keywords
        assert "get_text" in keywords
        assert "send" in keywords
        assert "set" in keywords
        assert "run" in keywords
        assert "DB" in keywords

    def test_click_failure(self, engine, mock_driver):
        from core.exceptions import DriverError
        mock_driver.click.return_value = False
        with pytest.raises(DriverError, match="点击失败"):
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
    """HTTP 关键字测试"""

    def test_http_get(self, engine, mock_driver):
        result = engine.execute("http_get", {"url": "https://api.example.com/users"})
        assert result is True
        mock_driver.http_get.assert_called_once_with(
            "https://api.example.com/users", headers=None
        )

    def test_http_get_with_headers(self, engine, mock_driver):
        headers = {"Authorization": "Bearer token123"}
        engine.execute("http_get", {"url": "https://api.example.com", "headers": headers})
        mock_driver.http_get.assert_called_once_with(
            "https://api.example.com", headers=headers
        )

    def test_http_get_stores_response(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_driver.http_get.return_value = mock_resp
        engine.execute("http_get", {"url": "https://api.example.com"})
        assert engine._last_response is mock_resp

    def test_http_get_status_check(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_driver.http_get.return_value = mock_resp
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
        mock_driver.http_post.assert_called_once_with(
            "https://api.example.com/users", body=body, headers=None
        )

    def test_http_post_with_expected_status(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_driver.http_post.return_value = mock_resp
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
        mock_driver.http_put.assert_called_once_with(
            "https://api.example.com/users/1", body=body, headers=None
        )

    def test_http_put_stores_response(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"updated": true}'
        mock_driver.http_put.return_value = mock_resp
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
        mock_driver.http_delete.assert_called_once_with(
            "https://api.example.com/users/1", headers=None
        )

    def test_http_delete_stores_response(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.text = ''
        mock_driver.http_delete.return_value = mock_resp
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
        from core.exceptions import DriverError
        mock_driver.upload_file.return_value = False
        with pytest.raises(DriverError, match="上传失败"):
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

    def test_resolve_data_reference_in_nested_params(self, engine_with_data):
        """测试嵌套参数中的数据引用"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        engine_with_data.driver.http_post.return_value = mock_resp

        result = engine_with_data.execute(
            "http_post",
            {
                "url": "${TestData.T002.url}",
                "body": {"username": "${TestData.T002.username}"}
            }
        )
        assert result is True
        call_args = engine_with_data.driver.http_post.call_args
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

    def test_send_post(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_driver.http_post.return_value = mock_resp
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "POST", "body": {"key": "value"}}
        )
        assert result is True
        mock_driver.http_post.assert_called_once()

    def test_send_get(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_driver.http_get.return_value = mock_resp
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "GET"}
        )
        assert result is True
        mock_driver.http_get.assert_called_once()

    def test_send_put(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_driver.http_put.return_value = mock_resp
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "PUT", "body": {}}
        )
        assert result is True
        mock_driver.http_put.assert_called_once()

    def test_send_delete(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_driver.http_delete.return_value = mock_resp
        result = engine.execute(
            "send", {"url": "https://api.example.com", "method": "DELETE"}
        )
        assert result is True
        mock_driver.http_delete.assert_called_once()

    def test_send_invalid_method(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="不支持的 HTTP 方法"):
            engine.execute("send", {"url": "https://api.example.com", "method": "PATCH"})

    def test_send_missing_url(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="缺少必需参数"):
            engine.execute("send", {"method": "POST"})

    def test_send_with_expected_status(self, engine, mock_driver):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_driver.http_post.return_value = mock_resp
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

    def test_db_query(self, engine, mock_driver):
        result = engine.execute(
            "DB", {"operation": "query", "query": "SELECT * FROM users", "var_name": "users"}
        )
        assert result is True
        assert "users" in engine._variables

    def test_db_insert(self, engine, mock_driver):
        result = engine.execute(
            "DB", {"operation": "insert", "query": "INSERT INTO users VALUES (1, 'test')"}
        )
        assert result is True

    def test_db_missing_query(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="缺少必需参数"):
            engine.execute("DB", {"operation": "query"})


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

