"""调试分析器 — 分析执行失败，生成 debug_hints 供 Design Agent 修复。

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_FALLBACK_RULES = [
    ("timeout", "model", "元素定位超时，可能是 locator 不准确", "检查 model 中的 locator 是否与页面实际元素匹配"),
    ("assertion", "data", "断言失败，期望值与实际值不符", "检查 data 文件中的期望值是否正确"),
    ("assert", "data", "断言失败，期望值与实际值不符", "检查 data 文件中的期望值是否正确"),
    ("element not found", "model", "元素未找到，locator 可能失效", "更新 model 中对应元素的 locator"),
    ("no such element", "model", "元素未找到，locator 可能失效", "更新 model 中对应元素的 locator"),
]


def _fallback_hints(error_text: str) -> list[dict]:
    """基于规则从错误文本生成 fallback hints。"""
    lower = error_text.lower()
    hints = []
    seen: set[str] = set()
    for keyword, hint_type, description, suggestion in _FALLBACK_RULES:
        if keyword in lower and hint_type not in seen:
            hints.append({"type": hint_type, "description": description, "suggestion": suggestion})
            seen.add(hint_type)
    if not hints:
        hints.append({
            "type": "case",
            "description": f"执行失败：{error_text[:200]}",
            "suggestion": "检查测试用例步骤和数据是否正确",
        })
    return hints


def analyze_failure(
    execution_report: dict,
    screenshots: list[str],
    llm_bridge: Any,
) -> list[dict]:
    """分析执行失败，返回 debug_hints 列表。

    Parameters
    ----------
    execution_report:
        来自 ExecutionState["report"] 的 dict。
    screenshots:
        失败截图路径列表。
    llm_bridge:
        提供 analyze_screenshot(path, prompt) 和 call_llm_text(prompt) 的模块或对象。

    Returns
    -------
    list of {"type": "model"|"case"|"data", "description": str, "suggestion": str}
    """
    # 1. 提取失败步骤错误信息
    error_parts: list[str] = []
    cases = execution_report.get("cases", [])
    for case in cases:
        if case.get("status") not in ("pass", "PASS"):
            err = case.get("error", "")
            if err:
                error_parts.append(f"[{case.get('id', '?')}] {err}")

    # 顶层 error 兜底
    top_error = execution_report.get("error", "")
    if top_error and not error_parts:
        error_parts.append(top_error)

    combined_error = "\n".join(error_parts) or "unknown failure"

    # 2. 截图分析
    screenshot_analyses: list[str] = []
    for path in screenshots:
        try:
            result = llm_bridge.analyze_screenshot(
                path,
                "请描述当前页面状态，是否有错误提示、弹窗或异常显示？",
            )
            screenshot_analyses.append(result.get("answer", ""))
        except Exception as exc:
            logger.warning("analyze_screenshot failed for %s: %s", path, exc)

    # 3. 综合调用 LLM 生成建议
    try:
        screenshot_section = (
            "\n\n【截图分析】\n" + "\n".join(screenshot_analyses)
            if screenshot_analyses
            else ""
        )
        prompt = (
            "你是一个测试自动化专家，请根据以下执行失败信息，生成修改建议列表。\n\n"
            "【失败信息】\n" + combined_error
            + screenshot_section
            + "\n\n"
            "请以 JSON 数组返回，每项格式：\n"
            '{"type": "model"|"case"|"data", "description": "问题描述", "suggestion": "修改建议"}\n'
            "只返回 JSON 数组，不要其他文字。"
        )
        response = llm_bridge.call_llm_text(prompt)
        text = response.strip()
        if "```json" in text:
            text = text[text.index("```json") + 7: text.rindex("```")].strip()
        elif "```" in text:
            text = text[text.index("```") + 3: text.rindex("```")].strip()
        hints = json.loads(text)
        if isinstance(hints, list) and hints:
            return hints
    except Exception as exc:
        logger.warning("LLM debug analysis failed, using fallback: %s", exc)

    # 4. Fallback
    return _fallback_hints(combined_error)
