"""KeywordEngine 单元测试"""
import pytest
from unittest.mock import MagicMock
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
    def test_click_not_standalone(self, engine):
        """click 不再是独立关键字，需通过数据表字段值使用"""
        with pytest.raises(UnknownKeywordError):
            engine.execute("click", {"locator": "#btn"})

    def test_type(self, engine, mock_driver):
        result = engine.execute("type", {"locator": "#input", "text": "hello"})
        assert result is True
        mock_driver.type.assert_called_once_with("#input", "hello")

    def test_check_still_works_as_alias(self, mock_driver):
        """check 走 verify 批量模式"""
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            'status': {'type': 'id', 'value': 'status', 'driver_type': 'web'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {'status': 'OK'}
        mock_driver.get_text.return_value = 'OK'
        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)
        result = engine.execute("check", {"model": "Page", "data": "E001"})
        assert result is True
        mock_data_manager.get_data.assert_called_once_with("Page_verify", "E001")

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

    def test_assert(self, engine, mock_driver):
        result = engine.execute("assert", {"locator": "#title", "expected": "Hello"})
        assert result is True
        mock_driver.assert_element.assert_called_once_with("#title", "Hello")

    def test_unknown_keyword(self, engine):
        with pytest.raises(UnknownKeywordError, match="未知关键字"):
            engine.execute("unknown", {})

    def test_case_insensitive(self, engine, mock_driver):
        engine.execute("WAIT", {"seconds": "2"})
        mock_driver.wait.assert_called_once_with(2.0)

    def test_get_keywords(self, engine):
        keywords = engine.get_keywords()
        assert len(keywords) == 14
        assert "click" not in keywords
        assert "verify" in keywords
        assert "open" not in keywords
        assert "select" not in keywords
        assert "hover" not in keywords
        assert "drag" not in keywords
        assert "scroll" not in keywords
        assert "double_click" not in keywords
        assert "right_click" not in keywords
        assert "key_press" not in keywords
        assert "check" not in keywords
        assert "run" in keywords
        assert "get" in keywords
        assert "assert" in keywords
        assert "get_text" in keywords
        assert "set" in keywords
        assert "DB" in keywords
        assert "send" in keywords
        assert "http_get" not in keywords
        assert "assert_json" not in keywords
        assert "assert_status" not in keywords

    def test_wait_default_seconds(self, engine, mock_driver):
        engine.execute("wait", {})
        mock_driver.wait.assert_called_once_with(1.0)

    def test_screenshot_default_path(self, engine, mock_driver):
        engine.execute("screenshot", {})
        mock_driver.screenshot.assert_called_once_with("screenshot.png")


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


class TestAdvancedKeywords:
    """高级关键字测试"""

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
        def flaky_clear(locator):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("ElementNotFound: #input")
            return True
        
        mock_driver.clear = flaky_clear
        result = engine.execute("clear", {"locator": "#input"})
        
        assert result is True
        assert call_count[0] == 2
        assert engine.get_retry_stats()["clear"] == [1]

    def test_retry_exhausted(self, mock_driver):
        """测试重试次数耗尽"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={"max_retries": 2, "retry_delay": 0.01}
        )
        
        def always_fail(locator):
            raise RuntimeError("ElementNotFound: #input")
        
        mock_driver.clear = always_fail
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            engine.execute("clear", {"locator": "#input"})

        assert exc_info.value.details.get("keyword") == "clear"
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
                keyword="clear", 
                param_name="locator", 
                reason="测试参数错误"
            )
        
        mock_driver.clear = fail_with_invalid_param
        
        with pytest.raises(InvalidParameterError):
            engine.execute("clear", {"locator": "#input"})
        
        # InvalidParameterError 不应该触发重试
        assert call_count[0] == 1

    def test_no_retry_when_disabled(self, mock_driver):
        """测试禁用重试 - max_retries=0 时仍执行一次，失败后抛出 RetryExhaustedError"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={"max_retries": 0}
        )

        call_count = [0]
        def fail_once(locator):
            call_count[0] += 1
            raise RuntimeError("ElementNotFound: #input")

        mock_driver.clear = fail_once

        with pytest.raises(RetryExhaustedError):
            engine.execute("clear", {"locator": "#input"})

        assert call_count[0] == 1

    def test_retry_only_on_configured_errors(self, mock_driver):
        """测试只在配置的错误类型上重试"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={
                "max_retries": 2, 
                "retry_delay": 0.01,
                "retry_on_errors": ["Timeout"]
            }
        )
        
        call_count = [0]
        def fail_with_element_not_found(locator):
            call_count[0] += 1
            raise RuntimeError("ElementNotFound: #input")
        
        mock_driver.clear = fail_with_element_not_found
        
        with pytest.raises(RuntimeError):
            engine.execute("clear", {"locator": "#input"})
        
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
        def flaky_clear(locator):
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("ElementNotFound: #input")
            return True
        
        mock_driver.clear = flaky_clear
        engine.execute("clear", {"locator": "#input"})
        
        stats = engine.get_retry_stats()
        assert "clear" in stats
        assert stats["clear"][0] == 2


class TestRunKeyword:
    """run 关键字测试 — 沙箱执行 Python 代码"""

    def test_run_success(self, mock_driver, tmp_path):
        """成功执行 Python 脚本并捕获返回值"""
        case_dir = tmp_path / "case"
        fun_dir = tmp_path / "fun" / "my_project"
        case_dir.mkdir(parents=True)
        fun_dir.mkdir(parents=True)

        script = fun_dir / "hello.py"
        script.write_text('print("hello world")', encoding="utf-8")

        case_file = case_dir / "test.xlsx"
        case_file.touch()

        engine = KeywordEngine(mock_driver, case_file=str(case_file))
        result = engine.execute("run", {"model": "my_project", "data": "hello.py"})
        assert result is True
        assert engine.get_return(-1) == "hello world"

    def test_run_json_output(self, mock_driver, tmp_path):
        """脚本输出 JSON 时自动解析为结构化数据"""
        case_dir = tmp_path / "case"
        fun_dir = tmp_path / "fun" / "calc"
        case_dir.mkdir(parents=True)
        fun_dir.mkdir(parents=True)

        script = fun_dir / "compute.py"
        script.write_text('import json; print(json.dumps({"total": 42}))', encoding="utf-8")

        case_file = case_dir / "test.xlsx"
        case_file.touch()

        engine = KeywordEngine(mock_driver, case_file=str(case_file))
        engine.execute("run", {"model": "calc", "data": "compute.py"})
        assert engine.get_return(-1) == {"total": 42}

    def test_run_script_not_found(self, mock_driver, tmp_path):
        """代码文件不存在时报参数错误"""
        case_dir = tmp_path / "case"
        fun_dir = tmp_path / "fun" / "proj"
        case_dir.mkdir(parents=True)
        fun_dir.mkdir(parents=True)

        case_file = case_dir / "test.xlsx"
        case_file.touch()

        engine = KeywordEngine(mock_driver, case_file=str(case_file))
        with pytest.raises(InvalidParameterError, match="不存在"):
            engine.execute("run", {"model": "proj", "data": "missing.py"})

    def test_run_script_error(self, mock_driver, tmp_path):
        """脚本执行出错时抛出异常"""
        from core.exceptions import DriverError, RetryExhaustedError
        case_dir = tmp_path / "case"
        fun_dir = tmp_path / "fun" / "err"
        case_dir.mkdir(parents=True)
        fun_dir.mkdir(parents=True)

        script = fun_dir / "bad.py"
        script.write_text('raise ValueError("boom")', encoding="utf-8")

        case_file = case_dir / "test.xlsx"
        case_file.touch()

        engine = KeywordEngine(mock_driver, case_file=str(case_file))
        with pytest.raises((DriverError, RetryExhaustedError)):
            engine.execute("run", {"model": "err", "data": "bad.py"})

    def test_run_missing_data(self, mock_driver):
        """缺少 data 参数时报错"""
        engine = KeywordEngine(mock_driver)
        with pytest.raises(InvalidParameterError, match="代码文件路径"):
            engine.execute("run", {"model": "proj"})


class TestSendKeyword:
    """send 关键字测试 — 接口测试批量模式"""

    def test_send_requires_model_and_data(self, engine, mock_driver):
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("send", {})
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("send", {"data": "D001"})
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("send", {"model": "LoginAPI"})

    def test_send_requires_context(self, engine, mock_driver):
        """没有 model_parser 和 data_manager 时报错"""
        with pytest.raises(InvalidParameterError, match="context"):
            engine.execute("send", {"model": "LoginAPI", "data": "D001"})

    def test_send_post_success(self, mock_driver):
        """POST 请求：从模型和数据表组装请求并发送"""
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            '_method': {'type': 'static', 'value': 'POST', 'driver_type': 'interface'},
            '_url': {'type': 'static', 'value': 'http://api.example.com/login', 'driver_type': 'interface'},
            'username': {'type': 'field', 'value': 'username', 'driver_type': 'interface'},
            'password': {'type': 'field', 'value': 'password', 'driver_type': 'interface'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {
            'username': 'admin',
            'password': 'admin123',
        }

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)

        import unittest.mock as um
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "abc123", "role": "admin"}

        with um.patch('api.rest_helper.RestHelper.send_request', return_value=mock_response) as mock_send:
            result = engine.execute("send", {"model": "LoginAPI", "data": "D001"})
            assert result is True
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args
            assert call_kwargs[1]['method'] == 'POST'
            assert call_kwargs[1]['url'] == 'http://api.example.com/login'
            assert call_kwargs[1]['body'] == {'username': 'admin', 'password': 'admin123'}

        ret = engine.get_return(-1)
        assert ret['status'] == 200
        assert ret['token'] == 'abc123'
        mock_data_manager.get_data.assert_called_once_with("LoginAPI", "D001")

    def test_send_get_success(self, mock_driver):
        """GET 请求：参数拼接到 URL"""
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            '_method': {'type': 'static', 'value': 'GET', 'driver_type': 'interface'},
            '_url': {'type': 'static', 'value': 'http://api.example.com/users', 'driver_type': 'interface'},
            'page': {'type': 'field', 'value': 'page', 'driver_type': 'interface'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {
            'page': '1',
        }

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)

        import unittest.mock as um
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"users": []}

        with um.patch('api.rest_helper.RestHelper.send_request', return_value=mock_response) as mock_send:
            result = engine.execute("send", {"model": "UserAPI", "data": "D001"})
            assert result is True
            call_kwargs = mock_send.call_args
            assert call_kwargs[1]['method'] == 'GET'
            assert 'page=1' in call_kwargs[1]['url']

    def test_send_model_not_found(self, mock_driver):
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = None
        mock_data_manager = MagicMock()

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)
        with pytest.raises(InvalidParameterError, match="模型不存在"):
            engine.execute("send", {"model": "Missing", "data": "D001"})

    def test_send_missing_url(self, mock_driver):
        """模型中没有 _url 定义时报错"""
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            '_method': {'type': 'static', 'value': 'POST', 'driver_type': 'interface'},
            'username': {'type': 'field', 'value': 'username', 'driver_type': 'interface'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {'username': 'admin'}

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)
        with pytest.raises(InvalidParameterError, match="_url"):
            engine.execute("send", {"model": "LoginAPI", "data": "D001"})

    def test_send_stores_response(self, mock_driver):
        """send 的返回值包含 status 和响应体字段，verify 可直接使用"""
        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            '_method': {'type': 'static', 'value': 'POST', 'driver_type': 'interface'},
            '_url': {'type': 'static', 'value': 'http://api.example.com/login', 'driver_type': 'interface'},
            'username': {'type': 'field', 'value': 'username', 'driver_type': 'interface'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {'username': 'admin'}

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)

        import unittest.mock as um
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 42, "username": "admin"}

        with um.patch('api.rest_helper.RestHelper.send_request', return_value=mock_response):
            engine.execute("send", {"model": "LoginAPI", "data": "D001"})

        ret = engine.get_return(-1)
        assert ret['status'] == 201
        assert ret['id'] == 42
        assert ret['username'] == 'admin'


class TestVerifyKeyword:
    """verify 关键字测试 — 只支持批量模式 (model + data)"""

    def test_verify_requires_model_and_data(self, engine, mock_driver):
        from core.exceptions import InvalidParameterError
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("verify", {})
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("verify", {"data": "#login-form"})
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("verify", {"model": "Login"})

    def test_batch_verify_all_match(self, mock_driver):
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
        result = engine.execute("verify", {"model": "Order", "data": "V001"})
        assert result is True
        mock_data_manager.get_data.assert_called_once_with("Order_verify", "V001")

    def test_batch_verify_mismatch(self, mock_driver):
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
        result = engine.execute("verify", {"model": "Order", "data": "V001"})
        assert result is False
        mock_data_manager.get_data.assert_called_once_with("Order_verify", "V001")

    def test_batch_verify_stores_actual_values(self, mock_driver):
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
        engine.execute("verify", {"model": "Order", "data": "V001"})
        assert engine.get_return(-1) == {'status': '已完成'}
        mock_data_manager.get_data.assert_called_once_with("Order_verify", "V001")

    def test_batch_verify_with_return_in_data_table(self, mock_driver):
        """数据表字段中使用 Return[-1]"""
        from data.data_resolver import DataResolver

        mock_model_parser = MagicMock()
        mock_model_parser.get_model.return_value = {
            'orderNo': {'type': 'id', 'value': 'order-id', 'driver_type': 'web'},
        }
        mock_data_manager = MagicMock()
        mock_data_manager.get_data.return_value = {'orderNo': 'Return[-1]'}
        mock_driver.get_text.return_value = 'ORD-999'

        engine = KeywordEngine(mock_driver,
                               model_parser=mock_model_parser,
                               data_manager=mock_data_manager)
        engine.store_return('ORD-999')
        resolver = DataResolver(return_provider=engine.get_return)
        engine.data_resolver = resolver

        result = engine.execute("verify", {"model": "Order", "data": "E001"})
        assert result is True
        mock_data_manager.get_data.assert_called_once_with("Order_verify", "E001")


class TestReturnMechanism:
    """Return 机制测试"""

    def test_return_values_stored_by_get_text(self, engine, mock_driver):
        mock_driver.get_text.return_value = "order-001"
        engine.execute("get_text", {"locator": "#order-id"})
        assert engine.get_return(-1) == "order-001"

    def test_return_values_stored_by_assert(self, engine, mock_driver):
        engine.execute("assert", {"data": "#element", "expected": "text"})
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

    def test_data_resolver_resolve_with_return(self):
        """resolve_with_return 解析数据表字段中的 Return 引用"""
        from data.data_resolver import DataResolver

        values = ["order-001", "user-42", "token-xyz"]
        def mock_provider(index):
            try:
                return values[index]
            except IndexError:
                return None

        resolver = DataResolver(return_provider=mock_provider)
        assert resolver.resolve_with_return("Return[-1]") == "token-xyz"
        assert resolver.resolve_with_return("Return[-2]") == "user-42"
        assert resolver.resolve_with_return("Return[0]") == "order-001"
        assert resolver.resolve_with_return("订单号: Return[-1]") == "订单号: token-xyz"

    def test_data_resolver_resolve_does_not_touch_return(self):
        """resolve (Case Sheet 层) 不解析 Return"""
        from data.data_resolver import DataResolver
        values = ["some-value"]
        resolver = DataResolver(return_provider=lambda i: values[i])
        assert resolver.resolve("Return[-1]") == "Return[-1]"

    def test_get_keyword_alias(self, engine, mock_driver):
        """get 是 get_text 的别名"""
        mock_driver.get_text.return_value = "hello"
        result = engine.execute("get", {"locator": "#elem"})
        assert result is True
        assert engine.get_return(-1) == "hello"

