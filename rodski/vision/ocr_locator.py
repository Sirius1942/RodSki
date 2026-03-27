"""OCR 文字定位器 - 使用 OmniParser 实现文字定位。

提供基于 OmniParser 服务的 OCR 文字定位功能，支持精确匹配和模糊匹配。
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Type alias for screenshot input
ScreenshotInput = Union[str, Path, bytes]


class OCRLocator:
    """OCR 文字定位器 - 使用 OmniParser 服务。

    通过 OmniParser 服务解析截图中的 UI 元素，筛选文字元素并提供文本定位能力。

    Args:
        omni_client: OmniClient 实例，用于调用 OmniParser 服务。
        box_threshold: 边界框检测阈值，默认 0.18。
        iou_threshold: IoU 阈值用于 NMS，默认 0.7。

    Examples:
        >>> from rodski.vision import OmniClient
        >>> client = OmniClient(url="http://localhost:8001")
        >>> locator = OCRLocator(client)
        >>> # 定位单个文字
        >>> bbox = locator.locate_text("登录", screenshot_path)
        >>> # 定位所有匹配文字
        >>> bboxes = locator.locate_all_text("确定", screenshot_path)
        >>> # 获取所有文字元素
        >>> elements = locator.get_all_text_elements(screenshot_path)
    """

    def __init__(
        self,
        omni_client,
        box_threshold: float = 0.18,
        iou_threshold: float = 0.7,
    ) -> None:
        """初始化 OCR 定位器。

        Args:
            omni_client: OmniClient 实例。
            box_threshold: 边界框检测阈值。
            iou_threshold: IoU 阈值。
        """
        self._omni_client = omni_client
        self._box_threshold = box_threshold
        self._iou_threshold = iou_threshold

    def locate_text(
        self,
        text: str,
        screenshot: ScreenshotInput,
        exact: bool = False,
    ) -> Optional[Tuple[int, int, int, int]]:
        """在截图中定位指定文字。

        Args:
            text: 要定位的文字内容。
            screenshot: 截图输入，支持以下格式：
                - 文件路径 (str 或 Path)
                - bytes (原始图像数据)
            exact: 是否精确匹配（默认 False 为模糊/包含匹配）。

        Returns:
            (x1, y1, x2, y2) 文字区域边界框（像素坐标），
            未找到返回 None。

        Raises:
            FileNotFoundError: 如果 screenshot 是路径且文件不存在。
            OmniParserError: 如果 OmniParser 服务调用失败。

        Examples:
            >>> bbox = locator.locate_text("登录", "screenshot.png")
            >>> if bbox:
            ...     x1, y1, x2, y2 = bbox
            ...     print(f"Found at: ({x1}, {y1}) - ({x2}, {y2})")
        """
        all_elements = self.get_all_text_elements(screenshot)
        if not all_elements:
            logger.debug("No text elements found in screenshot")
            return None

        matched_bbox = self._find_text_match(text, all_elements, exact)
        if matched_bbox:
            logger.debug("Located text '%s' at bbox=%s", text, matched_bbox)
        else:
            logger.debug("Text '%s' not found in screenshot", text)

        return matched_bbox

    def locate_all_text(
        self,
        text: str,
        screenshot: ScreenshotInput,
        exact: bool = False,
    ) -> List[Tuple[int, int, int, int]]:
        """定位所有匹配的文字位置。

        Args:
            text: 要定位的文字内容。
            screenshot: 截图输入（同 locate_text）。
            exact: 是否精确匹配（默认 False 为模糊/包含匹配）。

        Returns:
            边界框列表，每个元素为 (x1, y1, x2, y2) 像素坐标。
            未找到返回空列表。

        Examples:
            >>> bboxes = locator.locate_all_text("确定", "screenshot.png")
            >>> for bbox in bboxes:
            ...     print(f"Found at: {bbox}")
        """
        all_elements = self.get_all_text_elements(screenshot)
        if not all_elements:
            logger.debug("No text elements found in screenshot")
            return []

        matched_bboxes = self._find_all_text_matches(text, all_elements, exact)
        logger.debug("Found %d occurrences of text '%s'", len(matched_bboxes), text)
        return matched_bboxes

    def get_all_text_elements(self, screenshot: ScreenshotInput) -> List[Dict]:
        """获取截图中所有文字元素。

        Args:
            screenshot: 截图输入（同 locate_text）。

        Returns:
            文字元素列表，每个元素为字典格式：
            [
                {
                    "content": "文字内容",
                    "bbox": [x1, y1, x2, y2],  # 像素坐标
                    "type": "text",
                    "confidence": float  # 可选
                },
                ...
            ]

        Raises:
            FileNotFoundError: 如果 screenshot 是路径且文件不存在。
            OmniParserError: 如果 OmniParser 服务调用失败。

        Examples:
            >>> elements = locator.get_all_text_elements("screenshot.png")
            >>> for elem in elements:
            ...     print(f"{elem['content']} at {elem['bbox']}")
        """
        # 准备截图路径
        screenshot_path, need_cleanup = self._prepare_screenshot(screenshot)

        try:
            # 调用 OmniParser
            raw_elements = self._omni_client.parse(
                screenshot_path,
                box_threshold=self._box_threshold,
                iou_threshold=self._iou_threshold,
            )

            # 获取图像尺寸用于坐标转换
            img_w, img_h = self._get_image_size(screenshot_path)

            # 筛选 text 类型元素并转换坐标
            text_elements = []
            for elem in raw_elements:
                if elem.get("type") != "text":
                    continue

                bbox = elem.get("bbox")
                if not bbox or len(bbox) != 4:
                    logger.warning("Element has invalid bbox: %s", elem)
                    continue

                # 转换归一化坐标到像素坐标
                x1 = int(bbox[0] * img_w)
                y1 = int(bbox[1] * img_h)
                x2 = int(bbox[2] * img_w)
                y2 = int(bbox[3] * img_h)

                text_elements.append({
                    "content": elem.get("content", ""),
                    "bbox": [x1, y1, x2, y2],
                    "type": "text",
                    "confidence": elem.get("confidence"),
                })

            logger.debug(
                "Found %d text elements from %d total elements",
                len(text_elements),
                len(raw_elements),
            )
            return text_elements

        finally:
            if need_cleanup:
                self._cleanup_tmp(screenshot_path)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _prepare_screenshot(self, screenshot: ScreenshotInput) -> Tuple[str, bool]:
        """准备截图文件路径。

        将各种输入格式转换为文件路径。

        Args:
            screenshot: 截图输入。

        Returns:
            (文件路径, 是否需要清理) 元组。

        Raises:
            FileNotFoundError: 如果是路径且文件不存在。
        """
        # 已经是路径
        if isinstance(screenshot, (str, Path)):
            path = Path(screenshot)
            if not path.exists():
                raise FileNotFoundError(f"Screenshot file not found: {screenshot}")
            return str(path), False

        # bytes
        if isinstance(screenshot, bytes):
            return self._save_bytes_to_temp(screenshot), True

        raise TypeError(
            f"Unsupported screenshot type: {type(screenshot).__name__}. "
            "Expected str, Path, or bytes."
        )

    def _save_bytes_to_temp(self, data: bytes) -> str:
        """将字节数据保存到临时文件。"""
        tmp_dir = tempfile.gettempdir()
        filename = f"rodski_ocr_{int(time.time() * 1000)}.png"
        output_path = Path(tmp_dir) / filename
        output_path.write_bytes(data)
        logger.debug("Saved bytes to temp file: %s", output_path)
        return str(output_path)

    def _cleanup_tmp(self, path: str) -> None:
        """删除临时文件。"""
        try:
            p = Path(path)
            if p.exists():
                p.unlink()
        except OSError as exc:
            logger.debug("Could not delete temp file %s: %s", path, exc)

    @staticmethod
    def _get_image_size(image_path: str) -> Tuple[int, int]:
        """返回图像的 (width, height)。"""
        try:
            with Image.open(image_path) as img:
                return img.size  # (width, height)
        except Exception as exc:
            logger.warning("Could not determine image size: %s, defaulting to 1920x1080", exc)
            return 1920, 1080

    def _find_text_match(
        self,
        text: str,
        elements: List[Dict],
        exact: bool,
    ) -> Optional[Tuple[int, int, int, int]]:
        """在元素列表中查找匹配的文字。

        Args:
            text: 目标文字。
            elements: 文字元素列表。
            exact: 是否精确匹配。

        Returns:
            第一个匹配元素的边界框，未找到返回 None。
        """
        for elem in elements:
            content = elem.get("content", "")
            if self._text_matches(text, content, exact):
                bbox = elem["bbox"]
                return (bbox[0], bbox[1], bbox[2], bbox[3])
        return None

    def _find_all_text_matches(
        self,
        text: str,
        elements: List[Dict],
        exact: bool,
    ) -> List[Tuple[int, int, int, int]]:
        """在元素列表中查找所有匹配的文字。

        Args:
            text: 目标文字。
            elements: 文字元素列表。
            exact: 是否精确匹配。

        Returns:
            所有匹配元素的边界框列表。
        """
        bboxes = []
        for elem in elements:
            content = elem.get("content", "")
            if self._text_matches(text, content, exact):
                bbox = elem["bbox"]
                bboxes.append((bbox[0], bbox[1], bbox[2], bbox[3]))
        return bboxes

    @staticmethod
    def _text_matches(target: str, content: str, exact: bool) -> bool:
        """检查文本是否匹配。

        Args:
            target: 目标文字。
            content: 元素内容。
            exact: 是否精确匹配。

        Returns:
            是否匹配。
        """
        if exact:
            return target == content
        else:
            # 模糊匹配：目标文字包含在元素内容中
            return target in content