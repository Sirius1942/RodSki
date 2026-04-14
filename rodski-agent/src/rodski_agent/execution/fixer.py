"""简单修复策略 -- MVP 版本。

当 retry_decide 决定重试时，apply_fix 负责记录和应用简单的修复策略。
当前支持：
  - 超时问题：记录添加 wait 步骤
  - 元素定位问题：记录需要修复 locator（实际修复需要 LLM，暂只记录）

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

from rodski_agent.common.rodski_knowledge import validate_action, validate_locator_type


def apply_fix(state: dict) -> dict:
    """应用修复策略。

    根据 diagnosis 中的 root_cause 和 suggestion 选择修复策略，
    将修复记录追加到 fixes_applied 列表。

    Parameters
    ----------
    state : dict
        当前执行状态，需包含 ``diagnosis`` 字段。

    Returns
    -------
    dict
        ``{"fixes_applied": [...], "status": "running"}``
    """
    diagnosis = state.get("diagnosis", {})
    suggestion = diagnosis.get("suggestion", "")
    root_cause = diagnosis.get("root_cause", "")
    fixes = list(state.get("fixes_applied", []))

    # Strategy 1: Add wait for timeout issues
    if "timeout" in root_cause.lower() or "超时" in root_cause:
        fix_desc = _add_wait_fix(state)
        if fix_desc:
            fixes.append(fix_desc)

    # Strategy 2: Note locator fix needed (actual fix requires LLM, just record for now)
    elif "element" in root_cause.lower() or "元素" in root_cause or "locator" in root_cause.lower():
        fixes.append(f"locator_fix_suggested: {suggestion}")

    return {"fixes_applied": fixes, "status": "running"}


def _add_wait_fix(state: dict) -> str | None:
    """在失败步骤前添加 wait 步骤。

    验证 ``wait`` 是合法的 action 后，返回修复描述字符串。

    Returns
    -------
    str | None
        修复描述，或 None（如果 wait 不是合法 action）。
    """
    # Validate wait is a legal action
    if not validate_action("wait"):
        return None
    return "added_wait: wait 3s before failed step"
