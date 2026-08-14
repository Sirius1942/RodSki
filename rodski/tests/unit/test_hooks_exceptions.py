"""Hooks 机制新增异常类型测试（v8.2.0，SKI701/SKI702/SKI703）"""
from core.exceptions import (
    HookDeniedError,
    HookTimeoutError,
    ComplianceCheckFailedError,
    ERROR_CODE_MAP,
)


def test_hook_denied_error_to_dict():
    e = HookDeniedError(event="before_keyword", reason="DB write to prod")
    d = e.to_dict()
    assert d["error_code"] == "SKI701"
    assert d["details"]["event"] == "before_keyword"
    assert d["details"]["reason"] == "DB write to prod"


def test_hook_timeout_error_to_dict():
    e = HookTimeoutError(event="on_run_start", timeout=10)
    d = e.to_dict()
    assert d["error_code"] == "SKI702"
    assert d["error_level"] == "WARNING"
    assert d["details"]["event"] == "on_run_start"
    assert d["details"]["timeout"] == 10


def test_compliance_check_failed_error_to_dict():
    checks_failed = [
        {"check_name": "directory_structure", "reason": "缺少 case/"},
        {"check_name": "plan_selector_conflict", "reason": "@plan_id 与 --tag 互斥"},
    ]
    e = ComplianceCheckFailedError(checks_failed=checks_failed)
    d = e.to_dict()
    assert d["error_code"] == "SKI703"
    assert d["details"]["checks_failed"] == checks_failed
    assert "directory_structure" in d["message"]


def test_error_code_map_registered():
    assert ERROR_CODE_MAP["SKI701"] is HookDeniedError
    assert ERROR_CODE_MAP["SKI702"] is HookTimeoutError
    assert ERROR_CODE_MAP["SKI703"] is ComplianceCheckFailedError
