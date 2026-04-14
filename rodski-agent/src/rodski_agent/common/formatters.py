"""人类可读格式化器 — 将结构化结果渲染为终端友好的文本。

支持 ANSI 颜色（通过 ``click.style``），遵循 ``NO_COLOR`` 环境变量。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List


def _use_color() -> bool:
    """判断是否启用终端颜色。

    遵循 https://no-color.org/ 约定：如果环境变量 ``NO_COLOR`` 存在
    （不论值为何），则禁用颜色。
    """
    return "NO_COLOR" not in os.environ


def _style(text: str, **kwargs: Any) -> str:
    """条件着色：仅在颜色启用时应用 click.style。"""
    if not _use_color():
        return text
    try:
        import click
        return click.style(text, **kwargs)
    except ImportError:
        return text


def format_run_result(report: Dict[str, Any]) -> str:
    """将 run 命令的报告字典格式化为人类可读文本。

    Parameters
    ----------
    report : dict
        包含 ``total``, ``passed``, ``failed``, ``cases`` 字段的报告字典。

    Returns
    -------
    str
        格式化后的多行文本，包含摘要表和失败详情。
    """
    total = report.get("total", 0)
    passed = report.get("passed", 0)
    failed = report.get("failed", 0)
    cases: List[Dict[str, Any]] = report.get("cases", [])

    lines: list[str] = []

    # ---- 标题 ----
    lines.append("")
    lines.append(_style("Test Results", bold=True))
    lines.append("=" * 50)

    # ---- 摘要 ----
    pass_text = _style(str(passed), fg="green")
    fail_text = _style(str(failed), fg="red") if failed > 0 else str(failed)
    lines.append(f"Total: {total}  |  Passed: {pass_text}  |  Failed: {fail_text}")
    lines.append("-" * 50)

    # ---- 用例列表 ----
    for case in cases:
        case_id = case.get("id", "?")
        title = case.get("title", "")
        status = case.get("status", "UNKNOWN")
        time_val = case.get("time", 0)

        if status == "PASS":
            status_str = _style("PASS", fg="green")
        elif status == "FAIL":
            status_str = _style("FAIL", fg="red")
        else:
            status_str = _style(status, fg="yellow")

        label = f"{case_id}"
        if title:
            label = f"{case_id}: {title}"
        lines.append(f"  [{status_str}] {label} ({time_val:.1f}s)")

    # ---- 失败详情 ----
    failed_cases = [c for c in cases if c.get("status") != "PASS"]
    if failed_cases:
        lines.append("")
        lines.append(_style("Failure Details", bold=True))
        lines.append("-" * 50)
        for case in failed_cases:
            case_id = case.get("id", "?")
            error = case.get("error", "")
            lines.append(f"  {_style(case_id, fg='red')}: {error or '(no error message)'}")

    lines.append("")
    return "\n".join(lines)


def format_error(error_dict: Dict[str, Any]) -> str:
    """将错误字典格式化为人类可读文本。

    Parameters
    ----------
    error_dict : dict
        包含 ``code``, ``category``, ``message`` 等字段的错误字典。

    Returns
    -------
    str
        格式化后的错误文本。
    """
    code = error_dict.get("code", "UNKNOWN")
    category = error_dict.get("category", "unknown")
    message = error_dict.get("message", "Unknown error")
    suggestion = error_dict.get("suggestion")

    lines: list[str] = []
    lines.append(_style(f"Error [{code}]", fg="red", bold=True))
    lines.append(f"  Category: {category}")
    lines.append(f"  Message:  {message}")
    if suggestion:
        lines.append(f"  Suggestion: {suggestion}")
    return "\n".join(lines)
