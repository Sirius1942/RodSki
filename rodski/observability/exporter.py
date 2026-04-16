"""导出器 - 将 trace 和 metrics 导出为 JSON（兼容 OpenTelemetry span 格式）"""
import json
import logging
from pathlib import Path
from typing import Optional

from .span import Span
from .tracer import Tracer, get_tracer
from .metrics import MetricsCollector

logger = logging.getLogger("rodski.trace")


class JsonExporter:
    """JSON 导出器

    将 trace 树和 metrics 导出为 JSON 文件，span 格式兼容 OpenTelemetry。
    """

    @staticmethod
    def export_trace(tracer: Optional[Tracer] = None) -> Optional[dict]:
        """将 trace 导出为字典

        Args:
            tracer: Tracer 实例，默认使用全局单例

        Returns:
            trace 字典，如果没有根 span 则返回 None
        """
        tracer = tracer or get_tracer()
        root = tracer.get_root_span()
        if root is None:
            return None

        spans = []
        JsonExporter._flatten_spans(root, spans)

        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": {
                            "service.name": "rodski",
                        }
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "rodski.observability"},
                            "spans": spans,
                        }
                    ],
                }
            ]
        }

    @staticmethod
    def _flatten_spans(span: Span, result: list) -> None:
        """递归展平 span 树为列表

        Args:
            span: 当前 span
            result: 结果列表（原地修改）
        """
        span_dict = {
            "name": span.name,
            "traceId": span.trace_id,
            "spanId": span.span_id,
            "startTimeUnixNano": int(span.start_time * 1e9),
            "endTimeUnixNano": int(span.end_time * 1e9) if span.end_time else None,
            "status": {"code": 1 if span.status == "ok" else 2},
            "attributes": [
                {"key": k, "value": {"stringValue": str(v)}}
                for k, v in span.attributes.items()
            ],
        }
        if span.parent_id:
            span_dict["parentSpanId"] = span.parent_id

        result.append(span_dict)

        for child in span.children:
            JsonExporter._flatten_spans(child, result)

    @staticmethod
    def export_metrics(collector: Optional[MetricsCollector] = None) -> dict:
        """将 metrics 导出为字典

        Args:
            collector: MetricsCollector 实例，默认使用全局单例

        Returns:
            metrics 摘要字典
        """
        collector = collector or MetricsCollector.get_instance()
        return collector.get_summary()

    @staticmethod
    def export_to_file(
        output_path: str,
        tracer: Optional[Tracer] = None,
        collector: Optional[MetricsCollector] = None,
    ) -> str:
        """导出 trace 和 metrics 到 JSON 文件

        Args:
            output_path: 输出文件路径
            tracer: Tracer 实例
            collector: MetricsCollector 实例

        Returns:
            实际写入的文件路径
        """
        data = {}

        trace_data = JsonExporter.export_trace(tracer)
        if trace_data:
            data["trace"] = trace_data

        metrics_data = JsonExporter.export_metrics(collector)
        if metrics_data and (metrics_data.get("counters") or metrics_data.get("histograms")):
            data["metrics"] = metrics_data

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"trace/metrics 已导出: {output}")
        return str(output)
