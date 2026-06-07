"""单元测试 — LoadDriver"""
from __future__ import annotations
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import pytest

# ---------------------------------------------------------------------------
# 由于 LoadDriver.__init__ 跳过了 BaseDriver.__init__（不调用 super().__init__），
# 无需 mock ConfigManager / Logger。直接导入即可。
# ---------------------------------------------------------------------------
from rodski.drivers.load_driver import LoadDriver
from rodski.core.exceptions import LoadModeUnsupportedError


# ── helpers ──────────────────────────────────────────────────────────────────

class _FakeResponse:
    """模拟 Locust catch_response context manager 返回的响应对象。"""

    def __init__(self, status_code: int = 200, body: dict | None = None, fail_exc=None):
        self.status_code = status_code
        self._body = body or {}
        self._fail_exc = fail_exc
        self._failure_reason: str | None = None

    def json(self):
        return self._body

    def failure(self, reason: str):
        self._failure_reason = reason

    # context manager protocol
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _make_driver(status_code: int = 200, body: dict | None = None) -> tuple[LoadDriver, _FakeResponse]:
    """返回 (driver, fake_resp)，fake_resp 是 catch_response 返回的响应对象。"""
    fake_resp = _FakeResponse(status_code=status_code, body=body or {"msg": "ok"})

    client = MagicMock()
    client.request.return_value = fake_resp

    driver = LoadDriver(locust_client=client, host="http://example.com")
    return driver, fake_resp


# ── http_request ─────────────────────────────────────────────────────────────

class TestHttpRequest:
    def test_returns_status_and_body(self):
        driver, _ = _make_driver(status_code=200, body={"id": 42})
        result = driver.http_request("GET", "/api/items")
        assert result["status"] == 200
        assert result["id"] == 42

    def test_last_response_updated(self):
        driver, _ = _make_driver(status_code=201, body={"created": True})
        driver.http_request("POST", "/api/create")
        assert driver.get_last_response() == {"status": 201, "created": True}

    def test_non_json_body_returns_status_only(self):
        fake_resp = _FakeResponse(status_code=204, body=None)
        fake_resp.json = MagicMock(side_effect=ValueError("no json"))
        client = MagicMock()
        client.request.return_value = fake_resp

        driver = LoadDriver(locust_client=client)
        result = driver.http_request("DELETE", "/api/item/1")
        assert result == {"status": 204}

    def test_passes_headers_and_params(self):
        driver, _ = _make_driver()
        driver.http_request(
            "GET", "/search",
            headers={"Authorization": "Bearer tok"},
            params={"q": "test"},
            name="search-req",
        )
        call_kwargs = driver._client.request.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer tok"}
        assert call_kwargs.kwargs["params"] == {"q": "test"}
        assert call_kwargs.kwargs["name"] == "search-req"

    def test_default_name_falls_back_to_url(self):
        driver, _ = _make_driver()
        driver.http_request("GET", "/fallback")
        assert driver._client.request.call_args.kwargs["name"] == "/fallback"


# ── mark_request_failure ──────────────────────────────────────────────────────

class TestMarkRequestFailure:
    def test_calls_locust_failure(self):
        driver, fake_resp = _make_driver()
        driver.http_request("GET", "/api")          # sets _current_response_ctx
        driver.mark_request_failure("assert failed")
        assert fake_resp._failure_reason == "assert failed"

    def test_no_ctx_does_not_raise(self):
        driver, _ = _make_driver()
        # _current_response_ctx 尚未设置
        driver.mark_request_failure("early call")   # must not raise

    def test_failure_method_raises_silently(self):
        """failure() 本身抛异常时，mark_request_failure 应静默吞掉。"""
        fake_resp = _FakeResponse()
        fake_resp.failure = MagicMock(side_effect=RuntimeError("boom"))
        client = MagicMock()
        client.request.return_value = fake_resp

        driver = LoadDriver(locust_client=client)
        driver.http_request("GET", "/api")
        driver.mark_request_failure("reason")       # must not raise


# ── UI 方法抛 LoadModeUnsupportedError ────────────────────────────────────────

UI_METHODS = [
    ("click",         (0, 0),                {}),
    ("double_click",  (0, 0),                {}),
    ("right_click",   (0, 0),                {}),
    ("hover",         (0, 0),                {}),
    ("scroll",        (0, 0),                {}),
    ("type_text",     (0, 0, "hi"),          {}),
    ("navigate",      ("http://x",),         {}),
    ("launch",        (),                    {}),
    ("select",        (None, "val"),         {}),
    ("key_press",     ("Enter",),            {}),
    ("upload_file",   (None, "/path"),       {}),
    ("clear",         (None,),               {}),
    ("get_text",      (0, 0, 10, 10),        {}),
    ("assert_element",(),                    {}),
    ("evaluate",      (),                    {}),
    ("locate_element",("id", "foo"),         {}),
]


@pytest.mark.parametrize("method,args,kwargs", UI_METHODS)
def test_ui_method_raises(method, args, kwargs):
    driver, _ = _make_driver()
    with pytest.raises(LoadModeUnsupportedError) as exc_info:
        getattr(driver, method)(*args, **kwargs)
    assert method in exc_info.value.method_name


# ── screenshot / close / wait 不抛异常 ───────────────────────────────────────

class TestNoOpMethods:
    def test_screenshot_returns_none(self):
        driver, _ = _make_driver()
        result = driver.screenshot()
        assert result is None

    def test_screenshot_with_path_returns_none(self):
        driver, _ = _make_driver()
        result = driver.screenshot(path="/tmp/shot.png")
        assert result is None

    def test_close_does_not_raise(self):
        driver, _ = _make_driver()
        driver.close()  # no exception

    def test_wait_does_not_raise(self):
        driver, _ = _make_driver()
        driver.wait(seconds=1)  # no exception

    def test_take_screenshot_returns_empty_string(self):
        driver, _ = _make_driver()
        result = driver.take_screenshot()
        assert result == ""


# ── error_code ────────────────────────────────────────────────────────────────

def test_load_mode_unsupported_error_code():
    err = LoadModeUnsupportedError("click")
    assert err.error_code == "SKI601"
    assert "click" in str(err)


def test_load_mode_unsupported_error_no_method():
    err = LoadModeUnsupportedError()
    assert "UI 操作" in str(err)
