"""VisionLocator — 视觉定位器统一入口（v7.1.0 重构）。

通过 ``locate(locator_type, locator_value, screenshot)`` API 返回屏幕坐标边界框。

支持的定位器类型（通过 model.xml ``<location type="...">`` 定义）：

* ``vision``       — 截图 → PerceptionBackend.locate → 像素坐标边界框
                     （需要安装 rodski[perception] 或其他 backend，否则
                     抛 :py:class:`PerceptionUnavailableError`）
* ``vision_image`` — OpenCV 模板匹配（rodski 核心实现，无外部依赖）
                     在本类中以便利方法形式暴露；执行链路通常由
                     keyword_engine 直接调用 ``ImageTemplateMatcher``
* ``ocr``          — OCR 文字定位（需要 ``OCRLocator`` 注入 provider）
* ``vision_bbox``  — 直接解析坐标字符串（无依赖）

v7.1.0 变化
-----------
- 删除内置 OmniClient 依赖，``_locate_by_semantic`` 改走
  ``PerceptionRegistry.get_backend()``
- 删除已不存在的 ``ImageMatcher`` 符号引用；新代码请直接使用
  ``rodski.vision.image_matcher.ImageTemplateMatcher``
- ``ocr_locator`` 属性不再自动创建 OmniParser 客户端；未注入 provider 时
  调用会抛清晰错误
"""

from __future__ import annotations

import logging
import os
import pathlib
import tempfile
import time
import warnings
from typing import Any, Optional, Tuple

from PIL import Image

from .perception_interface import (
    PerceptionResult,
    PerceptionUnavailableError,
)
from .registry import PerceptionRegistry

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
    "screenshot": {
        "tmp_dir": "",   # 空字符串 → 使用系统临时目录
        "cleanup_max": 20,
    },
    "locator": {
        "min_confidence": 0.6,
        "images_dir": "images",
        "match_threshold": 0.85,
    },
    "cache": {
        "enabled": False,
        "ttl": 300,
    },
    "perception": {
        # PerceptionRegistry.get_backend() 透传的 kwargs。常用键：
        #   perception_backend: 显式 backend 名（"local" / "remote"）
        #   perception_model:   local backend 用的模型名
        #   ollama_host:        local backend 的 ollama 地址
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
            # v7.1.0 起 omniparser 段位被丢弃（OmniClient 已删除）
            raw.pop("omniparser", None)
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

    支持四种定位器类型：
        - vision: 自然语言描述 → PerceptionBackend.locate
        - vision_image: 参考图 → ImageTemplateMatcher（OpenCV）
        - ocr: 文字 → OCRLocator
        - vision_bbox: 字符串坐标 → BBoxLocator

    v7.1.0 起：``vision`` 走 ``PerceptionRegistry``；OmniClient 已删除。

    Args:
        config: 配置字典，可包含：
            - locator.match_threshold / images_dir
            - perception.perception_backend / perception_model / ollama_host
            - cache.enabled / ttl
        ocr_provider: 可选的 OCR provider（duck typed，需实现 ``parse``）。
        llm_analyzer: 仅 legacy 路径使用；新代码不再依赖 LLMAnalyzer。
        matcher: 仅 legacy 路径使用。
        cache: 预留缓存参数（当前不实现，保留接口）。
        global_vars: 全局变量字典（用于 ${var} 替换 / 配置注入）。
        omni_client: **已废弃**。v7.1.0 起 rodski 核心不再持有 OmniClient；
            若传入会被忽略并发 DeprecationWarning。
    """

    def __init__(
        self,
        config: dict | None = None,
        ocr_provider=None,
        llm_analyzer=None,
        matcher=None,
        cache=None,
        global_vars: dict | None = None,
        *,
        omni_client=None,
    ) -> None:
        self._cfg = _load_config(config)
        self._cache = cache  # reserved
        self._global_vars = global_vars

        # 延迟初始化：外部注入优先，否则按需创建
        self._llm_analyzer = llm_analyzer
        self._matcher = matcher
        self._ocr_provider = ocr_provider

        # v7.1.0 起 OmniClient 已删除
        if omni_client is not None:
            warnings.warn(
                "VisionLocator(omni_client=...) 已废弃（v7.1.0）。"
                "vision 定位现由 PerceptionBackend 提供，OmniClient 已删除。"
                "若需 OCR 能力，请改用 ocr_provider= 参数。",
                DeprecationWarning,
                stacklevel=2,
            )
            # 既有调用方传 MagicMock 等鸭子类型时仍可作为 OCR provider
            if self._ocr_provider is None:
                self._ocr_provider = omni_client
        # 兼容旧属性名
        self._omni_client = self._ocr_provider

        # 延迟加载的定位器
        self._image_matcher = None
        self._ocr_locator = None
        self._bbox_locator = None

        # 缓存的 perception backend（None = 尚未尝试获取；
        # PerceptionUnavailableError 实例 = 上次尝试失败）
        self._perception_backend = None

    # ------------------------------------------------------------------
    # 延迟加载属性
    # ------------------------------------------------------------------

    @property
    def image_matcher(self):
        """延迟加载 ImageTemplateMatcher（vision_image 定位器实现）。"""
        if self._image_matcher is None:
            from .image_matcher import ImageTemplateMatcher
            self._image_matcher = ImageTemplateMatcher(
                threshold=self._cfg.get("locator", {}).get("match_threshold", 0.85),
            )
        return self._image_matcher

    @property
    def ocr_locator(self):
        """延迟加载 OCRLocator（文字定位）。

        v7.1.0 起：构造时传入注入的 ``ocr_provider``。未注入 provider
        的实例在调用 ``locate_text`` 时会抛 ``RuntimeError`` 指引升级。
        """
        if self._ocr_locator is None:
            from .ocr_locator import OCRLocator
            self._ocr_locator = OCRLocator(provider=self._ocr_provider)
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
            locator_type: 定位器类型（vision / vision_image / ocr / vision_bbox）。
            locator_value: 定位器值。
            screenshot: 截图文件路径 / PIL Image / bytes。

        Returns:
            (x1, y1, x2, y2) 边界框，未找到返回 None。

        Raises:
            ValueError: 不支持的定位器类型。
            PerceptionUnavailableError: vision 定位但 backend 不可用。
        """
        if not locator_type or not locator_value:
            raise ValueError("locator_type and locator_value must not be empty")

        locator_type = locator_type.strip().lower()
        locator_value = locator_value.strip()

        if locator_type == "vision":
            return self._locate_by_vision(locator_value, screenshot)
        elif locator_type == "vision_image":
            return self._locate_by_vision_image(locator_value, screenshot)
        elif locator_type == "ocr":
            return self._locate_by_ocr(locator_value, screenshot)
        elif locator_type == "vision_bbox":
            return self._locate_by_bbox(locator_value)
        else:
            raise ValueError(
                f"Unsupported locator type: {locator_type!r}. "
                f"Expected 'vision', 'vision_image', 'ocr', or 'vision_bbox'."
            )

    # ------------------------------------------------------------------
    # 分发实现
    # ------------------------------------------------------------------

    def _locate_by_vision(
        self,
        description: str,
        screenshot,
    ) -> Optional[Tuple[int, int, int, int]]:
        """走 PerceptionBackend 的 VLM 语义定位。

        v7.1.0 起：完全通过 ``PerceptionRegistry`` 取 backend。未发现可用
        backend 时抛 :py:class:`PerceptionUnavailableError`（包含安装指引）。
        """
        if not description.strip():
            return None

        screenshot_path = self._get_screenshot_path(screenshot)
        backend = self._get_perception_backend()

        result = backend.locate(screenshot_path, description)
        if result is None:
            logger.debug(
                "perception backend %r 未定位到目标 %r",
                getattr(backend, "name", "?"), description,
            )
            return None
        return result.bbox

    def _locate_by_vision_image(
        self,
        template_value: str,
        screenshot,
    ) -> Optional[Tuple[int, int, int, int]]:
        """图片模板匹配（OpenCV）。"""
        from .image_matcher import resolve_template_path
        screenshot_path = self._get_screenshot_path(screenshot)
        template_path = resolve_template_path(
            template_value,
            model_dir=None,  # VisionLocator 不感知 model 目录；调用方应传绝对路径或在
                            # global_vars 中提供基目录
            global_vars=self._global_vars,
        )
        return self.image_matcher.locate(screenshot_path, template_path)

    def _locate_by_ocr(
        self,
        text: str,
        screenshot
    ) -> Optional[Tuple[int, int, int, int]]:
        """OCR 文字定位（需要 ocr_provider 已注入）。"""
        return self.ocr_locator.locate_text(text, screenshot)

    def _locate_by_bbox(self, bbox_str: str) -> Tuple[int, int, int, int]:
        """坐标定位。"""
        return self.bbox_locator.locate(bbox_str)

    # ------------------------------------------------------------------
    # PerceptionBackend 访问
    # ------------------------------------------------------------------

    def _get_perception_backend(self):
        """获取 perception backend 实例（带缓存）。

        多次调用复用同一实例；上次失败的情况下每次都重新尝试 discover
        （生产场景里第一次失败后通常不会奇迹般恢复，但测试可通过
        ``PerceptionRegistry.reset()`` 让状态变化生效）。
        """
        if isinstance(self._perception_backend, PerceptionUnavailableError):
            raise self._perception_backend
        if self._perception_backend is not None:
            return self._perception_backend

        # 组装 backend 构造参数：merge perception section + global_vars 中的
        # 相关键 + 环境变量（后者由 Registry 处理）
        perception_cfg = dict(self._cfg.get("perception", {}) or {})
        for key in (
            "perception_backend", "perception_model",
            "ollama_host", "perception_server",
        ):
            if self._global_vars and key in self._global_vars and key not in perception_cfg:
                perception_cfg[key] = self._global_vars[key]

        try:
            backend = PerceptionRegistry.get_backend(perception_cfg)
        except PerceptionUnavailableError as exc:
            self._perception_backend = exc
            raise
        self._perception_backend = backend
        return backend

    # ------------------------------------------------------------------
    # Legacy API - 已废弃，请使用 locate(type, value, screenshot)
    # ------------------------------------------------------------------

    def is_vision_locator(self, locator_str: str) -> bool:
        """判断字符串是否是视觉定位器（vision:/ocr:/vision_bbox: 前缀）。

        .. deprecated:: v5.4.0
            请使用 ``ModelParser.is_vision_locator(type_str)`` 替代。
        """
        warnings.warn(
            "VisionLocator.is_vision_locator() 已废弃，请使用 ModelParser.is_vision_locator(type_str)",
            DeprecationWarning,
            stacklevel=2,
        )
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

        .. deprecated:: v5.4.0
            请使用 ``locate(locator_type, locator_value, screenshot)`` 替代。
        """
        warnings.warn(
            "locate_legacy() 已废弃，请使用 locate(locator_type, locator_value, screenshot)",
            DeprecationWarning,
            stacklevel=2,
        )
        s = locator_str.strip() if locator_str else ""
        if not s:
            raise ValueError("locator_str must not be empty")

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

    def locate_with_driver(self, locator_str: str, driver=None) -> Tuple[int, int]:
        """已废弃别名，等价于 ``locate_legacy``。"""
        return self.locate_legacy(locator_str, driver)

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _get_screenshot_path(self, screenshot) -> str:
        """将截图输入转换为文件路径。"""
        if isinstance(screenshot, (str, pathlib.Path)):
            return str(screenshot)
        elif isinstance(screenshot, Image.Image):
            tmp_dir = self._cfg["screenshot"].get("tmp_dir") or tempfile.gettempdir()
            filename = f"rodski_vision_{int(time.time() * 1000)}.png"
            output_path = str(pathlib.Path(tmp_dir) / filename)
            screenshot.save(output_path, format="PNG")
            return output_path
        elif isinstance(screenshot, bytes):
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

    @staticmethod
    def _get_image_size(image_path: str) -> Tuple[int, int]:
        """返回图像的 (width, height)。"""
        try:
            with Image.open(image_path) as img:
                return img.size  # (width, height)
        except Exception:  # noqa: BLE001
            pass
        try:
            from .coordinate_utils import get_screen_size
            return get_screen_size()
        except Exception:  # noqa: BLE001
            pass
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
