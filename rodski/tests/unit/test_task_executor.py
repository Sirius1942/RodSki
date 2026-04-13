"""TaskExecutor 单元测试

测试用例任务执行器的基本功能。
覆盖：任务调度、执行顺序、结果收集。
"""
import json
import pytest
from unittest.mock import MagicMock
from core.keyword_engine import KeywordEngine
from core.task_executor import TaskExecutor


@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=KeywordEngine)
    engine.execute.return_value = True
    return engine


@pytest.fixture
def executor(mock_engine):
    return TaskExecutor(mock_engine)


class TestTaskExecutor:
    def test_execute_steps_all_pass(self, executor, mock_engine):
        steps = [
            {"keyword": "click", "params": {"locator": "#a"}, "name": "Step 1"},
            {"keyword": "type", "params": {"locator": "#b", "text": "hi"}, "name": "Step 2"},
        ]
        result = executor.execute_steps(steps)
        assert result is True
        assert len(executor.get_results()) == 2
        assert all(r["success"] for r in executor.get_results())

    def test_execute_steps_failure_stops(self, executor, mock_engine):
        mock_engine.execute.side_effect = [True, False]
        steps = [
            {"keyword": "click", "params": {"locator": "#a"}, "name": "Step 1"},
            {"keyword": "click", "params": {"locator": "#b"}, "name": "Step 2"},
            {"keyword": "click", "params": {"locator": "#c"}, "name": "Step 3"},
        ]
        result = executor.execute_steps(steps)
        assert result is False
        assert len(executor.get_results()) == 2

    def test_continue_on_fail(self, executor, mock_engine):
        mock_engine.execute.side_effect = [True, False, True]
        steps = [
            {"keyword": "click", "params": {}, "name": "S1"},
            {"keyword": "click", "params": {}, "name": "S2", "continue_on_fail": True},
            {"keyword": "click", "params": {}, "name": "S3"},
        ]
        result = executor.execute_steps(steps)
        assert result is False
        assert len(executor.get_results()) == 3

    def test_retry_on_failure(self, mock_engine):
        mock_engine.execute.side_effect = [False, False, True]
        executor = TaskExecutor(mock_engine, max_retries=2)
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        result = executor.execute_steps(steps)
        assert result is True

    def test_retry_exhausted(self, mock_engine):
        mock_engine.execute.return_value = False
        executor = TaskExecutor(mock_engine, max_retries=1)
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        result = executor.execute_steps(steps)
        assert result is False

    def test_get_summary(self, executor, mock_engine):
        mock_engine.execute.side_effect = [True, True, False]
        steps = [
            {"keyword": "click", "params": {}, "name": "S1"},
            {"keyword": "click", "params": {}, "name": "S2"},
            {"keyword": "click", "params": {}, "name": "S3"},
        ]
        executor.execute_steps(steps)
        summary = executor.get_summary()
        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["pass_rate"] == 66.7
        assert summary["duration"] >= 0

    def test_get_summary_empty(self, executor):
        summary = executor.get_summary()
        assert summary["total"] == 0
        assert summary["pass_rate"] == 0

    def test_save_results(self, executor, mock_engine, tmp_path):
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        executor.execute_steps(steps)
        path = str(tmp_path / "results.json")
        executor.save_results(path)
        data = json.loads(open(path).read())
        assert "summary" in data
        assert "results" in data
        assert "timestamp" in data

    def test_load_case(self, executor):
        raw = [
            {"keyword": "click", "name": "Click button", "locator": "#btn"},
            {"Keyword": "type", "Name": "Type text", "locator": "#inp", "text": "hi"},
            {"keyword": None, "name": "Empty"},
        ]
        steps = executor.load_case(raw)
        assert len(steps) == 2
        assert steps[0]["keyword"] == "click"
        assert steps[0]["params"]["locator"] == "#btn"
        assert steps[1]["keyword"] == "type"

    def test_load_case_empty(self, executor):
        steps = executor.load_case([])
        assert steps == []

    def test_with_logger(self, mock_engine):
        logger = MagicMock()
        executor = TaskExecutor(mock_engine, logger=logger)
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        executor.execute_steps(steps)
        logger.info.assert_called_once()

    def test_results_reset_on_execute(self, executor, mock_engine):
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        executor.execute_steps(steps)
        assert len(executor.get_results()) == 1
        executor.execute_steps(steps)
        assert len(executor.get_results()) == 1

    def test_exception_in_execute(self, mock_engine):
        mock_engine.execute.side_effect = Exception("boom")
        executor = TaskExecutor(mock_engine, max_retries=0)
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        result = executor.execute_steps(steps)
        assert result is False
        assert "error" in executor.get_results()[0]
        assert "boom" in executor.get_results()[0]["error"]

    def test_error_recorded_in_results(self, mock_engine):
        mock_engine.execute.return_value = False
        executor = TaskExecutor(mock_engine, max_retries=0)
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        executor.execute_steps(steps)
        result = executor.get_results()[0]
        assert result["success"] is False
        assert "error" in result

    def test_no_error_on_success(self, executor, mock_engine):
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        executor.execute_steps(steps)
        result = executor.get_results()[0]
        assert result["success"] is True
        assert "error" not in result

    def test_logger_error_on_failure(self, mock_engine):
        mock_engine.execute.return_value = False
        mock_logger = MagicMock()
        executor = TaskExecutor(mock_engine, logger=mock_logger)
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        executor.execute_steps(steps)
        mock_logger.error.assert_called_once()

    def test_retry_error_includes_count(self, mock_engine):
        mock_engine.execute.return_value = False
        executor = TaskExecutor(mock_engine, max_retries=2)
        steps = [{"keyword": "click", "params": {}, "name": "S1"}]
        executor.execute_steps(steps)
        error = executor.get_results()[0]["error"]
        assert "已重试 2 次" in error
