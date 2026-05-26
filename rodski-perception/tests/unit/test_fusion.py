"""fusion.py 单元测试 — 覆盖 IoU 计算、聚类、评分、融合裁决。"""

import pytest

from rodski_perception.fusion import (
    DEFAULT_WEIGHTS,
    FusionResult,
    HintResult,
    cluster_by_iou,
    compute_iou,
    fuse,
    score_cluster,
)


class TestComputeIoU:
    def test_identical_boxes(self):
        assert compute_iou((0, 0, 100, 100), (0, 0, 100, 100)) == 1.0

    def test_no_overlap(self):
        assert compute_iou((0, 0, 50, 50), (100, 100, 200, 200)) == 0.0

    def test_partial_overlap(self):
        iou = compute_iou((0, 0, 100, 100), (50, 50, 150, 150))
        # intersection = 50*50 = 2500, union = 10000+10000-2500 = 17500
        assert abs(iou - 2500 / 17500) < 0.001

    def test_contained(self):
        iou = compute_iou((0, 0, 200, 200), (50, 50, 100, 100))
        # intersection = 50*50 = 2500, union = 40000+2500-2500 = 40000
        assert abs(iou - 2500 / 40000) < 0.001


class TestClusterByIoU:
    def test_all_overlapping(self):
        results = [
            HintResult("vision_image", (100, 100, 200, 200), 0.9),
            HintResult("ocr", (110, 110, 210, 210), 0.8),
            HintResult("vision", (105, 105, 205, 205), 0.7),
        ]
        clusters = cluster_by_iou(results, threshold=0.5)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3

    def test_two_clusters(self):
        results = [
            HintResult("vision_image", (0, 0, 100, 100), 0.9),
            HintResult("ocr", (10, 10, 110, 110), 0.8),
            HintResult("vision", (500, 500, 600, 600), 0.7),
        ]
        clusters = cluster_by_iou(results, threshold=0.5)
        assert len(clusters) == 2

    def test_all_separate(self):
        results = [
            HintResult("vision_image", (0, 0, 50, 50), 0.9),
            HintResult("ocr", (200, 200, 250, 250), 0.8),
            HintResult("vision", (400, 400, 450, 450), 0.7),
        ]
        clusters = cluster_by_iou(results, threshold=0.5)
        assert len(clusters) == 3


class TestScoreCluster:
    def test_basic_scoring(self):
        cluster = [
            HintResult("vision_image", (100, 100, 200, 200), 0.9),
            HintResult("ocr", (110, 110, 210, 210), 0.8),
        ]
        score = score_cluster(cluster, DEFAULT_WEIGHTS)
        expected = 0.9 * 1.0 + 0.8 * 0.8
        assert abs(score - expected) < 0.001

    def test_element_type_bonus(self):
        cluster = [
            HintResult("vision", (100, 100, 200, 200), 0.7, label="button"),
        ]
        score_with = score_cluster(cluster, DEFAULT_WEIGHTS, element_type="button")
        score_without = score_cluster(cluster, DEFAULT_WEIGHTS, element_type=None)
        assert score_with > score_without


class TestFuse:
    def test_empty_returns_none(self):
        assert fuse([]) is None

    def test_single_hint(self):
        results = [HintResult("vision_image", (100, 100, 200, 200), 0.9)]
        r = fuse(results)
        assert r is not None
        assert r.consensus_count == 1
        assert r.coordinates == (150, 150)

    def test_three_hints_consensus(self):
        """三个 hints 高度重叠 → consensus_count=3, confidence 高。"""
        results = [
            HintResult("vision_image", (100, 100, 200, 200), 0.92),
            HintResult("ocr", (105, 105, 205, 205), 0.88),
            HintResult("vision", (102, 102, 202, 202), 0.75),
        ]
        r = fuse(results)
        assert r is not None
        assert r.consensus_count == 3
        assert r.confidence >= 0.85

    def test_two_consensus_one_outlier(self):
        """两个共识 + 一个偏离 → consensus_count=2。"""
        results = [
            HintResult("vision_image", (100, 100, 200, 200), 0.9),
            HintResult("ocr", (110, 110, 210, 210), 0.85),
            HintResult("vision", (500, 500, 600, 600), 0.7),
        ]
        r = fuse(results)
        assert r is not None
        assert r.consensus_count == 2

    def test_all_different_takes_highest_weight(self):
        """三个各不相同 → 取 weight 最高的聚类。"""
        results = [
            HintResult("vision_image", (0, 0, 50, 50), 0.9),
            HintResult("ocr", (200, 200, 250, 250), 0.8),
            HintResult("vision", (400, 400, 450, 450), 0.7),
        ]
        r = fuse(results)
        assert r is not None
        # vision_image has highest weight, so its cluster wins
        assert r.bbox == (0, 0, 50, 50)
