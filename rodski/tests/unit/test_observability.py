"""Observability 模块单元测试

测试 observability 包中的 Span、Tracer、MetricsCollector、JsonExporter。
覆盖：span 创建和属性、tracer 嵌套 span 管理、metrics 计数器和直方图、
JSON 导出格式（兼容 OpenTelemetry）。
"""
import json
import os
import tempfile
import time
import pytest

from observability.span import Span
from observability.tracer import Tracer, get_tracer, trace_span
from observability.metrics import MetricsCollector
from observability.exporter import JsonExporter


class TestSpan:
    """Span 数据结构测试"""

    def test_span_creation(self):
        """测试 span 基本创建"""
        span = Span(
            name="test_span",
            trace_id="abc123",
            span_id="def456",
        )
        assert span.name == "test_span"
        assert span.trace_id == "abc123"
        assert span.span_id == "def456"
        assert span.parent_id is None
        assert span.status == "ok"
        assert span.end_time is None
        assert span.attributes == {}
        assert span.children == []

    def test_span_duration_completed(self):
        """测试已完成 span 的持续时间计算"""
        span = Span(
            name="test",
            trace_id="t1",
            span_id="s1",
            start_time=100.0,
            end_time=102.5,
        )
        assert span.duration == pytest.approx(2.5)

    def test_span_duration_in_progress(self):
        """测试进行中 span 的持续时间（使用当前时间）"""
        span = Span(
            name="test",
            trace_id="t1",
            span_id="s1",
            start_time=time.time() - 1.0,
        )
        assert span.duration >= 1.0

    def test_span_to_dict(self):
        """测试 span 转字典格式（兼容 OpenTelemetry）"""
        span = Span(
            name="click",
            trace_id="trace001",
            span_id="span001",
            parent_id="span000",
            start_time=1000.0,
            end_time=1001.5,
            attributes={"keyword": "click"},
            status="ok",
        )
        d = span.to_dict()
        assert d["name"] == "click"
        assert d["traceId"] == "trace001"
        assert d["spanId"] == "span001"
        assert d["parentSpanId"] == "span000"
        assert d["startTimeUnixNano"] == int(1000.0 * 1e9)
        assert d["endTimeUnixNano"] == int(1001.5 * 1e9)
        assert d["attributes"] == {"keyword": "click"}
        assert d["status"] == "ok"

    def test_span_to_dict_no_parent(self):
        """测试根 span 转字典时无 parentSpanId"""
        span = Span(name="root", trace_id="t1", span_id="s1", start_time=100.0, end_time=101.0)
        d = span.to_dict()
        assert "parentSpanId" not in d

    def test_span_to_dict_with_children(self):
        """测试带子 span 的字典转换"""
        parent = Span(name="parent", trace_id="t1", span_id="p1", start_time=100.0, end_time=102.0)
        child = Span(name="child", trace_id="t1", span_id="c1", parent_id="p1", start_time=100.5, end_time=101.5)
        parent.children.append(child)
        d = parent.to_dict()
        assert len(d["children"]) == 1
        assert d["children"][0]["name"] == "child"

    def test_generate_id_length(self):
        """测试生成的 span ID 为 16 字符十六进制"""
        span_id = Span.generate_id()
        assert len(span_id) == 16
        assert all(c in "0123456789abcdef" for c in span_id)

    def test_generate_trace_id_length(self):
        """测试生成的 trace ID 为 32 字符十六进制"""
        trace_id = Span.generate_trace_id()
        assert len(trace_id) == 32
        assert all(c in "0123456789abcdef" for c in trace_id)

    def test_generate_ids_unique(self):
        """测试生成的 ID 唯一"""
        ids = {Span.generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestTracer:
    """Tracer 单元测试"""

    @pytest.fixture(autouse=True)
    def reset_tracer(self):
        """每个测试前后重置全局 Tracer 单例"""
        Tracer._reset_instance()
        yield
        Tracer._reset_instance()

    def test_singleton(self):
        """测试 Tracer 全局单例"""
        t1 = Tracer.get_instance()
        t2 = Tracer.get_instance()
        assert t1 is t2

    def test_get_tracer_function(self):
        """测试 get_tracer() 返回全局单例"""
        t = get_tracer()
        assert t is Tracer.get_instance()

    def test_start_and_end_span(self):
        """测试基本的 span 开始和结束"""
        tracer = get_tracer()
        span = tracer.start_span("test_op")
        assert span.name == "test_op"
        assert tracer.get_current_span() is span
        assert tracer.get_root_span() is span

        tracer.end_span("ok")
        assert span.end_time is not None
        assert span.status == "ok"
        assert tracer.get_current_span() is None

    def test_nested_spans(self):
        """测试嵌套 span 自动建立父子关系"""
        tracer = get_tracer()
        parent = tracer.start_span("parent")
        child = tracer.start_span("child")

        assert child.parent_id == parent.span_id
        assert child in parent.children
        assert tracer.get_current_span() is child

        tracer.end_span("ok")  # 结束 child
        assert tracer.get_current_span() is parent

        tracer.end_span("ok")  # 结束 parent
        assert tracer.get_current_span() is None

    def test_span_attributes(self):
        """测试 span 属性传递"""
        tracer = get_tracer()
        span = tracer.start_span("op", keyword="click", locator="#btn")
        assert span.attributes == {"keyword": "click", "locator": "#btn"}
        tracer.end_span()

    def test_span_error_status(self):
        """测试 span 错误状态"""
        tracer = get_tracer()
        span = tracer.start_span("failing_op")
        tracer.end_span("error")
        assert span.status == "error"

    def test_reset(self):
        """测试 tracer 重置"""
        tracer = get_tracer()
        tracer.start_span("op1")
        tracer.end_span()

        tracer.reset()
        assert tracer.get_root_span() is None
        assert tracer.get_current_span() is None

    def test_end_span_empty_stack(self):
        """测试空栈时 end_span 不报错"""
        tracer = get_tracer()
        tracer.end_span()  # 不应抛异常

    def test_trace_id_consistency(self):
        """测试同一 trace 中所有 span 共享 trace_id"""
        tracer = get_tracer()
        parent = tracer.start_span("parent")
        child = tracer.start_span("child")
        grandchild = tracer.start_span("grandchild")

        assert parent.trace_id == child.trace_id == grandchild.trace_id

        tracer.end_span()
        tracer.end_span()
        tracer.end_span()


class TestTraceSpanDecorator:
    """trace_span 装饰器测试"""

    @pytest.fixture(autouse=True)
    def reset_tracer(self):
        Tracer._reset_instance()
        yield
        Tracer._reset_instance()

    def test_decorator_success(self):
        """测试装饰器成功执行时自动创建和结束 span"""
        @trace_span("my_operation")
        def my_func():
            return 42

        result = my_func()
        assert result == 42

        tracer = get_tracer()
        root = tracer.get_root_span()
        assert root is not None
        assert root.name == "my_operation"
        assert root.status == "ok"
        assert root.end_time is not None

    def test_decorator_exception(self):
        """测试装饰器异常时 span 记录错误"""
        @trace_span("failing_op")
        def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            failing_func()

        tracer = get_tracer()
        root = tracer.get_root_span()
        assert root.status == "error"
        assert root.attributes["error"] == "test error"
        assert root.attributes["error_type"] == "ValueError"

    def test_decorator_preserves_function_name(self):
        """测试装饰器保留原函数名"""
        @trace_span("op")
        def my_original_func():
            pass

        assert my_original_func.__name__ == "my_original_func"


class TestMetricsCollector:
    """MetricsCollector 单元测试"""

    @pytest.fixture(autouse=True)
    def reset_collector(self):
        MetricsCollector._reset_instance()
        yield
        MetricsCollector._reset_instance()

    def test_singleton(self):
        """测试 MetricsCollector 全局单例"""
        c1 = MetricsCollector.get_instance()
        c2 = MetricsCollector.get_instance()
        assert c1 is c2

    def test_increment_counter(self):
        """测试计数器递增"""
        mc = MetricsCollector()
        mc.increment("requests")
        mc.increment("requests")
        mc.increment("requests", value=3)
        assert mc.get_counter("requests") == 5

    def test_increment_with_labels(self):
        """测试带标签的计数器"""
        mc = MetricsCollector()
        mc.increment("errors", labels={"keyword": "click"})
        mc.increment("errors", labels={"keyword": "type"})
        mc.increment("errors", labels={"keyword": "click"})
        assert mc.get_counter("errors", labels={"keyword": "click"}) == 2
        assert mc.get_counter("errors", labels={"keyword": "type"}) == 1

    def test_counter_nonexistent(self):
        """测试不存在的计数器返回 0"""
        mc = MetricsCollector()
        assert mc.get_counter("nonexistent") == 0

    def test_record_histogram(self):
        """测试直方图数值记录"""
        mc = MetricsCollector()
        mc.record("duration", 0.5)
        mc.record("duration", 1.0)
        mc.record("duration", 0.3)
        values = mc.get_histogram("duration")
        assert values == [0.5, 1.0, 0.3]

    def test_record_histogram_with_labels(self):
        """测试带标签的直方图"""
        mc = MetricsCollector()
        mc.record("duration", 0.5, labels={"keyword": "click"})
        mc.record("duration", 1.2, labels={"keyword": "navigate"})
        assert mc.get_histogram("duration", labels={"keyword": "click"}) == [0.5]
        assert mc.get_histogram("duration", labels={"keyword": "navigate"}) == [1.2]

    def test_histogram_nonexistent(self):
        """测试不存在的直方图返回空列表"""
        mc = MetricsCollector()
        assert mc.get_histogram("nonexistent") == []

    def test_get_summary(self):
        """测试获取指标摘要"""
        mc = MetricsCollector()
        mc.increment("total")
        mc.record("latency", 0.1)
        mc.record("latency", 0.5)
        mc.record("latency", 0.3)

        summary = mc.get_summary()
        assert "counters" in summary
        assert "histograms" in summary
        assert summary["counters"]["total"]["_total"] == 1
        assert summary["histograms"]["latency"]["_total"]["count"] == 3
        assert summary["histograms"]["latency"]["_total"]["min"] == pytest.approx(0.1)
        assert summary["histograms"]["latency"]["_total"]["max"] == pytest.approx(0.5)

    def test_reset(self):
        """测试重置所有指标"""
        mc = MetricsCollector()
        mc.increment("counter1")
        mc.record("hist1", 1.0)
        mc.reset()
        assert mc.get_counter("counter1") == 0
        assert mc.get_histogram("hist1") == []

    def test_labels_key_ordering(self):
        """测试标签键排序一致性"""
        mc = MetricsCollector()
        mc.increment("test", labels={"b": "2", "a": "1"})
        mc.increment("test", labels={"a": "1", "b": "2"})
        assert mc.get_counter("test", labels={"a": "1", "b": "2"}) == 2


class TestJsonExporter:
    """JsonExporter 单元测试"""

    @pytest.fixture(autouse=True)
    def reset_all(self):
        Tracer._reset_instance()
        MetricsCollector._reset_instance()
        yield
        Tracer._reset_instance()
        MetricsCollector._reset_instance()

    def test_export_trace_empty(self):
        """测试没有 trace 时返回 None"""
        tracer = Tracer()
        result = JsonExporter.export_trace(tracer)
        assert result is None

    def test_export_trace_single_span(self):
        """测试导出单个 span 的 trace"""
        tracer = Tracer()
        span = tracer.start_span("root_op")
        tracer.end_span("ok")

        result = JsonExporter.export_trace(tracer)
        assert result is not None
        assert "resourceSpans" in result
        spans = result["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) == 1
        assert spans[0]["name"] == "root_op"
        assert spans[0]["status"]["code"] == 1  # ok

    def test_export_trace_nested_spans(self):
        """测试导出嵌套 span 的 trace（展平为列表）"""
        tracer = Tracer()
        tracer.start_span("parent")
        tracer.start_span("child")
        tracer.end_span("ok")
        tracer.end_span("ok")

        result = JsonExporter.export_trace(tracer)
        spans = result["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) == 2
        assert spans[0]["name"] == "parent"
        assert spans[1]["name"] == "child"
        assert spans[1]["parentSpanId"] == spans[0]["spanId"]

    def test_export_trace_error_status(self):
        """测试导出错误状态的 span"""
        tracer = Tracer()
        span = tracer.start_span("fail_op")
        span.attributes["error"] = "something went wrong"
        tracer.end_span("error")

        result = JsonExporter.export_trace(tracer)
        spans = result["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert spans[0]["status"]["code"] == 2  # error
        assert any(
            a["key"] == "error" and a["value"]["stringValue"] == "something went wrong"
            for a in spans[0]["attributes"]
        )

    def test_export_metrics(self):
        """测试导出 metrics"""
        mc = MetricsCollector()
        mc.increment("requests", value=5)
        mc.record("latency", 0.2)

        result = JsonExporter.export_metrics(mc)
        assert result["counters"]["requests"]["_total"] == 5
        assert result["histograms"]["latency"]["_total"]["count"] == 1

    def test_export_to_file(self):
        """测试导出到 JSON 文件"""
        tracer = Tracer()
        tracer.start_span("file_test")
        tracer.end_span("ok")

        mc = MetricsCollector()
        mc.increment("test_counter")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result_path = JsonExporter.export_to_file(output_path, tracer, mc)
            assert os.path.exists(result_path)

            with open(result_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "trace" in data
            assert "metrics" in data
        finally:
            os.unlink(output_path)

    def test_export_to_file_no_metrics(self):
        """测试仅有 trace 无 metrics 时的导出"""
        tracer = Tracer()
        tracer.start_span("only_trace")
        tracer.end_span("ok")

        mc = MetricsCollector()  # 空的

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            JsonExporter.export_to_file(output_path, tracer, mc)
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert "trace" in data
            assert "metrics" not in data
        finally:
            os.unlink(output_path)
