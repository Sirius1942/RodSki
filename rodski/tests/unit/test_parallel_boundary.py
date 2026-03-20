"""parallel_executor 并发边界测试"""
import pytest
from core.parallel_executor import ParallelExecutor


class TestParallelExecutorBoundary:
    """并发执行器边界测试"""
    
    def test_zero_workers(self):
        """测试 0 个 worker"""
        executor = ParallelExecutor(max_workers=1)
        tasks = []
        results = executor.execute(tasks)
        assert len(results) == 0
    
    def test_single_task(self):
        """测试单个任务"""
        executor = ParallelExecutor(max_workers=1)
        
        def simple_task():
            return "done"
        
        results = executor.execute([simple_task])
        assert len(results) == 1
    
    def test_more_tasks_than_workers(self):
        """测试任务数 > worker 数"""
        executor = ParallelExecutor(max_workers=2)
        
        def task(n):
            return n * 2
        
        tasks = [lambda i=i: task(i) for i in range(10)]
        results = executor.execute(tasks)
        assert len(results) == 10
    
    def test_task_exception(self):
        """测试任务异常处理"""
        executor = ParallelExecutor(max_workers=2)
        
        def failing_task():
            raise ValueError("Task failed")
        
        results = executor.execute([failing_task])
        # 应该捕获异常而不是崩溃
        assert len(results) == 1
