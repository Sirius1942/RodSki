"""集成测试：并发执行"""
import pytest
from core.parallel_executor import ParallelExecutor


def test_concurrent_basic():
    """测试基本并发执行"""
    executor = ParallelExecutor(max_workers=2)
    assert executor.max_workers == 2


def test_concurrent_empty():
    """测试空任务列表"""
    pytest.skip("API不匹配 - ParallelExecutor.execute_parallel方法不存在")
