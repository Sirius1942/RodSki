"""Unit tests for design/debugger.py"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from rodski_agent.design.debugger import analyze_failure, _fallback_hints


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_bridge(llm_response: str = None, screenshot_answer: str = "页面正常", raise_llm: bool = False):
    bridge = MagicMock()
    bridge.analyze_screenshot.return_value = {"answer": screenshot_answer, "confidence": 0.8}
    if raise_llm:
        bridge.call_llm_text.side_effect = Exception("LLM unavailable")
    else:
        bridge.call_llm_text.return_value = llm_response or json.dumps([
            {"type": "model", "description": "locator 失效", "suggestion": "更新 CSS 选择器"}
        ])
    return bridge


def _make_report(cases=None, error=""):
    return {
        "total": len(cases or []),
        "passed": 0,
        "failed": len(cases or []),
        "cases": cases or [],
        "error": error,
    }


# ---------------------------------------------------------------------------
# Tests: hints format
# ---------------------------------------------------------------------------

def test_returns_hint_list_with_correct_keys():
    bridge = _make_bridge()
    report = _make_report(cases=[{"id": "TC01", "status": "fail", "error": "timeout waiting for element"}])
    hints = analyze_failure(report, [], bridge)
    assert isinstance(hints, list)
    assert len(hints) > 0
    for h in hints:
        assert "type" in h
        assert "description" in h
        assert "suggestion" in h
        assert h["type"] in ("model", "case", "data")


def test_hint_type_values_are_valid():
    bridge = _make_bridge(llm_response=json.dumps([
        {"type": "data", "description": "断言失败", "suggestion": "修正期望值"},
        {"type": "model", "description": "元素未找到", "suggestion": "更新 locator"},
    ]))
    report = _make_report(cases=[{"id": "TC01", "status": "fail", "error": "assertion error"}])
    hints = analyze_failure(report, [], bridge)
    for h in hints:
        assert h["type"] in ("model", "case", "data")


# ---------------------------------------------------------------------------
# Tests: screenshot integration
# ---------------------------------------------------------------------------

def test_analyze_screenshot_called_for_each_path():
    bridge = _make_bridge()
    report = _make_report(cases=[{"id": "TC01", "status": "fail", "error": "element not found"}])
    screenshots = ["/tmp/shot1.png", "/tmp/shot2.png"]
    analyze_failure(report, screenshots, bridge)
    assert bridge.analyze_screenshot.call_count == 2


def test_screenshot_failure_does_not_crash():
    bridge = _make_bridge()
    bridge.analyze_screenshot.side_effect = Exception("vision unavailable")
    report = _make_report(cases=[{"id": "TC01", "status": "fail", "error": "timeout"}])
    hints = analyze_failure(report, ["/tmp/shot.png"], bridge)
    assert isinstance(hints, list)
    assert len(hints) > 0


# ---------------------------------------------------------------------------
# Tests: LLM fallback
# ---------------------------------------------------------------------------

def test_fallback_when_llm_fails():
    bridge = _make_bridge(raise_llm=True)
    report = _make_report(cases=[{"id": "TC01", "status": "fail", "error": "timeout waiting"}])
    hints = analyze_failure(report, [], bridge)
    assert isinstance(hints, list)
    assert len(hints) > 0


def test_fallback_when_llm_returns_invalid_json():
    bridge = _make_bridge(llm_response="这不是JSON")
    report = _make_report(cases=[{"id": "TC01", "status": "fail", "error": "assertion failed"}])
    hints = analyze_failure(report, [], bridge)
    assert isinstance(hints, list)
    assert len(hints) > 0


# ---------------------------------------------------------------------------
# Tests: fallback rules
# ---------------------------------------------------------------------------

def test_timeout_error_produces_model_hint():
    hints = _fallback_hints("timeout waiting for element #submit")
    types = [h["type"] for h in hints]
    assert "model" in types


def test_assertion_error_produces_data_hint():
    hints = _fallback_hints("assertion failed: expected 'foo' but got 'bar'")
    types = [h["type"] for h in hints]
    assert "data" in types


def test_assert_keyword_produces_data_hint():
    hints = _fallback_hints("assert error on step 3")
    types = [h["type"] for h in hints]
    assert "data" in types


def test_unknown_error_produces_case_hint():
    hints = _fallback_hints("something completely unexpected happened")
    assert hints[0]["type"] == "case"


def test_element_not_found_produces_model_hint():
    hints = _fallback_hints("no such element: #login-btn")
    types = [h["type"] for h in hints]
    assert "model" in types
