"""统一驱动接口基类 - 支持23种操作关键字"""
from abc import ABC, abstractmethod
from typing import Any, Optional


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

    # ── New: HTTP methods ─────────────────────────────────────────

    def http_get(self, url: str, headers: Optional[dict] = None) -> Any:
        return True

    def http_post(self, url: str, body: Any = None, headers: Optional[dict] = None) -> Any:
        return True

    def http_put(self, url: str, body: Any = None, headers: Optional[dict] = None) -> Any:
        return True

    def http_delete(self, url: str, headers: Optional[dict] = None) -> Any:
        return True

    # ── New: UI interaction methods ───────────────────────────────

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

    def get_supported_keywords(self) -> list:
        return [
            "click", "type", "check", "wait", "navigate",
            "screenshot", "select", "hover", "drag", "scroll", "assert",
            "http_get", "http_post", "http_put", "http_delete",
            "assert_json", "assert_status",
            "upload_file", "clear", "double_click", "right_click",
            "key_press", "get_text",
        ]
