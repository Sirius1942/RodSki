"""视觉断言模块 — lazy imports to avoid requiring cv2 at import time."""

__all__ = ["BaseAssertion", "ImageMatcher", "VideoAnalyzer"]


def __getattr__(name):
    if name == 'BaseAssertion':
        from .base_assertion import BaseAssertion
        return BaseAssertion
    if name == 'ImageMatcher':
        from .image_matcher import ImageMatcher
        return ImageMatcher
    if name == 'VideoAnalyzer':
        from .video_analyzer import VideoAnalyzer
        return VideoAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
