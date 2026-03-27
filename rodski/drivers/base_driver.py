"""统一 UI 驱动接口基类

BaseDriver 只负责 UI 自动化操作。HTTP/API 操作由 RestHelper 独立处理，
通过 KeywordEngine 根据 model.xml 中 element 的 driver_type 路由到对应后端。
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseDriver(ABC):

    @abstractmethod
    def click(self, locator: str, **kwargs) -> bool:
        pass

    @abstractmethod
    def type(self, locator: str, text: str, **kwargs) -> bool:
        pass

    @abstractmethod
    def check(self, locator: str, **kwargs) -> bool:
        pass

    @abstractmethod
    def wait(self, seconds: float) -> None:
        pass

    @abstractmethod
    def navigate(self, url: str) -> bool:
        pass

    @abstractmethod
    def screenshot(self, path: str) -> bool:
        pass

    @abstractmethod
    def select(self, locator: str, value: str) -> bool:
        pass

    @abstractmethod
    def hover(self, locator: str) -> bool:
        pass

    @abstractmethod
    def drag(self, from_loc: str, to_loc: str) -> bool:
        pass

    @abstractmethod
    def scroll(self, x: int = 0, y: int = 300) -> bool:
        pass

    @abstractmethod
    def assert_element(self, locator: str, expected: str) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    # ── 扩展 UI 操作（非抽象，提供默认实现）─────────────────────

    def upload_file(self, locator: str, file_path: str) -> bool:
        return True

    def clear(self, locator: str) -> bool:
        return True

    def double_click(self, locator: str) -> bool:
        return True

    def right_click(self, locator: str) -> bool:
        return True

    def key_press(self, key: str) -> bool:
        return True

    def get_text(self, locator: str) -> Optional[str]:
        return ""

    # ── 桌面平台扩展（非抽象，子类可选覆盖）────────────────────

    def launch(self, app_path: str) -> bool:
        """启动桌面应用（Desktop 平台实现，Web/Mobile 返回 False）。"""
        return False

    def click_at(self, x: int, y: int) -> bool:
        """通过坐标点击（视觉定位后调用）。"""
        return False
