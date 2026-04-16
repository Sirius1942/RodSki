"""Observability 模块 - 轻量级 trace 和 metrics

提供执行过程的细粒度性能数据：
- Span: 执行跨度数据结构
- Tracer: 全局 trace 收集器（单例）
- MetricsCollector: 内存指标收集器（counter / histogram）
- JsonExporter: 导出 trace 和 metrics 为 JSON（兼容 OpenTelemetry）
- trace_span: 装饰器，自动创建/结束 span
"""
from .span import Span
from .tracer import Tracer, get_tracer, trace_span
from .metrics import MetricsCollector
from .exporter import JsonExporter

__all__ = [
    "Span",
    "Tracer",
    "get_tracer",
    "trace_span",
    "MetricsCollector",
    "JsonExporter",
]
