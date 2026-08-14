"""ExploreExecutor 单元测试

测试 execute_command() API 的基本功能
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

try:
    from rodski.core.explore_executor import ExploreExecutor
    from rodski.core.exceptions import SKIError
except ImportError:
    from core.explore_executor import ExploreExecutor
    from core.exceptions import SKIError


class TestExploreExecutor:
    """ExploreExecutor 测试类"""

    @pytest.fixture
    def mock_keyword_engine(self):
        """模拟 KeywordEngine"""
        engine = Mock()
        engine.SUPPORTED = ["type", "click", "verify", "get"]
        engine.driver = Mock()
        engine.driver.screenshot = Mock()
        engine.driver.current_url = Mock(return_value="http://example.com")
        engine._context = Mock()
        engine._context.get_return = Mock(return_value=None)
        engine.execute = Mock()
        return engine

    @pytest.fixture
    def explore_executor(self, mock_keyword_engine):
        """创建 ExploreExecutor 实例"""
        module_dir = Path("/tmp/test_module")
        executor = ExploreExecutor(mock_keyword_engine, module_dir)
        executor.start_session("test_session_001")
        return executor

    def test_execute_command_success(self, explore_executor, mock_keyword_engine):
        """测试命令执行成功"""
        command = {
            "action": "type",
            "model": "LoginPage",
            "data": "AdminUser"
        }

        result = explore_executor.execute_command(command)

        assert result["success"] is True
        assert "evidence" in result
        assert result["errors"] == []

        # 验证 KeywordEngine.execute() 被调用
        mock_keyword_engine.execute.assert_called_once()
        call_args = mock_keyword_engine.execute.call_args
        assert call_args[1]["keyword"] == "type"
        assert call_args[1]["params"]["model"] == "LoginPage"

    def test_execute_command_missing_action(self, explore_executor):
        """测试命令缺少 action 字段"""
        command = {
            "model": "LoginPage",
            "data": "AdminUser"
        }

        result = explore_executor.execute_command(command)

        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "action" in result["errors"][0].lower()

    def test_execute_command_missing_model(self, explore_executor):
        """测试命令缺少 model 字段"""
        command = {
            "action": "type",
            "data": "AdminUser"
        }

        result = explore_executor.execute_command(command)

        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "model" in result["errors"][0].lower()

    def test_execute_command_unsupported_action(self, explore_executor):
        """测试不支持的 action"""
        command = {
            "action": "invalid_action",
            "model": "LoginPage"
        }

        result = explore_executor.execute_command(command)

        assert result["success"] is False
        assert len(result["errors"]) > 0

    def test_execute_command_with_data(self, explore_executor, mock_keyword_engine):
        """测试带 data 参数的命令"""
        command = {
            "action": "type",
            "model": "LoginPage",
            "data": "AdminUser"
        }

        result = explore_executor.execute_command(command)

        assert result["success"] is True
        call_args = mock_keyword_engine.execute.call_args
        assert call_args[1]["params"]["data"] == "AdminUser"

    def test_execute_command_without_data(self, explore_executor, mock_keyword_engine):
        """测试不带 data 参数的命令"""
        command = {
            "action": "click",
            "model": "LoginButton"
        }

        result = explore_executor.execute_command(command)

        assert result["success"] is True
        call_args = mock_keyword_engine.execute.call_args
        assert "data" not in call_args[1]["params"] or call_args[1]["params"]["data"] is None

    def test_evidence_collection(self, explore_executor, mock_keyword_engine):
        """测试证据采集"""
        command = {
            "action": "type",
            "model": "LoginPage"
        }

        result = explore_executor.execute_command(command)

        evidence = result["evidence"]
        assert "screenshot" in evidence
        assert "url" in evidence
        assert evidence["url"] == "http://example.com"
        assert "return_value" in evidence
        assert "browser_errors" in evidence

    def test_session_management(self, mock_keyword_engine):
        """测试会话管理"""
        module_dir = Path("/tmp/test_module")
        executor = ExploreExecutor(mock_keyword_engine, module_dir)

        executor.start_session("session_001")
        assert executor._session_id == "session_001"
        assert executor._step_counter == 0

        # 执行命令后步骤计数器递增
        command = {"action": "type", "model": "LoginPage"}
        executor.execute_command(command)
        assert executor._step_counter == 1
