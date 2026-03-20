"""Windows 自动化驱动 (pywinauto)"""
import time
from .base_driver import BaseDriver


class PywinautoDriver(BaseDriver):
    def __init__(self, app_path: str = None):
        try:
            from pywinauto import Application
            self.app = Application().connect(path=app_path) if app_path else None
        except ImportError:
            raise ImportError("pywinauto not installed")

    def click(self, locator: str, **kwargs) -> bool:
        try:
            self.app.window(title=locator).click()
            return True
        except Exception:
            return False

    def type(self, locator: str, text: str, **kwargs) -> bool:
        try:
            self.app.window(title=locator).type_keys(text)
            return True
        except Exception:
            return False

    def check(self, locator: str, **kwargs) -> bool:
        try:
            return self.app.window(title=locator).exists()
        except Exception:
            return False

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def navigate(self, url: str) -> bool:
        return False

    def screenshot(self, path: str) -> bool:
        try:
            self.app.top_window().capture_as_image().save(path)
            return True
        except Exception:
            return False

    def select(self, locator: str, value: str) -> bool:
        try:
            self.app.window(title=locator).select(value)
            return True
        except Exception:
            return False

    def hover(self, locator: str) -> bool:
        return False

    def drag(self, from_loc: str, to_loc: str) -> bool:
        return False

    def scroll(self, x: int = 0, y: int = 300) -> bool:
        return False

    def assert_element(self, locator: str, expected: str) -> bool:
        try:
            text = self.app.window(title=locator).window_text()
            return expected in text
        except Exception:
            return False

    def close(self) -> None:
        if self.app:
            self.app.kill()
