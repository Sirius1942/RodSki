"""
LLM Analyzer — 多模态 LLM 语义识别层

通过统一的 LLMClient 架构调用 Claude / OpenAI GPT-4V / Qwen-VL，
具体 provider 由 LLM 配置决定。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class LLMAnalyzer:
    """多模态 LLM 客户端，为 OmniParser 元素列表附加语义标签。

    内部调用统一的 LLMClient 架构。若 LLMClient 初始化失败，
    analyze() 将直接返回原始元素列表（不做任何修改）。
    """

    def __init__(self, config: dict | None = None, global_vars: dict | None = None) -> None:
        self._disabled = False
        try:
            from rodski.llm import LLMClient
            self._client = LLMClient(config, global_vars)
            self._capability = self._client.get_capability('vision_locator')
        except Exception as e:
            logger.warning("LLMClient init failed; LLMAnalyzer disabled: %s", e)
            self._client = None
            self._capability = None
            self._disabled = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        screenshot_path: str,
        elements: list[dict],
    ) -> list[dict]:
        """
        给每个 OmniParser 元素附加 ``semantic_label`` 字段。

        Parameters
        ----------
        screenshot_path:
            截图文件路径（PNG/JPEG/WebP）。
        elements:
            OmniParser 返回的 ``parsed_content_list``。

        Returns
        -------
        增强后的元素列表（in-place 修改后的副本），每个元素含
        ``semantic_label`` 字段。若 LLM 调用失败或分析器被禁用，
        则保留原始列表。
        """
        if not elements:
            return elements

        if self._disabled:
            logger.debug("LLMAnalyzer is disabled; returning elements unchanged.")
            return elements

        return self._capability.execute(screenshot_path, elements)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_labels(elements: list[dict], labels: list[dict]) -> list[dict]:
        """将 LLM 返回的语义标签合并回元素列表。"""
        label_map: dict[int, str] = {}
        for item in labels:
            idx = item.get("index")
            label = item.get("semantic_label", "")
            if idx is not None and label:
                label_map[idx] = label

        result = []
        for i, elem in enumerate(elements):
            enhanced = dict(elem)
            enhanced["semantic_label"] = label_map.get(i, elem.get("content", ""))
            result.append(enhanced)
        return result
