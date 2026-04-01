"""视觉断言模块 - 支持图片和视频帧的视觉匹配"""
from core.assertion.base_assertion import BaseAssertion
from core.assertion.image_matcher import ImageMatcher
from core.assertion.video_analyzer import VideoAnalyzer

__all__ = ["BaseAssertion", "ImageMatcher", "VideoAnalyzer"]
