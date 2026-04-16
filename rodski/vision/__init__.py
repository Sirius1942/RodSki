"""Vision module for RodSki — lazy imports to avoid requiring optional dependencies."""

__all__ = [
    "OmniClient",
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
    "LLMAnalyzer",
    "VisionMatcher",
    "VisionLocator",
    "BBoxLocator",
    "OCRLocator",
    "VisionCache",
    "VisionError",
    "ElementNotFoundError",
    "OmniParserError",
    "LLMAnalysisError",
    "CoordinateError",
    "VisionTimeoutError",
    "InvalidBBoxError",
]

_MODULE_MAP = {
    "OmniClient": ".omni_client",
    "LLMAnalyzer": ".llm_analyzer",
    "VisionMatcher": ".matcher",
    "VisionLocator": ".locator",
    "BBoxLocator": ".bbox_locator",
    "OCRLocator": ".ocr_locator",
    "VisionCache": ".cache",
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
