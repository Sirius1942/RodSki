"""Logger 单元测试

测试 core/logger.py 中的日志模块。
覆盖：日志初始化、级别设置、文件输出、控制台输出、
      日志格式化、多实例隔离。
"""
import pytest
from core.logger import Logger


@pytest.fixture
def logger(tmp_path):
    return Logger(name="test_logger", log_dir=str(tmp_path / "logs"), console=False)


class TestLogger:
    def test_info(self, logger):
        logger.info("test info")
        content = logger.get_latest_log()
        assert "test info" in content
        assert "INFO" in content

    def test_error(self, logger):
        logger.error("test error")
        content = logger.get_latest_log()
        assert "test error" in content
        assert "ERROR" in content

    def test_debug_shown_in_file_at_default_file_level(self, logger):
        """file_level 默认 DEBUG，文件中应记录 DEBUG 消息"""
        logger.debug("hidden debug")
        content = logger.get_latest_log()
        assert "hidden debug" in content

    def test_debug_shown_at_debug_level(self, logger):
        logger.set_level("DEBUG")
        logger.debug("visible debug")
        content = logger.get_latest_log()
        assert "visible debug" in content

    def test_warning(self, logger):
        logger.warning("test warning")
        content = logger.get_latest_log()
        assert "WARNING" in content

    def test_set_level(self, logger):
        logger.set_level("ERROR")
        logger.info("should not appear")
        logger.error("should appear")
        content = logger.get_latest_log()
        assert "should not appear" not in content
        assert "should appear" in content

    def test_get_log_files(self, logger):
        logger.info("test")
        files = logger.get_log_files()
        assert len(files) >= 1

    def test_get_latest_log_empty(self, tmp_path):
        logger = Logger(name="empty", log_dir=str(tmp_path / "empty_logs"), console=False)
        logger.clear_logs()
        content = logger.get_latest_log()
        assert content == ""

    def test_clear_logs(self, logger):
        logger.info("test")
        count = logger.clear_logs()
        assert count >= 1
        assert logger.get_log_files() == []

    def test_console_logger(self, tmp_path, capsys):
        logger = Logger(name="console_test", log_dir=str(tmp_path / "clogs"), console=True)
        logger.info("console msg")
        captured = capsys.readouterr()
        assert "console msg" in captured.out
