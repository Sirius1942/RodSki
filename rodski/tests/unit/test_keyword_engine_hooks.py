"""KeywordEngine before_keyword/after_keyword 进程内回调测试（v8.2.0 Hooks 机制）"""
from unittest.mock import MagicMock

import pytest

from core.keyword_engine import KeywordEngine, HookDecision, HookResult
from core.exceptions import HookDeniedError


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.click.return_value = True
    driver.navigate.return_value = True
    driver.wait.return_value = None
    driver.close.return_value = None
    driver._is_closed = False
    return driver


@pytest.fixture
def engine(mock_driver):
    return KeywordEngine(mock_driver)


def test_before_keyword_allow_passes_through(engine):
    calls = []

    def hook(keyword, params):
        calls.append((keyword, params))
        return HookDecision(allow=True)

    engine.before_keyword_hooks.append(hook)
    result = engine.execute("wait", {"data": "0"})
    assert result is None or result is True or result is False  # wait 返回值不关键，重点是不抛异常
    assert calls == [("wait", {"data": "0"})]


def test_before_keyword_deny_raises_hook_denied_error(engine):
    def hook(keyword, params):
        return HookDecision(allow=False, reason="高危操作：DB 写入生产环境")

    engine.before_keyword_hooks.append(hook)
    with pytest.raises(HookDeniedError) as exc_info:
        engine.execute("wait", {"data": "0"})
    assert exc_info.value.event == "before_keyword"
    assert "高危操作" in exc_info.value.reason


def test_before_keyword_deny_does_not_call_driver(engine, mock_driver):
    def hook(keyword, params):
        return HookDecision(allow=False, reason="deny")

    engine.before_keyword_hooks.append(hook)
    with pytest.raises(HookDeniedError):
        engine.execute("navigate", {"data": "http://prod.example.com"})
    mock_driver.navigate.assert_not_called()


def test_before_keyword_hook_exception_does_not_block_execution(engine):
    def bad_hook(keyword, params):
        raise RuntimeError("hook 自身故障")

    engine.before_keyword_hooks.append(bad_hook)
    # hook 自身抛异常应仅 warning，不阻断关键字执行
    engine.execute("wait", {"data": "0"})


def test_after_keyword_called_on_success(engine):
    results = []

    def hook(keyword, params, hook_result):
        results.append((keyword, hook_result.status, hook_result.attempts))

    engine.after_keyword_hooks.append(hook)
    engine.execute("wait", {"data": "0"})
    assert len(results) == 1
    assert results[0][0] == "wait"
    assert results[0][1] == "ok"
    assert results[0][2] == 1


def test_after_keyword_called_on_failure(engine):
    results = []

    def hook(keyword, params, hook_result):
        results.append(hook_result.status)

    engine.after_keyword_hooks.append(hook)

    # 未知关键字在进入 try/finally 之前就直接抛出，不会经过 after_keyword（与
    # before_keyword 一样，都在关键字方法查找/校验阶段之前）。用已知关键字但
    # 参数非法（进入 try 块后由方法内部抛出不重试的异常）来触发 after_keyword
    # 的失败路径。
    with pytest.raises(Exception):
        engine.execute("get", {})  # get 缺少必需参数 data → InvalidParameterError
    assert results == ["error"]


def test_after_keyword_hook_exception_swallowed(engine):
    def bad_hook(keyword, params, hook_result):
        raise RuntimeError("after hook 故障")

    engine.after_keyword_hooks.append(bad_hook)
    # after hook 抛异常不应影响本次关键字调用的正常返回
    engine.execute("wait", {"data": "0"})


def test_hook_decision_and_result_basic_attrs():
    d = HookDecision(allow=False, reason="x")
    assert d.allow is False
    assert d.reason == "x"
    r = HookResult(status="ok", attempts=2, elapsed=0.5)
    assert r.status == "ok"
    assert r.attempts == 2
    assert r.elapsed == 0.5


def test_default_hooks_lists_empty(engine):
    assert engine.before_keyword_hooks == []
    assert engine.after_keyword_hooks == []
