"""OCR 文字定位器（v7.1.0 重构：与 OmniClient 解耦）。

v7.1.0 之前 ``OCRLocator`` 直接持有 ``OmniClient`` 实例并调用其 ``parse``
方法获取文字元素。v7.1.0 把 OmniClient 从 rodski 核心移除后，本模块
退化为一个 **协议适配层**：

- 调用方可注入任意实现 ``parse(screenshot, box_threshold, iou_threshold)``
  的对象（duck typing），例如 rodski-perception backend 暴露的 OCR 子能力
- 未注入 provider 时，``locate_text`` / ``get_all_text_elements`` 抛出
  清晰的 ``RuntimeError`` 并附带升级指引

设计参考：``rodski/docs/CORE_DESIGN_CONSTRAINTS.md`` §2.6.7（``ocr``
定位器不走 PerceptionBackend，由 rodski 自带 OCR provider；54c 会接入
真正的本地 OCR 实现）。
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

logger = logging.getLogger(__name__)

# Type alias for screenshot input
ScreenshotInput = Union[str, Path, bytes]


class _OCRProviderProtocol(Protocol):
    """OCR 后端协议（duck typed）。

    任意实现 ``parse(screenshot, box_threshold, iou_threshold)`` 并返回
    元素列表的对象都可作为 provider 注入。
    """

    def parse(  # pragma: no cover - 协议声明
        self,
        screenshot: Any,
        box_threshold: float = 0.18,
        iou_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]: ...


_NO_PROVIDER_HINT = (
    "OCR provider 未配置。v7.1.0 起 rodski 核心不再内置 OmniParser 客户端。\n"
    "  解决方案：\n"
    "    - 升级到 v7.1.0 后的本地 OCR 实现（rodski-perception 提供）\n"
    "    - 或通过 OCRLocator(provider=...) 注入自定义 OCR provider\n"
    "  参考 docs/CORE_DESIGN_CONSTRAINTS.md §2.6.7"
)



class OCRLocator:
    """OCR 文字定位器（v7.1.0 起 provider-agnostic）。

    通过注入的 ``provider`` 对象解析截图中的 UI 元素并筛选文字元素。
    未注入 provider 时，调用 ``locate_text`` 等方法会抛 ``RuntimeError``
    指引用户安装 OCR 实现。

    Args:
        provider: OCR provider，需实现
            ``parse(screenshot, box_threshold, iou_threshold) -> list[dict]``。
            可为 ``None``，此时所有定位方法在调用时报错。
        box_threshold: 边界框检测阈值，默认 0.18。
        iou_threshold: IoU 阈值用于 NMS，默认 0.7。
        omni_client: **已废弃**，等价于 ``provider``，仅保留向后兼容形参。

    Examples:
        >>> # 注入自定义 OCR provider
        >>> locator = OCRLocator(provider=my_ocr_provider)
        >>> bbox = locator.locate_text("登录", "screenshot.png")
        >>>
        >>> # 无 provider 时调用报错（v7.1.0 起的默认行为）
        >>> OCRLocator().locate_text("x", "y.png")   # RuntimeError
    """

    def __init__(
        self,
        provider: Optional[_OCRProviderProtocol] = None,
        box_threshold: float = 0.18,
        iou_threshold: float = 0.7,
        *,
        omni_client: Optional[_OCRProviderProtocol] = None,
    ) -> None:
        # 向后兼容：旧代码用 omni_client= 形参
        if provider is None and omni_client is not None:
            provider = omni_client
        self._omni_client = provider  # 保留旧属性名供既有测试访问
        self._provider = provider
        self._box_threshold = box_threshold
        self._iou_threshold = iou_threshold

    # ------------------------------------------------------------------
    # provider 注入 / 检查
    # ------------------------------------------------------------------

    def set_provider(self, provider: _OCRProviderProtocol) -> None:
        """运行时注入 / 替换 OCR provider。"""
        self._provider = provider
        self._omni_client = provider

    def _require_provider(self) -> _OCRProviderProtocol:
        if self._provider is None:
            raise RuntimeError(_NO_PROVIDER_HINT)
        return self._provider


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
            # 调用 provider 解析截图
            provider = self._require_provider()
            raw_elements = provider.parse(
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
            from PIL import Image  # 延迟导入避免顶层 ImportError
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