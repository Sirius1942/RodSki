"""性能监控装饰器"""
import time
import logging
from functools import wraps
from typing import Callable, Optional

logger = logging.getLogger("ski.perf")

# 全局 Profiler 实例（可选）
_global_profiler: Optional['Profiler'] = None


def set_profiler(profiler):
    """设置全局 Profiler"""
    global _global_profiler
    _global_profiler = profiler


def monitor_performance(func: Callable) -> Callable:
    """监控函数执行时间"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        success = False
        try:
            result = func(*args, **kwargs)
            success = True
            elapsed = time.perf_counter() - start
            if elapsed > 1.0:  # 只记录超过1秒的操作
                logger.warning(f"{func.__name__} 耗时 {elapsed:.2f}s")
            
            # 记录到 Profiler
            if _global_profiler and len(args) > 1:
                keyword = args[1] if isinstance(args[1], str) else func.__name__
                _global_profiler.record(keyword, elapsed, success)
            
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(f"{func.__name__} 失败 (耗时 {elapsed:.2f}s): {e}")
            
            # 记录失败到 Profiler
            if _global_profiler and len(args) > 1:
                keyword = args[1] if isinstance(args[1], str) else func.__name__
                _global_profiler.record(keyword, elapsed, False)
            
            raise
    return wrapper
