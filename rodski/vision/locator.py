"""VisionLocator — 统一视觉定位入口。

解析 model.xml 中 element 的 ``locator`` 属性，返回屏幕坐标 ``(cx, cy)``。

支持两种格式：

* ``vision:<描述>``    — 截图 → OmniParser → LLM 语义分析 → 匹配 → 坐标
* ``vision_bbox:x1,y1,x2,y2`` — 直接计算中心坐标，无需 AI 调用

依赖 vision_config.yaml（位于 rodski/config/），缺失时使用内置默认值。
"""

from __future__ import annotations

import logging
import os
import pathlib
import tempfile
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_PREFIX_VISION = "vision:"
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
    """统一视觉定位入口，解析 locator 属性并返回坐标。

    Args:
        omni_client: OmniClient 实例；为 None 时按配置自动创建。
        llm_analyzer: LLMAnalyzer 实例；为 None 时按配置自动创建。
        matcher: VisionMatcher 实例；为 None 时自动创建。
        config: 覆盖 vision_config.yaml 的额外配置字典。
        cache: 预留缓存参数（当前不实现，保留接口）。
    """

    def __init__(
        self,
        omni_client=None,
        llm_analyzer=None,
        matcher=None,
        config: dict | None = None,
        cache=None,  # 预留接口，暂不实现
        global_vars: dict | None = None,  # 全局变量
    ) -> None:
        self._cfg = _load_config(config)
        self._cache = cache  # reserved
        self._global_vars = global_vars

        # 延迟初始化：外部注入优先，否则按需创建
        self._omni_client = omni_client
        self._llm_analyzer = llm_analyzer
        self._matcher = matcher

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_vision_locator(self, locator_str: str) -> bool:
        """判断字符串是否是视觉定位器（vision: 或 vision_bbox: 前缀）。"""
        if not locator_str:
            return False
        s = locator_str.strip()
        return s.startswith(_PREFIX_VISION) or s.startswith(_PREFIX_BBOX)

    def locate(self, locator_str: str, driver=None) -> tuple[int, int]:
        """解析 locator 字符串，返回 (cx, cy) 中心坐标。

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

        if s.startswith(_PREFIX_BBOX):
            return self._locate_bbox(s[len(_PREFIX_BBOX):])

        if s.startswith(_PREFIX_VISION):
            return self._locate_vision(s[len(_PREFIX_VISION):], driver)

        raise ValueError(
            f"Unsupported locator format: {locator_str!r}. "
            f"Expected 'vision:<desc>' or 'vision_bbox:x1,y1,x2,y2'."
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _locate_bbox(self, bbox_str: str) -> tuple[int, int]:
        """vision_bbox 分支：直接解析坐标字符串并返回中心点。"""
        from vision.coordinate_utils import bbox_str_to_coords
        cx, cy = bbox_str_to_coords(bbox_str)
        logger.debug("vision_bbox resolved to (%d, %d)", cx, cy)
        return cx, cy

    def _locate_vision(self, description: str, driver=None) -> tuple[int, int]:
        """vision 分支：截图 → OmniParser → LLM → 匹配 → 坐标。"""
        if not description.strip():
            raise ValueError("vision locator description must not be empty")

        screenshot_path = self._take_screenshot(driver)
        try:
            elements = self._parse_screenshot(screenshot_path)
            elements = self._analyze(screenshot_path, elements)
            cx, cy = self._match_and_resolve(description, elements, screenshot_path)
        finally:
            self._cleanup_tmp(screenshot_path)

        return cx, cy

    def _take_screenshot(self, driver=None) -> str:
        """截图并返回临时文件路径。"""
        tmp_dir = self._cfg["screenshot"].get("tmp_dir") or tempfile.gettempdir()
        filename = f"rodski_vision_{int(time.time() * 1000)}.png"
        output_path = str(pathlib.Path(tmp_dir) / filename)

        if driver is not None:
            from vision.screenshot import capture_web
            capture_web(driver, output_path)
        else:
            from vision.screenshot import capture_desktop
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

    def _match_and_resolve(
        self,
        description: str,
        elements: list[dict],
        screenshot_path: str,
    ) -> tuple[int, int]:
        """语义匹配并将归一化 bbox 转换为像素坐标。"""
        matcher = self._get_matcher()
        min_conf = self._cfg.get("locator", {}).get("min_confidence", 0.6)

        candidates = matcher.match_all(description, elements)
        candidates = [c for c in candidates if c.get("confidence", 0) >= min_conf]
        if not candidates:
            raise RuntimeError(
                f"No element matched description {description!r} "
                f"(min_confidence={min_conf})"
            )

        best = candidates[0]
        bbox = best.get("bbox")
        if not bbox or len(bbox) != 4:
            raise RuntimeError(
                f"Matched element has invalid bbox: {bbox!r}"
            )

        # bbox 可能是归一化值（0-1）或绝对像素值
        # OmniParser 返回归一化值；若已是像素值则转换结果相同（当 w=h=1）
        from vision.coordinate_utils import normalized_to_pixel
        img_w, img_h = self._get_image_size(screenshot_path)
        cx, cy, *_ = normalized_to_pixel(bbox, img_w, img_h)
        logger.debug(
            "Matched '%s' (conf=%.2f) -> bbox=%s -> (%d, %d)",
            description, best.get("confidence", 0), bbox, cx, cy,
        )
        return cx, cy

    @staticmethod
    def _get_image_size(image_path: str) -> tuple[int, int]:
        """返回图像的 (width, height)，用于归一化坐标转换。"""
        try:
            from PIL import Image  # type: ignore[import]
            with Image.open(image_path) as img:
                return img.size  # (width, height)
        except ImportError:
            pass
        # Pillow 不可用时回退到 pyautogui 屏幕尺寸
        try:
            from vision.coordinate_utils import get_screen_size
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
    # Lazy component getters
    # ------------------------------------------------------------------

    def _get_omni_client(self):
        if self._omni_client is None:
            from vision.omni_client import OmniClient
            omni_cfg = self._cfg.get("omniparser", {})
            self._omni_client = OmniClient(
                url=omni_cfg.get("url", "http://14.103.175.167:7862/parse/"),
                timeout=omni_cfg.get("timeout", 5),
            )
        return self._omni_client

    def _get_llm_analyzer(self):
        if self._llm_analyzer is None:
            from vision.llm_analyzer import LLMAnalyzer
            self._llm_analyzer = LLMAnalyzer(
                config=self._cfg.get("llm"),
                global_vars=self._global_vars
            )
        return self._llm_analyzer

    def _get_matcher(self):
        if self._matcher is None:
            from vision.matcher import VisionMatcher
            self._matcher = VisionMatcher()
        return self._matcher

