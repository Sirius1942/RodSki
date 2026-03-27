"""
VisionMatcher — 语义匹配算法

将用户描述（来自 locator="vision:<描述>"）与 LLMAnalyzer 增强后的
元素列表进行语义匹配，返回最佳候选或全部候选（按置信度降序）。

匹配策略（confidence 级别）：
  1.0  精确匹配：target == semantic_label（忽略大小写及首尾空格）
  0.8  包含匹配：target 包含在 semantic_label 中，或 semantic_label 包含在 target 中
  0.6  关键词交集：target 与 semantic_label 分词后关键词有交集
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """统一转小写、去除首尾空格。"""
    return text.strip().lower()


def _tokenize(text: str) -> set[str]:
    """
    简单分词：按非字母数字汉字边界切分，过滤空串和单字符停用词。
    同时保留原文作为一个 token，以支持多字词精确命中。
    """
    tokens = set(re.split(r'[\s\W]+', _normalize(text)))
    tokens.discard("")
    # 过滤单字母/数字噪音（保留中文单字）
    tokens = {t for t in tokens if len(t) > 1 or '\u4e00' <= t <= '\u9fff'}
    return tokens


def _score(target: str, label: str) -> float | None:
    """
    计算 target 与 label 之间的匹配置信度。
    无任何匹配时返回 None。
    """
    t = _normalize(target)
    l = _normalize(label)

    if not t or not l:
        return None

    # Level 1: 精确匹配
    if t == l:
        return 1.0

    # Level 2: 包含匹配
    if t in l or l in t:
        return 0.8

    # Level 3: 关键词交集
    t_tokens = _tokenize(target)
    l_tokens = _tokenize(label)
    if t_tokens and l_tokens and t_tokens & l_tokens:
        return 0.6

    return None

# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class VisionMatcher:
    """
    将文本描述与带 semantic_label 的元素列表进行语义匹配。

    Usage::

        matcher = VisionMatcher()
        best = matcher.match("登录按钮", elements)
        if best:
            print(best["bbox"], best["confidence"])
    """

    def match(self, target: str, elements: list[dict]) -> dict | None:
        """
        返回置信度最高的单个匹配元素，无匹配则返回 None。

        Parameters
        ----------
        target:
            用户描述字符串（locator="vision:<target>" 中的 target 部分）。
        elements:
            经 LLMAnalyzer.analyze() 增强后含 ``semantic_label`` 字段的列表。

        Returns
        -------
        匹配的元素字典（含额外的 ``confidence`` 字段），或 None。
        """
        candidates = self.match_all(target, elements)
        return candidates[0] if candidates else None

    def match_all(self, target: str, elements: list[dict]) -> list[dict]:
        """
        返回所有匹配候选，按 confidence 降序排列。

        Parameters
        ----------
        target:
            用户描述字符串。
        elements:
            经 LLMAnalyzer.analyze() 增强后含 ``semantic_label`` 字段的列表。

        Returns
        -------
        按 confidence 降序排列的匹配元素列表（每个元素含 ``confidence`` 字段）。
        若无任何匹配，返回空列表。
        """
        if not target or not elements:
            return []

        results: list[dict] = []
        for elem in elements:
            label = elem.get("semantic_label") or elem.get("content", "")
            confidence = _score(target, label)
            if confidence is not None:
                enhanced = dict(elem)
                enhanced["confidence"] = confidence
                results.append(enhanced)

        results.sort(key=lambda x: x["confidence"], reverse=True)
        logger.debug(
            "match_all('%s'): %d candidate(s) found from %d elements",
            target, len(results), len(elements),
        )
        return results
