"""指标收集 - 简单的内存指标收集器（counter / histogram）"""
import threading
from typing import Optional


class MetricsCollector:
    """内存指标收集器

    支持两种指标类型：
    - counter: 计数器（只增不减），如请求总数、错误数
    - histogram: 直方图（记录数值分布），如延迟、执行时长

    线程安全：使用 threading.Lock 保护内部状态。

    用法:
        collector = MetricsCollector()
        collector.increment("keyword.total", labels={"keyword": "click"})
        collector.record("keyword.duration", 0.35, labels={"keyword": "click"})
    """

    _instance: Optional["MetricsCollector"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._counters: dict[str, dict[str, float]] = {}
        self._histograms: dict[str, dict[str, list[float]]] = {}
        self._state_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "MetricsCollector":
        """获取或创建全局单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def _reset_instance(cls) -> None:
        """重置单例（仅用于测试）"""
        with cls._lock:
            cls._instance = None

    @staticmethod
    def _labels_key(labels: Optional[dict]) -> str:
        """将 labels 字典转为字符串 key（用于内部存储）"""
        if not labels:
            return ""
        sorted_items = sorted(labels.items())
        return ",".join(f"{k}={v}" for k, v in sorted_items)

    def increment(self, name: str, value: float = 1, labels: Optional[dict] = None) -> None:
        """递增计数器

        Args:
            name: 指标名称
            value: 递增量，默认 1
            labels: 可选标签字典
        """
        lk = self._labels_key(labels)
        with self._state_lock:
            if name not in self._counters:
                self._counters[name] = {}
            self._counters[name][lk] = self._counters[name].get(lk, 0) + value

    def record(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        """记录直方图数值

        Args:
            name: 指标名称
            value: 观测值
            labels: 可选标签字典
        """
        lk = self._labels_key(labels)
        with self._state_lock:
            if name not in self._histograms:
                self._histograms[name] = {}
            if lk not in self._histograms[name]:
                self._histograms[name][lk] = []
            self._histograms[name][lk].append(value)

    def get_counter(self, name: str, labels: Optional[dict] = None) -> float:
        """读取计数器当前值

        Args:
            name: 指标名称
            labels: 可选标签字典

        Returns:
            计数器当前值，不存在返回 0
        """
        lk = self._labels_key(labels)
        with self._state_lock:
            return self._counters.get(name, {}).get(lk, 0)

    def get_histogram(self, name: str, labels: Optional[dict] = None) -> list[float]:
        """读取直方图全部观测值

        Args:
            name: 指标名称
            labels: 可选标签字典

        Returns:
            观测值列表，不存在返回空列表
        """
        lk = self._labels_key(labels)
        with self._state_lock:
            return list(self._histograms.get(name, {}).get(lk, []))

    def get_summary(self) -> dict:
        """获取所有指标摘要

        Returns:
            包含 counters 和 histograms 摘要的字典
        """
        with self._state_lock:
            summary = {"counters": {}, "histograms": {}}

            for name, label_values in self._counters.items():
                summary["counters"][name] = {}
                for lk, val in label_values.items():
                    summary["counters"][name][lk or "_total"] = val

            for name, label_values in self._histograms.items():
                summary["histograms"][name] = {}
                for lk, values in label_values.items():
                    if not values:
                        continue
                    sorted_vals = sorted(values)
                    count = len(sorted_vals)
                    total = sum(sorted_vals)
                    summary["histograms"][name][lk or "_total"] = {
                        "count": count,
                        "sum": total,
                        "min": sorted_vals[0],
                        "max": sorted_vals[-1],
                        "avg": total / count,
                        "p50": sorted_vals[count // 2],
                        "p90": sorted_vals[int(count * 0.9)] if count >= 10 else sorted_vals[-1],
                        "p99": sorted_vals[int(count * 0.99)] if count >= 100 else sorted_vals[-1],
                    }

            return summary

    def reset(self) -> None:
        """重置所有指标"""
        with self._state_lock:
            self._counters.clear()
            self._histograms.clear()
