"""LoadDriver — 压测专用驱动，继承 BaseDriver，只支持接口场景。
内部通过 Locust FastHttpUser.client 发送请求，由 Locust 统一计时与错误统计。
每个 VU（RodskiLoadUser 实例）持有独立的 LoadDriver 实例。
"""
from __future__ import annotations
from typing import Any, Optional, Tuple

try:
    from .base_driver import BaseDriver
    from ..core.exceptions import LoadModeUnsupportedError
except ImportError:
    from drivers.base_driver import BaseDriver
    from core.exceptions import LoadModeUnsupportedError


class LoadDriver(BaseDriver):
    # 专属标记：keyword_engine 用此区分压测驱动，避免 hasattr('http_request') 误判 MagicMock
    _is_load_driver: bool = True

    def __init__(self, locust_client: Any, host: str = ""):
        self._client = locust_client
        self._host = host
        self._last_response: Optional[dict] = None
        self._current_response_ctx = None  # Locust catch_response context

    # ── 接口操作（支持）──────────────────────────────────────────────────────

    def http_request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[dict] = None,
        json: Any = None,
        params: Optional[dict] = None,
        name: Optional[str] = None,
    ) -> dict:
        """由 KeywordEngine._kw_send() 调用。
        通过 Locust FastHttpClient 发送请求，自动计时并统计到 env.stats。
        返回格式与 InterfaceDriver 一致：{"status": 200, ...响应体字段}
        """
        with self._client.request(
            method=method,
            url=url,
            headers=headers or {},
            json=json,
            params=params,
            name=name or url,
            catch_response=True,
        ) as resp:
            self._current_response_ctx = resp
            try:
                body = resp.json()
            except Exception:
                body = {}
            result = {"status": resp.status_code, **body}
            self._last_response = result
            return result

    def get_last_response(self) -> Optional[dict]:
        return self._last_response

    def mark_request_failure(self, reason: str) -> None:
        """verify 失败时由 KeywordEngine 调用，通知 Locust 标记为失败请求。"""
        if self._current_response_ctx is not None:
            try:
                self._current_response_ctx.failure(reason)
            except Exception:
                pass

    # ── UI 操作（不支持）────────────────────────────────────────────────────

    def _ui_not_supported(self, method_name: str) -> None:
        raise LoadModeUnsupportedError(method_name)

    def click(self, x: int, y: int) -> None:              self._ui_not_supported("click")
    def double_click(self, x: int, y: int) -> None:       self._ui_not_supported("double_click")
    def right_click(self, x: int, y: int) -> None:        self._ui_not_supported("right_click")
    def hover(self, x: int, y: int) -> None:              self._ui_not_supported("hover")
    def drag(self, from_loc: Any, to_loc: Any, **kw):     self._ui_not_supported("drag")
    def scroll(self, x: int, y: int) -> None:             self._ui_not_supported("scroll")
    def type_text(self, x: int, y: int, text: str) -> None: self._ui_not_supported("type_text")
    def navigate(self, url: str, **kwargs):               self._ui_not_supported("navigate")
    def launch(self, **kwargs) -> None:                   self._ui_not_supported("launch")
    def select(self, locator: Any, value: Any, **kw):     self._ui_not_supported("select")
    def key_press(self, *args, **kwargs):                 self._ui_not_supported("key_press")
    def upload_file(self, locator: Any, path: Any, **kw): self._ui_not_supported("upload_file")
    def clear(self, locator: Any, **kwargs):              self._ui_not_supported("clear")
    def get_text(self, x1: int, y1: int, x2: int, y2: int) -> str: self._ui_not_supported("get_text")
    def assert_element(self, *args, **kwargs):            self._ui_not_supported("assert_element")
    def evaluate(self, *args, **kwargs):                  self._ui_not_supported("evaluate")

    def screenshot(self, path: Any = None, **kwargs):     return None  # 压测时跳过截图
    def close(self) -> None:                              pass          # 压测不需要关闭浏览器
    def wait(self, seconds: float = 0, **kwargs) -> None: pass          # 压测忽略显式等待

    # ── 抽象方法最小实现（BaseDriver 要求）──────────────────────────────────

    def locate_element(
        self,
        locator_type: str,
        locator_value: str,
    ) -> Optional[Tuple[int, int, int, int]]:
        self._ui_not_supported("locate_element")

    def take_screenshot(self) -> str:
        return ""  # 压测时不截图，返回空路径
