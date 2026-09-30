"""Windows 自动化驱动 (pywinauto)"""
import time
import logging
from typing import Optional, Tuple
from .base_driver import BaseDriver

logger = logging.getLogger("rodski")


class PywinautoDriver(BaseDriver):
    def __init__(self, app_path: str = None):
        logger.info(f"初始化 Pywinauto 驱动: app_path={app_path}")
        try:
            from pywinauto import Application
            self.app = Application().connect(path=app_path) if app_path else None
            logger.info("Pywinauto 驱动初始化成功")
        except ImportError as e:
            logger.error(f"pywinauto 未安装: {e}")
            raise ImportError("pywinauto not installed")

    def launch(self, **kwargs) -> None:
        """启动应用"""
        pass

    def close(self) -> None:
        if self.app:
            self.app.kill()

    # v11.7.0: 控件定位尚未实现。显式报"不支持"而不是静默返回 None——否则自动等待会把
    # "驱动没实现"当成"控件暂未出现"，白白等满 AutoWait 后才给出含糊的超时错误。
    _NOT_IMPLEMENTED = ("PywinautoDriver 尚未实现控件定位（Windows 原生控件）；"
                        "请在模型中使用视觉定位器（vision / ocr / vision_bbox），由 DesktopDriver 执行")

    def locate_element(self, locator_type: str, locator_value: str) -> Optional[Tuple[int, int, int, int]]:
        """定位元素（未实现）"""
        raise NotImplementedError(self._NOT_IMPLEMENTED)

    def probe(self, locator: str, frame: Optional[str] = None) -> bool:
        raise NotImplementedError(self._NOT_IMPLEMENTED)

    def click_locator(self, locator: str, **kwargs) -> bool:
        raise NotImplementedError(self._NOT_IMPLEMENTED)

    def type_locator(self, locator: str, text: str, **kwargs) -> bool:
        raise NotImplementedError(self._NOT_IMPLEMENTED)

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
        """获取文字（未实现）"""
        raise NotImplementedError("PywinautoDriver 尚未实现区域文字读取")

    def take_screenshot(self) -> str:
        """截图"""
        import tempfile
        path = tempfile.mktemp(suffix='.png')
        try:
            self.app.top_window().capture_as_image().save(path)
            logger.debug(f"截图成功: {path}")
            return path
        except Exception as e:
            logger.error(f"截图失败: {e}")
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
