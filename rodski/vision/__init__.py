"""Vision module for RodSki — lazy imports to avoid requiring optional dependencies.

v7.1.0
------
OmniClient 已删除。perception (VLM 语义定位) 通过 ``PerceptionRegistry``
+ entry_points 插件机制提供，由独立的 ``rodski-perception`` 包实现。
仅核心安装的环境下：

- ``vision_image`` (``ImageTemplateMatcher``) 正常可用
- ``vision_bbox`` (``BBoxLocator``) 正常可用
- ``ocr`` (``OCRLocator``) 需要注入 OCR provider；默认无 provider 时调用
  会抛清晰错误
- ``vision`` (VLM 语义定位) 抛 ``PerceptionUnavailableError`` 提示安装
  ``pip install rodski[perception]``
"""

__all__ = [
    # 坐标 / 截图工具
    "normalized_to_pixel",
    "bbox_str_to_coords",
    "get_screen_size",
    "parse_bbox",
    "calculate_center",
    "normalize_to_pixel",
    "pixel_to_normalize",
    "capture_web",
    "capture_desktop",
    "auto_cleanup",
    # 子模块入口
    "LLMAnalyzer",
    "VisionMatcher",
    "VisionLocator",
    "BBoxLocator",
    "OCRLocator",
    "VisionCache",
    "ImageTemplateMatcher",
    # perception 抽象 + Registry (v7.1.0)
    "PerceptionBackend",
    "PerceptionResult",
    "PerceptionUnavailableError",
    "LocatorHint",
    "PerceptionRegistry",
    # 异常
    "VisionError",
    "ElementNotFoundError",
    "OmniParserError",  # v7.1.0 起 deprecated，保留给历史代码
    "LLMAnalysisError",
    "CoordinateError",
    "VisionTimeoutError",
    "InvalidBBoxError",
]

_MODULE_MAP = {
    "LLMAnalyzer": ".llm_analyzer",
    "VisionMatcher": ".matcher",
    "VisionLocator": ".locator",
    "BBoxLocator": ".bbox_locator",
    "OCRLocator": ".ocr_locator",
    "VisionCache": ".cache",
    "ImageTemplateMatcher": ".image_matcher",
}

_PERCEPTION_ATTRS = {
    "PerceptionBackend": ".perception_interface",
    "PerceptionResult": ".perception_interface",
    "PerceptionUnavailableError": ".perception_interface",
    "LocatorHint": ".perception_interface",
    "PerceptionRegistry": ".registry",
}

_COORD_ATTRS = {
    "normalized_to_pixel", "bbox_str_to_coords", "get_screen_size",
    "parse_bbox", "calculate_center", "normalize_to_pixel", "pixel_to_normalize",
}

_SCREENSHOT_ATTRS = {"capture_web", "capture_desktop", "auto_cleanup"}

_EXCEPTION_ATTRS = {
    "VisionError", "ElementNotFoundError", "OmniParserError",
    "LLMAnalysisError", "CoordinateError", "VisionTimeoutError", "InvalidBBoxError",
}


def __getattr__(name):
    import importlib
    if name in _MODULE_MAP:
        mod = importlib.import_module(_MODULE_MAP[name], __name__)
        return getattr(mod, name)
    if name in _PERCEPTION_ATTRS:
        mod = importlib.import_module(_PERCEPTION_ATTRS[name], __name__)
        return getattr(mod, name)
    if name in _COORD_ATTRS:
        from . import coordinate_utils
        return getattr(coordinate_utils, name)
    if name in _SCREENSHOT_ATTRS:
        from . import screenshot
        return getattr(screenshot, name)
    if name in _EXCEPTION_ATTRS:
        from . import exceptions
        return getattr(exceptions, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
