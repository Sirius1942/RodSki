"""VisionLocator — 视觉定位器统一入口。

解析 model.xml 中 element 的 ``locator`` 属性，返回屏幕坐标边界框 ``(x1, y1, x2, y2)``。

支持三种定位器格式：

* ``vision:<描述>``    — 截图 → OmniParser → LLM 语义分析 → 匹配 → 边界框
* ``vision:<模板图片路径>`` — 图片模板匹配 → 边界框（延迟加载 ImageMatcher）
* ``ocr:<文字内容>`` — OCR 文字识别定位 → 边界框（延迟加载 OCRLocator）
* ``vision_bbox:x1,y1,x2,y2`` — 直接解析坐标字符串

依赖 vision_config.yaml（位于 rodski/config/），缺失时使用内置默认值。
"""

from __future__ import annotations

import logging
import os
import pathlib
import tempfile
import time
from typing import Any, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)

_PREFIX_VISION = "vision:"
_PREFIX_OCR = "ocr:"
_PREFIX_BBOX = "vision_bbox:"

_CONFIG_PATH = (
    pathlib.Path(__file__).parent.parent  # rodski/
    / "config"
    / "vision_config.yaml"
)

_DEFAULT_CONFIG: dict[str, Any] = {
    "omniparser": {
        "url": "http://14.103.175.167:7862/parse/",
        "box_threshold": 0.18,
        "iou_threshold": 0.7,
        "timeout": 5,
    },
    "screenshot": {
        "tmp_dir": "",   # 空字符串 → 使用系统临时目录
        "cleanup_max": 20,
    },
    "locator": {
        "min_confidence": 0.6,
        "images_dir": "images",
        "match_threshold": 0.8,
    },
    "cache": {
        "enabled": False,
        "ttl": 300,
    },
}

def _load_config(extra: dict | None = None) -> dict[str, Any]:
    """合并配置：外部传入 > vision_config.yaml > 内置默认值。"""
    import copy
    cfg = copy.deepcopy(_DEFAULT_CONFIG)
    if _CONFIG_PATH.exists():
        try:
            import yaml  # optional dependency
            with _CONFIG_PATH.open(encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            for section, values in raw.items():
                if isinstance(values, dict):
                    cfg.setdefault(section, {}).update(values)
                else:
                    cfg[section] = values
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load vision_config.yaml: %s", exc)
    if extra:
        for section, values in extra.items():
            if isinstance(values, dict):
                cfg.setdefault(section, {}).update(values)
            else:
                cfg[section] = values
    return cfg


class VisionLocator:
    """视觉定位器统一入口，整合多种定位策略。

    支持三种定位器类型：
        - vision: 图片模板匹配或语义匹配
        - ocr: OCR 文字定位
        - vision_bbox: 坐标定位

    Args:
        config: 配置字典，支持以下键：
            - images_dir: 模板图片目录
            - match_threshold: 图片匹配阈值
            - omni_url: OmniParser 服务地址
            - cache_ttl: 缓存 TTL
            - cache_enabled: 是否启用缓存
        omni_client: OmniClient 实例；为 None 时按配置自动创建。
        llm_analyzer: LLMAnalyzer 实例；为 None 时按配置自动创建。
        matcher: VisionMatcher 实例；为 None 时自动创建。
        cache: 预留缓存参数（当前不实现，保留接口）。
        global_vars: 全局变量
    """

    def __init__(
        self,
        config: dict | None = None,
        omni_client=None,
        llm_analyzer=None,
        matcher=None,
        cache=None,
        global_vars: dict | None = None,
    ) -> None:
        self._cfg = _load_config(config)
        self._cache = cache  # reserved
        self._global_vars = global_vars

        # 延迟初始化：外部注入优先，否则按需创建
        self._omni_client = omni_client
        self._llm_analyzer = llm_analyzer
        self._matcher = matcher

        # 延迟加载的定位器（新 API）
        self._image_matcher = None
        self._ocr_locator = None
        self._bbox_locator = None

    # ------------------------------------------------------------------
    # 延迟加载属性
    # ------------------------------------------------------------------

    @property
    def image_matcher(self):
        """延迟加载 ImageMatcher（图片模板匹配）。"""
        if self._image_matcher is None:
            from .image_matcher import ImageMatcher
            self._image_matcher = ImageMatcher(
                images_dir=self._cfg.get("locator", {}).get("images_dir", "images"),
                threshold=self._cfg.get("locator", {}).get("match_threshold", 0.8)
            )
        return self._image_matcher

    @property
    def ocr_locator(self):
        """延迟加载 OCRLocator（文字定位）。"""
        if self._ocr_locator is None:
            from .ocr_locator import OCRLocator
            omni_client = self._get_omni_client()
            omni_cfg = self._cfg.get("omniparser", {})
            self._ocr_locator = OCRLocator(
                omni_client=omni_client,
                box_threshold=omni_cfg.get("box_threshold", 0.18),
                iou_threshold=omni_cfg.get("iou_threshold", 0.7),
            )
        return self._ocr_locator

    @property
    def bbox_locator(self):
        """延迟加载 BBoxLocator（坐标定位）。"""
        if self._bbox_locator is None:
            from .bbox_locator import BBoxLocator
            self._bbox_locator = BBoxLocator()
        return self._bbox_locator

    # ------------------------------------------------------------------
    # Public API - 统一定位入口
    # ------------------------------------------------------------------

    def locate(
        self,
        locator_type: str,
        locator_value: str,
        screenshot
    ) -> Optional[Tuple[int, int, int, int]]:
        """统一定位入口，返回边界框坐标。

        Args:
            locator_type: 定位器类型
                - vision: 图片匹配或语义匹配
                - ocr: 文字定位
                - vision_bbox: 坐标定位
            locator_value: 定位器值
                - vision: 模板图片路径或语义描述
                - ocr: 待定位的文字内容
                - vision_bbox: "x1,y1,x2,y2" 格式坐标字符串
            screenshot: 截图，可以是：
                - str/Path: 截图文件路径
                - PIL.Image.Image: PIL 图像对象
                - bytes: 图像字节数据

        Returns:
            (x1, y1, x2, y2) 边界框坐标，未找到返回 None。

        Raises:
            ValueError: 不支持的定位器类型。
        """
        if not locator_type or not locator_value:
            raise ValueError("locator_type and locator_value must not be empty")

        locator_type = locator_type.strip().lower()
        locator_value = locator_value.strip()

        if locator_type == "vision":
            return self._locate_by_vision(locator_value, screenshot)
        elif locator_type == "ocr":
            return self._locate_by_ocr(locator_value, screenshot)
        elif locator_type == "vision_bbox":
            return self._locate_by_bbox(locator_value)
        else:
            raise ValueError(
                f"Unsupported locator type: {locator_type!r}. "
                f"Expected 'vision', 'ocr', or 'vision_bbox'."
            )

    def _locate_by_vision(
        self,
        locator_value: str,
        screenshot
    ) -> Optional[Tuple[int, int, int, int]]:
        """图片匹配定位。

        优先尝试模板图片匹配，若失败则尝试语义匹配（OmniParser + LLM）。

        Args:
            locator_value: 模板图片路径或语义描述
            screenshot: 截图

        Returns:
            (x1, y1, x2, y2) 边界框坐标，未找到返回 None。
        """
        # 判断是否为图片路径（存在文件或以路径特征开头）
        is_image_path = self._is_image_path(locator_value)

        if is_image_path:
            # 模板图片匹配
            try:
                return self.image_matcher.match(locator_value, screenshot)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Template matching failed: %s, falling back to semantic", exc)

        # 语义匹配（OmniParser + LLM）
        return self._locate_by_semantic(locator_value, screenshot)

    def _is_image_path(self, value: str) -> bool:
        """判断值是否为图片路径。"""
        # 检查是否为绝对路径或相对路径
        if os.path.isabs(value) or value.startswith(("./", "../")):
            return True
        # 检查是否为图片文件名（带扩展名）
        image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
        ext = os.path.splitext(value)[1].lower()
        if ext in image_extensions:
            return True
        # 检查文件是否存在
        if os.path.exists(value):
            return True
        return False

    def _locate_by_semantic(
        self,
        description: str,
        screenshot
    ) -> Optional[Tuple[int, int, int, int]]:
        """语义匹配定位（OmniParser + LLM）。

        Args:
            description: 语义描述
            screenshot: 截图

        Returns:
            (x1, y1, x2, y2) 边界框坐标，未找到返回 None。
        """
        if not description.strip():
            return None

        # 获取截图路径
        screenshot_path = self._get_screenshot_path(screenshot)

        try:
            # 调用 OmniParser 解析
            elements = self._parse_screenshot(screenshot_path)
            # 调用 LLM 增强语义标签
            elements = self._analyze(screenshot_path, elements)
            # 匹配并返回坐标
            return self._match_and_resolve_bbox(description, elements, screenshot_path)
        finally:
            # 清理临时文件（仅当 screenshot 是我们创建的临时文件时）
            pass

    def _locate_by_ocr(
        self,
        text: str,
        screenshot
    ) -> Optional[Tuple[int, int, int, int]]:
        """OCR 文字定位。

        Args:
            text: 待定位的文字内容
            screenshot: 截图

        Returns:
            (x1, y1, x2, y2) 边界框坐标，未找到返回 None。
        """
        return self.ocr_locator.locate_text(text, screenshot)

    def _locate_by_bbox(self, bbox_str: str) -> Tuple[int, int, int, int]:
        """坐标定位。

        Args:
            bbox_str: "x1,y1,x2,y2" 格式的坐标字符串

        Returns:
            (x1, y1, x2, y2) 边界框坐标

        Raises:
            InvalidBBoxError: 坐标格式无效。
        """
        return self.bbox_locator.locate(bbox_str)

    # ------------------------------------------------------------------
    # Legacy API - 向后兼容
    # ------------------------------------------------------------------

    def is_vision_locator(self, locator_str: str) -> bool:
        """判断字符串是否是视觉定位器（vision:/ocr:/vision_bbox: 前缀）。"""
        if not locator_str:
            return False
        s = locator_str.strip()
        return (
            s.startswith(_PREFIX_VISION)
            or s.startswith(_PREFIX_OCR)
            or s.startswith(_PREFIX_BBOX)
        )

    def locate_legacy(self, locator_str: str, driver=None) -> Tuple[int, int]:
        """解析 locator 字符串，返回 (cx, cy) 中心坐标。

        这是向后兼容的旧 API，内部调用新的 locate() 方法。

        Args:
            locator_str: 形如 ``"vision:登录按钮"`` 或
                ``"vision_bbox:100,200,150,250"`` 的定位字符串。
            driver: Selenium WebDriver 实例（web 截图时使用）；
                为 None 时使用桌面截图。

        Returns:
            ``(cx, cy)`` 像素坐标元组。

        Raises:
            ValueError: locator_str 格式不合法或无法解析。
            RuntimeError: OmniParser / LLM 调用失败，或未找到匹配元素。
        """
        s = locator_str.strip() if locator_str else ""
        if not s:
            raise ValueError("locator_str must not be empty")

        # 解析前缀和值
        if s.startswith(_PREFIX_BBOX):
            bbox_str = s[len(_PREFIX_BBOX):]
            bbox = self._locate_by_bbox(bbox_str)
            cx = (bbox[0] + bbox[2]) // 2
            cy = (bbox[1] + bbox[3]) // 2
            return cx, cy

        if s.startswith(_PREFIX_OCR):
            text = s[len(_PREFIX_OCR):]
            screenshot_path = self._take_screenshot(driver)
            try:
                bbox = self.locate("ocr", text, screenshot_path)
                if bbox is None:
                    raise RuntimeError(f"OCR text not found: {text!r}")
                cx = (bbox[0] + bbox[2]) // 2
                cy = (bbox[1] + bbox[3]) // 2
                return cx, cy
            finally:
                self._cleanup_tmp(screenshot_path)

        if s.startswith(_PREFIX_VISION):
            value = s[len(_PREFIX_VISION):]
            screenshot_path = self._take_screenshot(driver)
            try:
                bbox = self.locate("vision", value, screenshot_path)
                if bbox is None:
                    raise RuntimeError(f"Vision element not found: {value!r}")
                cx = (bbox[0] + bbox[2]) // 2
                cy = (bbox[1] + bbox[3]) // 2
                return cx, cy
            finally:
                self._cleanup_tmp(screenshot_path)

        raise ValueError(
            f"Unsupported locator format: {locator_str!r}. "
            f"Expected 'vision:<desc>', 'ocr:<text>', or 'vision_bbox:x1,y1,x2,y2'."
        )

    # 保持向后兼容：locate_legacy 作为默认 locate 方法
    # 新代码应使用新的 locate(type, value, screenshot) API
    def locate_with_driver(self, locator_str: str, driver=None) -> Tuple[int, int]:
        """解析 locator 字符串，返回 (cx, cy) 中心坐标。

        这是向后兼容的 API，与 locate_legacy 相同。
        """
        return self.locate_legacy(locator_str, driver)

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _get_screenshot_path(self, screenshot) -> str:
        """将截图输入转换为文件路径。"""
        if isinstance(screenshot, (str, pathlib.Path)):
            return str(screenshot)
        elif isinstance(screenshot, Image.Image):
            # 保存到临时文件
            tmp_dir = self._cfg["screenshot"].get("tmp_dir") or tempfile.gettempdir()
            filename = f"rodski_vision_{int(time.time() * 1000)}.png"
            output_path = str(pathlib.Path(tmp_dir) / filename)
            screenshot.save(output_path, format="PNG")
            return output_path
        elif isinstance(screenshot, bytes):
            # 保存到临时文件
            tmp_dir = self._cfg["screenshot"].get("tmp_dir") or tempfile.gettempdir()
            filename = f"rodski_vision_{int(time.time() * 1000)}.png"
            output_path = str(pathlib.Path(tmp_dir) / filename)
            with open(output_path, "wb") as f:
                f.write(screenshot)
            return output_path
        else:
            raise TypeError(
                f"Unsupported screenshot type: {type(screenshot).__name__}. "
                f"Expected str/Path, PIL.Image.Image, or bytes."
            )

    def _take_screenshot(self, driver=None) -> str:
        """截图并返回临时文件路径。"""
        tmp_dir = self._cfg["screenshot"].get("tmp_dir") or tempfile.gettempdir()
        filename = f"rodski_vision_{int(time.time() * 1000)}.png"
        output_path = str(pathlib.Path(tmp_dir) / filename)

        if driver is not None:
            from .screenshot import capture_web
            capture_web(driver, output_path)
        else:
            from .screenshot import capture_desktop
            capture_desktop(output_path)

        logger.debug("Screenshot saved: %s", output_path)
        return output_path

    def _parse_screenshot(self, screenshot_path: str) -> list[dict]:
        """调用 OmniParser 解析截图，返回元素列表。"""
        client = self._get_omni_client()
        omni_cfg = self._cfg.get("omniparser", {})
        elements = client.parse(
            screenshot_path,
            box_threshold=omni_cfg.get("box_threshold", 0.18),
            iou_threshold=omni_cfg.get("iou_threshold", 0.7),
        )
        logger.debug("OmniParser returned %d element(s)", len(elements))
        return elements

    def _analyze(self, screenshot_path: str, elements: list[dict]) -> list[dict]:
        """调用 LLMAnalyzer 增强语义标签。"""
        analyzer = self._get_llm_analyzer()
        return analyzer.analyze(screenshot_path, elements)

    def _match_and_resolve_bbox(
        self,
        description: str,
        elements: list[dict],
        screenshot_path: str,
    ) -> Optional[Tuple[int, int, int, int]]:
        """语义匹配并将归一化 bbox 转换为像素坐标。"""
        matcher = self._get_matcher()
        min_conf = self._cfg.get("locator", {}).get("min_confidence", 0.6)

        candidates = matcher.match_all(description, elements)
        candidates = [c for c in candidates if c.get("confidence", 0) >= min_conf]
        if not candidates:
            logger.debug(
                "No element matched description %r (min_confidence=%s)",
                description, min_conf
            )
            return None

        best = candidates[0]
        bbox = best.get("bbox")
        if not bbox or len(bbox) != 4:
            logger.warning("Matched element has invalid bbox: %r", bbox)
            return None

        # bbox 可能是归一化值（0-1）或绝对像素值
        # OmniParser 返回归一化值
        from .coordinate_utils import normalized_to_pixel
        img_w, img_h = self._get_image_size(screenshot_path)
        cx, cy, x1, y1, x2, y2 = normalized_to_pixel(bbox, img_w, img_h)
        logger.debug(
            "Matched '%s' (conf=%.2f) -> bbox=%s -> (%d, %d, %d, %d)",
            description, best.get("confidence", 0), bbox, x1, y1, x2, y2,
        )
        return (x1, y1, x2, y2)

    @staticmethod
    def _get_image_size(image_path: str) -> Tuple[int, int]:
        """返回图像的 (width, height)，用于归一化坐标转换。"""
        try:
            with Image.open(image_path) as img:
                return img.size  # (width, height)
        except Exception:  # noqa: BLE001
            pass
        # Pillow 不可用时回退到 pyautogui 屏幕尺寸
        try:
            from .coordinate_utils import get_screen_size
            return get_screen_size()
        except Exception:  # noqa: BLE001
            pass
        # 最终兜底：返回 1920x1080
        logger.warning("Cannot determine image size; defaulting to 1920x1080")
        return 1920, 1080

    def _cleanup_tmp(self, screenshot_path: str) -> None:
        """删除临时截图文件（静默处理错误）。"""
        try:
            p = pathlib.Path(screenshot_path)
            if p.exists():
                p.unlink()
        except OSError as exc:
            logger.debug("Could not delete tmp screenshot %s: %s", screenshot_path, exc)

    # ------------------------------------------------------------------
    # Lazy component getters（旧 API 兼容）
    # ------------------------------------------------------------------

    def _get_omni_client(self):
        if self._omni_client is None:
            from .omni_client import OmniClient
            omni_cfg = self._cfg.get("omniparser", {})
            self._omni_client = OmniClient(
                url=omni_cfg.get("url", "http://14.103.175.167:7862/parse/"),
                timeout=omni_cfg.get("timeout", 5),
            )
        return self._omni_client

    def _get_llm_analyzer(self):
        if self._llm_analyzer is None:
            from .llm_analyzer import LLMAnalyzer
            self._llm_analyzer = LLMAnalyzer(
                config=self._cfg.get("llm"),
                global_vars=self._global_vars
            )
        return self._llm_analyzer

    def _get_matcher(self):
        if self._matcher is None:
            from .matcher import VisionMatcher
            self._matcher = VisionMatcher()
        return self._matcher

