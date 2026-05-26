"""rodski-perception 评测子系统。

提供数据集加载、指标计算、评测运行能力。
"""

from __future__ import annotations

from .dataset import EvalDataset, EvalTask, load_dataset
from .metrics import accuracy, bbox_iou, center_in_bbox, latency_percentile
from .runner import run_eval

__all__ = [
    "EvalDataset",
    "EvalTask",
    "load_dataset",
    "accuracy",
    "bbox_iou",
    "center_in_bbox",
    "latency_percentile",
    "run_eval",
]
