"""Windows 自动化驱动 (pywinauto)"""
import time
from typing import Optional, Tuple
from .base_driver import BaseDriver


class PywinautoDriver(BaseDriver):
    def __init__(self, app_path: str = None):
        try:
            from pywinauto import Application
            self.app = Application().connect(path=app_path) if app_path else None
        except ImportError:
            raise ImportError("pywinauto not installed")

    def launch(self, **kwargs) -> None:
        """启动应用"""
        pass

    def close(self) -> None:
        if self.app:
            self.app.kill()

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素"""
        return None

    def click(self, x: int, y: int) -> None:
        """点击坐标"""
        import pyautogui
        pyautogui.click(x, y)

    def type_text(self, x: int, y: int, text: str) -> None:
        """输入文字"""
        import pyautogui
        pyautogui.click(x, y)
        pyautogui.typewrite(text)

    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """获取文字"""
        return ""

    def take_screenshot(self) -> str:
        """截图"""
        import tempfile
        path = tempfile.mktemp(suffix='.png')
        try:
            self.app.top_window().capture_as_image().save(path)
            return path
        except Exception:
            return ""

    def double_click(self, x: int, y: int) -> None:
        """双击"""
        import pyautogui
        pyautogui.doubleClick(x, y)

    def right_click(self, x: int, y: int) -> None:
        """右键点击"""
        import pyautogui
        pyautogui.rightClick(x, y)

    def hover(self, x: int, y: int) -> None:
        """悬停"""
        import pyautogui
        pyautogui.moveTo(x, y)

    def scroll(self, x: int, y: int) -> None:
        """滚动"""
        import pyautogui
        clicks = -int(y / 120)
        pyautogui.scroll(clicks)
