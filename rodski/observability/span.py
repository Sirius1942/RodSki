"""Span 数据结构 - 表示一个执行跨度"""
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Span:
    """表示一个执行跨度（trace 中的单个操作）

    Attributes:
        name: span 名称（如关键字名、阶段名）
        trace_id: 所属 trace 的唯一标识
        span_id: 本 span 的唯一标识
        parent_id: 父 span 标识，根 span 为 None
        start_time: 开始时间（Unix 时间戳，秒）
        end_time: 结束时间（Unix 时间戳，秒），未结束为 None
        attributes: 自由属性字典
        children: 子 span 列表
        status: 状态，"ok" 或 "error"
    """
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    status: str = "ok"

    @property
    def duration(self) -> float:
        """计算 span 持续时间（秒）

        Returns:
            持续时间，未结束则计算到当前时刻
        """
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def to_dict(self) -> dict:
        """转换为字典格式（兼容 OpenTelemetry span 格式）

        Returns:
            包含 span 信息的字典，时间戳为纳秒精度
        """
        result = {
            "name": self.name,
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "startTimeUnixNano": int(self.start_time * 1e9),
            "endTimeUnixNano": int(self.end_time * 1e9) if self.end_time else None,
            "attributes": self.attributes,
            "status": self.status,
        }
        if self.parent_id:
            result["parentSpanId"] = self.parent_id
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result

    @staticmethod
    def generate_id() -> str:
        """生成唯一标识（16 字符十六进制）"""
        return uuid.uuid4().hex[:16]

    @staticmethod
    def generate_trace_id() -> str:
        """生成 trace ID（32 字符十六进制）"""
        return uuid.uuid4().hex
