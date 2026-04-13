"""关键字引擎异常场景测试

测试 core/keyword_engine.py 中的异常处理路径。
覆盖：未知关键字 UnknownKeywordError、必需参数缺失 InvalidParameterError、
      驱动已关闭 DriverStoppedError、close 关键字执行。
"""
import pytest
from unittest.mock import MagicMock
from core.keyword_engine import KeywordEngine
from core.exceptions import (
    UnknownKeywordError,
    InvalidParameterError,
    DriverStoppedError,
    RetryExhaustedError,
)


@pytest.fixture
def mock_driver():
    """创建基础 mock driver，所有方法默认返回 True"""
    driver = MagicMock()
    driver.click.return_value = True
    driver.type_locator.return_value = True
    driver.wait.return_value = None
    driver.navigate.return_value = True
    driver.screenshot.return_value = True
    driver.clear.return_value = True
    driver.close.return_value = None
    driver.get_text_locator.return_value = "text"
    driver.upload_file.return_value = True
    driver._is_closed = False
    return driver


@pytest.fixture
def engine(mock_driver):
    return KeywordEngine(mock_driver)


# =====================================================================
# 未知关键字
# =====================================================================
class TestUnknownKeyword:
    """未知关键字应抛出 UnknownKeywordError"""

    def test_unknown_keyword_raises(self, engine):
        """完全未知的关键字名"""
        with pytest.raises(UnknownKeywordError, match="未知关键字"):
            engine.execute("nonexistent_action", {})

    def test_unknown_keyword_similar_name(self, engine):
        """拼写接近但不匹配的关键字（如 'typ' 而非 'type'）"""
        with pytest.raises(UnknownKeywordError):
            engine.execute("typ", {"locator": "#input", "text": "hello"})

    def test_click_not_standalone_keyword(self, engine):
        """click 不是独立关键字，应抛 UnknownKeywordError
        （click 操作通过 type 批量模式中的数据表字段值实现）"""
        with pytest.raises(UnknownKeywordError):
            engine.execute("click", {"locator": "#btn"})

    def test_removed_keywords_raise(self, engine):
        """已移除的关键字（open/select/hover/drag/scroll）应抛异常"""
        for kw in ["open", "select", "hover", "drag", "scroll"]:
            with pytest.raises(UnknownKeywordError):
                engine.execute(kw, {})


# =====================================================================
# 必需参数缺失
# =====================================================================
class TestMissingRequiredParams:
    """必需参数缺失时应抛出 InvalidParameterError"""

    def test_verify_requires_model_and_data(self, engine):
        """verify 需要 model 和 data 两个参数"""
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("verify", {})

    def test_verify_requires_data(self, engine):
        """verify 只有 model 没有 data 应报错"""
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("verify", {"model": "Login"})

    def test_send_requires_model_and_data(self, engine):
        """send 需要 model 和 data 两个参数"""
        with pytest.raises(InvalidParameterError, match="model/data"):
            engine.execute("send", {})

    def test_send_requires_context(self, engine):
        """send 在没有 model_parser/data_manager 时报错"""
        with pytest.raises(InvalidParameterError, match="context"):
            engine.execute("send", {"model": "API", "data": "D001"})

    def test_set_invalid_format(self, engine):
        """set 参数格式不是 key=value 时报错"""
        with pytest.raises(InvalidParameterError, match="格式应为 key=value"):
            engine.execute("set", {"value": "no_equals_sign"})

    def test_run_missing_data(self, engine):
        """run 缺少 data（脚本路径）时报错"""
        with pytest.raises(InvalidParameterError, match="代码文件路径"):
            engine.execute("run", {"model": "proj"})

    def test_db_missing_data(self, engine):
        """DB 缺少 data 参数时报错"""
        with pytest.raises(InvalidParameterError, match="缺少数据行 ID"):
            engine.execute("DB", {"model": "QuerySQL"})


# =====================================================================
# close 关键字
# =====================================================================
class TestCloseKeyword:
    """close 关键字 —— 关闭浏览器"""

    def test_close_calls_driver(self, engine, mock_driver):
        """close 应调用 driver.close()"""
        result = engine.execute("close", {})
        assert result is True
        mock_driver.close.assert_called_once()

    def test_close_stores_return(self, engine, mock_driver):
        """close 应存储 True 到 return values"""
        engine.execute("close", {})
        assert engine.get_return(-1) is True

    def test_close_case_insensitive(self, engine, mock_driver):
        """close 应不区分大小写"""
        result = engine.execute("CLOSE", {})
        assert result is True
        mock_driver.close.assert_called_once()


# =====================================================================
# 驱动状态异常
# =====================================================================
class TestDriverStateExceptions:
    """驱动状态异常时的行为"""

    def test_driver_closed_no_factory_raises(self):
        """驱动已关闭且无 factory 时操作应抛 DriverStoppedError"""
        driver = MagicMock()
        driver._is_closed = True
        engine = KeywordEngine(driver, driver_factory=None)
        with pytest.raises(DriverStoppedError):
            engine.execute("navigate", {"url": "https://test.com"})

    def test_driver_closed_with_factory_recreates(self):
        """驱动已关闭但有 factory 时应自动重建"""
        closed_driver = MagicMock()
        closed_driver._is_closed = True

        new_driver = MagicMock()
        new_driver._is_closed = False
        new_driver.navigate.return_value = True

        engine = KeywordEngine(
            closed_driver,
            driver_factory=MagicMock(return_value=new_driver),
        )
        result = engine.execute("navigate", {"url": "https://test.com"})
        assert result is True
        new_driver.navigate.assert_called_once_with("https://test.com")


# =====================================================================
# 异常不触发重试
# =====================================================================
class TestExceptionRetryBehavior:
    """某些异常类型不应触发重试"""

    def test_invalid_parameter_not_retried(self, mock_driver):
        """InvalidParameterError 不应触发重试"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={"max_retries": 3, "retry_delay": 0.01},
        )
        call_count = [0]

        def fail_with_param_error(locator):
            call_count[0] += 1
            raise InvalidParameterError(
                keyword="clear", param_name="locator", reason="无效定位器"
            )

        mock_driver.clear = fail_with_param_error
        with pytest.raises(InvalidParameterError):
            engine.execute("clear", {"locator": "#bad"})
        assert call_count[0] == 1  # 只执行一次，不重试

    def test_unknown_keyword_not_retried(self, mock_driver):
        """UnknownKeywordError 不应触发重试"""
        engine = KeywordEngine(
            mock_driver,
            retry_config={"max_retries": 3, "retry_delay": 0.01},
        )
        with pytest.raises(UnknownKeywordError):
            engine.execute("fake_keyword", {})
