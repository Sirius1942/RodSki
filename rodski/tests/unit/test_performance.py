"""性能监控测试"""
import time
from core.performance import monitor_performance


def test_monitor_performance():
    """测试性能监控装饰器"""
    @monitor_performance
    def fast_func():
        time.sleep(0.1)
        return True
    
    @monitor_performance
    def slow_func():
        time.sleep(1.5)
        return True
    
    assert fast_func() is True
    assert slow_func() is True


def test_monitor_with_exception():
    """测试异常情况下的性能监控"""
    @monitor_performance
    def error_func():
        raise ValueError("测试错误")
    
    try:
        error_func()
        assert False, "应该抛出异常"
    except ValueError:
        pass
