"""评测指标计算。"""

from __future__ import annotations

from typing import List, Tuple


def center_in_bbox(
    center: Tuple[int, int],
    bbox: Tuple[int, int, int, int],
) -> bool:
    """判断预测中心点是否落在 expected_bbox 内。"""
    x, y = center
    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def accuracy(predictions: List[dict]) -> float:
    """accuracy = 预测中心点落在 expected_bbox 内的比例。"""
    if not predictions:
        return 0.0
    hits = sum(1 for p in predictions if p.get("hit", False))
    return hits / len(predictions)


def bbox_iou(
    a: Tuple[int, int, int, int],
    b: Tuple[int, int, int, int],
) -> float:
    """计算两个 bbox 的 IoU。"""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def latency_percentile(latencies: List[int], p: float) -> int:
    """计算延迟百分位数。"""
    if not latencies:
        return 0
    sorted_l = sorted(latencies)
    idx = int(len(sorted_l) * p / 100)
    idx = min(idx, len(sorted_l) - 1)
    return sorted_l[idx]


__all__ = ["center_in_bbox", "accuracy", "bbox_iou", "latency_percentile"]
