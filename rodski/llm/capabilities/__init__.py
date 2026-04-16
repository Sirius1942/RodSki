"""LLM Capabilities — lazy imports to avoid requiring optional dependencies."""

__all__ = [
    'BaseCapability',
    'VisionLocatorCapability',
    'ScreenshotVerifierCapability',
    'TestReviewerCapability',
]

_LAZY_IMPORTS = {
    'BaseCapability': '.base',
    'VisionLocatorCapability': '.vision_locator',
    'ScreenshotVerifierCapability': '.screenshot_verifier',
    'TestReviewerCapability': '.test_reviewer',
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib
        mod = importlib.import_module(_LAZY_IMPORTS[name], __name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
