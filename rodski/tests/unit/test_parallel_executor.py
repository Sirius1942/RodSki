"""测试并发执行器"""
import pytest
from unittest.mock import Mock, MagicMock
from core.parallel_executor import ParallelExecutor


class TestParallelExecutor:
    def test_execute_cases_success(self):
        """测试并发执行成功"""
        cases = [
            {"name": "case1", "steps": [{"keyword": "clear", "params": {"locator": "#btn1"}}]},
            {"name": "case2", "steps": [{"keyword": "type", "params": {"locator": "#input", "text": "test"}}]},
        ]
        
        def driver_factory():
            driver = Mock()
            driver.clear = Mock(return_value=True)
            driver.type = Mock(return_value=True)
            driver.quit = Mock()
            return driver
        
        executor = ParallelExecutor(max_workers=2)
        results = executor.execute_cases(cases, driver_factory)
        
        assert len(results) == 2
        assert all(r["success"] for r in results)
    
    def test_execute_cases_with_failure(self):
        """测试部分用例失败"""
        cases = [
            {"name": "case1", "steps": [{"keyword": "clear", "params": {"locator": "#btn"}}]},
        ]
        
        def driver_factory():
            driver = Mock()
            driver.clear = Mock(side_effect=Exception("Clear failed"))
            driver.quit = Mock()
            return driver
        
        executor = ParallelExecutor(max_workers=1)
        results = executor.execute_cases(cases, driver_factory)
        
        assert len(results) == 1
        assert not results[0]["success"]
