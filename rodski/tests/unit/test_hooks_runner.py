"""外部命令 hook 执行器测试（v8.2.0 Hooks 机制）"""
import sys

from core.hooks_runner import run_external_hook


def _py(code: str):
    return [sys.executable, "-c", code]


def test_all_hooks_allow():
    decision = run_external_hook(
        "on_run_start",
        {"x": 1},
        [{"command": _py("import sys; sys.exit(0)")}],
    )
    assert decision.allow is True


def test_hook_deny_short_circuits():
    decision = run_external_hook(
        "on_run_start",
        {"x": 1},
        [
            {"command": _py("import sys; print('{\"reason\": \"policy violation\"}'); sys.exit(2)")},
            # 第二个 hook 不应被执行到（虽然本实现无法直接断言"未调用"，
            # 但通过短路后 decision.allow=False 间接验证不会继续遍历）
            {"command": _py("import sys; sys.exit(0)")},
        ],
    )
    assert decision.allow is False
    assert "SKI701" in decision.reason
    assert "policy violation" in decision.reason


def test_hook_timeout_treated_as_deny():
    decision = run_external_hook(
        "on_run_start",
        {"x": 1},
        [{"command": _py("import time; time.sleep(2)"), "timeout": 0.2}],
    )
    assert decision.allow is False
    assert "SKI702" in decision.reason
    assert "超时" in decision.reason


def test_hook_nonzero_non_two_exit_code_warns_but_continues():
    decision = run_external_hook(
        "on_run_start",
        {"x": 1},
        [
            {"command": _py("import sys; sys.exit(1)")},
            {"command": _py("import sys; sys.exit(0)")},
        ],
    )
    assert decision.allow is True


def test_hook_illegal_stdout_used_as_plain_reason():
    decision = run_external_hook(
        "on_run_start",
        {"x": 1},
        [{"command": _py("import sys; print('plain text, not json'); sys.exit(2)")}],
    )
    assert decision.allow is False
    assert "plain text, not json" in decision.reason


def test_command_not_executable_warns_and_continues():
    decision = run_external_hook(
        "on_run_start",
        {"x": 1},
        [{"command": ["/nonexistent/binary/path/xyz"]}],
    )
    assert decision.allow is True  # 命令不可执行按 warning 处理，不阻断


def test_context_passed_via_stdin():
    decision = run_external_hook(
        "on_run_start",
        {"case_id": "c001"},
        [
            {
                "command": _py(
                    "import sys, json; "
                    "data = json.loads(sys.stdin.read()); "
                    "sys.exit(0 if data.get('case_id') == 'c001' "
                    "and data.get('event') == 'on_run_start' else 2)"
                )
            }
        ],
    )
    assert decision.allow is True


def test_empty_hook_specs_allows():
    decision = run_external_hook("on_run_start", {"x": 1}, [])
    assert decision.allow is True
