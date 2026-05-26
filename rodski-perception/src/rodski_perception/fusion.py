"""FusionLocator — 多定位器融合裁决算法。

算法流程（参考 v7.1.0-perception-design.md §1.5.2）：
1. 并行执行所有 hints，各自得到 bbox + confidence
2. 计算两两 bbox 的 IoU
3. IoU > threshold 的 bbox 归为一组（共识聚类）
4. 每组得分 = sum(confidence_i * weight[type_i])，element_type 一致加 +0.2
5. 返回最高分聚类的中心点 + 综合 confidence
6. 所有 hints 都失败 → 返回 None
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

DEFAULT_WEIGHTS: Dict[str, float] = {
    "vision_image": 1.0,
    "ocr": 0.8,
    "vision": 0.6,
}

ELEMENT_TYPE_BONUS = 0.2


@dataclass
class HintResult:
    """单个 hint 的定位结果。"""
    hint_type: str
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) pixel coords
    confidence: float
    label: str = ""
    latency_ms: int = 0


@dataclass
class FusionResult:
    """融合裁决输出。"""
    bbox: Tuple[int, int, int, int]
    coordinates: Tuple[int, int]
    confidence: float
    consensus_count: int
    hint_results: Dict[str, dict]


def compute_iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
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
    if union <= 0:
        return 0.0
    return inter / union


def cluster_by_iou(
    results: List[HintResult],
    threshold: float = 0.5,
) -> List[List[HintResult]]:
    """IoU 聚类：IoU > threshold 的 bbox 归为一组。

    使用贪心合并：遍历每个结果，如果与某个已有聚类中任一成员 IoU > threshold，
    则加入该聚类；否则新建聚类。
    """
    clusters: List[List[HintResult]] = []
    for r in results:
        merged = False
        for cluster in clusters:
            for member in cluster:
                if compute_iou(r.bbox, member.bbox) > threshold:
                    cluster.append(r)
                    merged = True
                    break
            if merged:
                break
        if not merged:
            clusters.append([r])
    return clusters


def score_cluster(
    cluster: List[HintResult],
    weights: Optional[Dict[str, float]] = None,
    element_type: Optional[str] = None,
) -> float:
    """计算聚类得分 = sum(confidence_i * weight[type_i]) + element_type bonus。"""
    w = weights or DEFAULT_WEIGHTS
    score = 0.0
    for r in cluster:
        base = r.confidence * w.get(r.hint_type, 0.5)
        # element_type 一致加成：label 中包含 element_type 关键词
        if element_type and r.label and element_type.lower() in r.label.lower():
            base += ELEMENT_TYPE_BONUS
        score += base
    return score


def _cluster_bbox(cluster: List[HintResult]) -> Tuple[int, int, int, int]:
    """取聚类中所有 bbox 的平均值作为共识 bbox。"""
    n = len(cluster)
    x1 = sum(r.bbox[0] for r in cluster) // n
    y1 = sum(r.bbox[1] for r in cluster) // n
    x2 = sum(r.bbox[2] for r in cluster) // n
    y2 = sum(r.bbox[3] for r in cluster) // n
    return (x1, y1, x2, y2)


def fuse(
    hint_results: List[HintResult],
    weights: Optional[Dict[str, float]] = None,
    element_type: Optional[str] = None,
    iou_threshold: float = 0.5,
) -> Optional[FusionResult]:
    """融合裁决主逻辑。

    Returns None if no hints succeeded.
    """
    if not hint_results:
        return None

    # 单个 hint 时直接返回
    if len(hint_results) == 1:
        r = hint_results[0]
        w = weights or DEFAULT_WEIGHTS
        conf = r.confidence * w.get(r.hint_type, 0.5)
        bbox = r.bbox
        cx, cy = (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2
        return FusionResult(
            bbox=bbox,
            coordinates=(cx, cy),
            confidence=min(conf, 1.0),
            consensus_count=1,
            hint_results={r.hint_type: {"bbox": list(r.bbox), "confidence": r.confidence}},
        )

    clusters = cluster_by_iou(hint_results, threshold=iou_threshold)

    # 对每个聚类评分，选最高分
    best_cluster: Optional[List[HintResult]] = None
    best_score = -1.0
    for cluster in clusters:
        s = score_cluster(cluster, weights, element_type)
        if s > best_score:
            best_score = s
            best_cluster = cluster

    if best_cluster is None:
        return None

    bbox = _cluster_bbox(best_cluster)
    cx, cy = (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2

    # 综合 confidence：归一化得分（除以理论最大值）
    w = weights or DEFAULT_WEIGHTS
    max_possible = sum(w.get(r.hint_type, 0.5) for r in hint_results)
    confidence = min(best_score / max_possible, 1.0) if max_possible > 0 else 0.0

    # 构建 hint_results dict
    hr_dict = {}
    for r in hint_results:
        hr_dict[r.hint_type] = {
            "bbox": list(r.bbox),
            "confidence": r.confidence,
            "latency_ms": r.latency_ms,
        }

    return FusionResult(
        bbox=bbox,
        coordinates=(cx, cy),
        confidence=confidence,
        consensus_count=len(best_cluster),
        hint_results=hr_dict,
    )


__all__ = [
    "HintResult",
    "FusionResult",
    "compute_iou",
    "cluster_by_iou",
    "score_cluster",
    "fuse",
    "DEFAULT_WEIGHTS",
]
