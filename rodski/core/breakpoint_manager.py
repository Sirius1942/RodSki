"""断点管理器 - 支持多层级断点设置和触发检测

支持断点类型：
- step:N - 在第 N 个测试步骤前暂停
- scenario:ID - 在指定 scenario 前暂停
- node:NAME - 在业务模型节点前暂停
- flow:ID - 在指定 Flow 前暂停
- driver:ACTION - 在指定驱动动作前暂停（如 click, fill）
- batch:row:N - 在批量操作的第 N 行前暂停
"""
import logging
import re
from typing import List, Optional, Set, Tuple, Literal
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("rodski")


class BreakpointType(str, Enum):
    """断点类型"""
    STEP = "step"
    SCENARIO = "scenario"
    NODE = "node"
    FLOW = "flow"
    DRIVER = "driver"
    BATCH_ROW = "batch:row"
    BUSINESS_CALL = "business_call"


@dataclass
class Breakpoint:
    """断点定义"""
    type: BreakpointType
    value: str  # 断点值（如步骤号、scenario ID、node 名称）
    condition: Optional[str] = None  # 可选条件（未来扩展）
    enabled: bool = True

    def matches(self, **kwargs) -> bool:
        """检查是否匹配断点条件"""
        if not self.enabled:
            return False

        if self.type == BreakpointType.STEP:
            step_num = kwargs.get("step_num")
            return step_num is not None and str(step_num) == self.value

        elif self.type == BreakpointType.SCENARIO:
            scenario_id = kwargs.get("scenario_id")
            return scenario_id is not None and scenario_id == self.value

        elif self.type == BreakpointType.NODE:
            node_name = kwargs.get("node_name")
            return node_name is not None and node_name == self.value

        elif self.type == BreakpointType.FLOW:
            flow_id = kwargs.get("flow_id")
            return flow_id is not None and flow_id == self.value

        elif self.type == BreakpointType.DRIVER:
            driver_action = kwargs.get("driver_action")
            return driver_action is not None and driver_action == self.value

        elif self.type == BreakpointType.BATCH_ROW:
            batch_row = kwargs.get("batch_row")
            return batch_row is not None and str(batch_row) == self.value

        elif self.type == BreakpointType.BUSINESS_CALL:
            business_call_id = kwargs.get("business_call_id")
            return business_call_id is not None and business_call_id == self.value

        return False

    def __str__(self) -> str:
        return f"{self.type.value}:{self.value}"


class BreakpointManager:
    """断点管理器"""

    def __init__(self):
        self.breakpoints: List[Breakpoint] = []
        self._hit_count: int = 0

    def add_breakpoint(self, bp: Breakpoint) -> None:
        """添加断点"""
        self.breakpoints.append(bp)
        logger.info(f"[Breakpoint] Added: {bp}")

    def add_from_string(self, bp_str: str) -> bool:
        """从字符串添加断点

        支持格式：
        - step:5
        - scenario:S003
        - node:fill_vin
        - flow:F_INVOICE_PLATFORM
        - driver:click
        - batch:row:3
        - business_call:PUBLISH_INQUIRY.node:submit_configured_inquiry
        """
        bp_str = bp_str.strip()

        # 处理嵌套断点（如 business_call:ID.node:NAME）
        if ".node:" in bp_str:
            parts = bp_str.split(".node:")
            if len(parts) == 2 and parts[0].startswith("business_call:"):
                business_call_id = parts[0].replace("business_call:", "")
                node_name = parts[1]
                # 添加两个断点：business_call 和 node
                self.add_breakpoint(Breakpoint(
                    type=BreakpointType.BUSINESS_CALL,
                    value=business_call_id
                ))
                self.add_breakpoint(Breakpoint(
                    type=BreakpointType.NODE,
                    value=node_name
                ))
                return True

        # 标准格式：type:value
        if ":" not in bp_str:
            logger.warning(f"[Breakpoint] Invalid format: {bp_str} (expected type:value)")
            return False

        # 处理 batch:row:N
        if bp_str.startswith("batch:row:"):
            row_num = bp_str.replace("batch:row:", "")
            if not row_num.isdigit():
                logger.warning(f"[Breakpoint] Invalid batch row number: {row_num}")
                return False
            self.add_breakpoint(Breakpoint(
                type=BreakpointType.BATCH_ROW,
                value=row_num
            ))
            return True

        # 标准断点
        parts = bp_str.split(":", 1)
        if len(parts) != 2:
            logger.warning(f"[Breakpoint] Invalid format: {bp_str}")
            return False

        bp_type_str, bp_value = parts
        try:
            bp_type = BreakpointType(bp_type_str)
        except ValueError:
            logger.warning(f"[Breakpoint] Unknown type: {bp_type_str}")
            return False

        self.add_breakpoint(Breakpoint(type=bp_type, value=bp_value))
        return True

    def check_hit(self, **kwargs) -> Optional[Breakpoint]:
        """检查是否命中断点"""
        for bp in self.breakpoints:
            if bp.matches(**kwargs):
                self._hit_count += 1
                logger.info(f"[Breakpoint] Hit #{self._hit_count}: {bp}")
                return bp
        return None

    def remove_breakpoint(self, index: int) -> bool:
        """移除断点"""
        if 0 <= index < len(self.breakpoints):
            removed = self.breakpoints.pop(index)
            logger.info(f"[Breakpoint] Removed: {removed}")
            return True
        return False

    def clear_all(self) -> None:
        """清除所有断点"""
        count = len(self.breakpoints)
        self.breakpoints.clear()
        logger.info(f"[Breakpoint] Cleared {count} breakpoints")

    def list_breakpoints(self) -> List[str]:
        """列出所有断点"""
        return [str(bp) for bp in self.breakpoints]

    def get_hit_count(self) -> int:
        """获取断点命中次数"""
        return self._hit_count


def parse_breakpoints_from_args(break_at: Optional[str]) -> List[str]:
    """从命令行参数解析断点列表

    Args:
        break_at: 断点字符串，支持逗号分隔多个断点
                 如："step:3,step:7,node:fill_vin"

    Returns:
        断点字符串列表
    """
    if not break_at:
        return []

    # 按逗号分隔
    parts = [p.strip() for p in break_at.split(",") if p.strip()]
    return parts
