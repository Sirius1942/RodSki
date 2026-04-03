"""Vision Locator Capability"""
import base64
import json
import logging
import pathlib
from .base import BaseCapability

logger = logging.getLogger(__name__)


class VisionLocatorCapability(BaseCapability):
    """视觉定位能力"""

    def execute(self, screenshot_path: str, elements: list[dict]) -> list[dict]:
        """执行视觉定位

        Args:
            screenshot_path: 截图路径
            elements: OmniParser 解析的元素列表

        Returns:
            添加了 semantic_label 的元素列表
        """
        try:
            image_base64 = self._encode_image(screenshot_path)
            prompt = self._build_prompt(elements)
            response = self.client.call_vision(image_base64, prompt)
            labels = json.loads(response)
            return self._merge_labels(elements, labels)
        except Exception as e:
            logger.error(f"Vision locator failed: {e}")
            return elements  # 降级：返回原始元素

    def _encode_image(self, path: str) -> str:
        """Base64 编码图片"""
        with open(path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode()

    def _build_prompt(self, elements: list[dict]) -> str:
        """构建提示词"""
        element_summary = json.dumps(
            [{"index": i, "content": e.get("content", ""), "type": e.get("type", "")}
             for i, e in enumerate(elements)],
            ensure_ascii=False,
        )
        return (
            "你是一个 UI 元素语义分析助手。"
            "以下是从截图中识别出的 UI 元素列表（JSON 格式），"
            "请为每个元素生成一个简洁的中文语义标签（semantic_label），"
            "描述该元素的功能或用途。\n\n"
            f"元素列表：\n{element_summary}\n\n"
            "请严格以如下 JSON 数组格式返回，不要有任何多余内容：\n"
            '[{"index": 0, "semantic_label": "..."}，...]'
        )

    def _merge_labels(self, elements: list[dict], labels: list[dict]) -> list[dict]:
        """合并语义标签"""
        label_map = {item["index"]: item["semantic_label"] for item in labels}
        for i, elem in enumerate(elements):
            if i in label_map:
                elem["semantic_label"] = label_map[i]
        return elements
