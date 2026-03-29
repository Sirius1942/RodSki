"""Vision module for RodSki — OmniParser client, coordinate utilities, screenshot tools, and LLM semantic layer."""

from .omni_client import OmniClient
from .coordinate_utils import (
    normalized_to_pixel,
    bbox_str_to_coords,
    get_screen_size,
    parse_bbox,
    calculate_center,
    normalize_to_pixel,
    pixel_to_normalize,
)
from .screenshot import capture_web, capture_desktop, auto_cleanup
from .llm_analyzer import LLMAnalyzer
from .matcher import VisionMatcher
from .locator import VisionLocator
from .bbox_locator import BBoxLocator
from .ocr_locator import OCRLocator
from .cache import VisionCache
from .exceptions import (
    VisionError,
    ElementNotFoundError,
    OmniParserError,
    LLMAnalysisError,
    CoordinateError,
    VisionTimeoutError,
    InvalidBBoxError,
)
from .screen_recorder import ScreenRecorder
from .ai_verifier import AIScreenshotVerifier, analyze_recording

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
    "ScreenRecorder",
    "AIScreenshotVerifier",
    "analyze_recording",
]
