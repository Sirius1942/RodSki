"""Execution Agent 节点实现

每个节点函数签名: fn(state: dict) -> dict
接收当前 state，返回需要更新的字段。

节点列表:
  - pre_check: 预检查
  - execute: 执行测试
  - parse_result: 解析结果
  - diagnose: 诊断失败用例（LLM 驱动，不可用时优雅降级）
  - report: 生成报告
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from rodski_agent.common.rodski_knowledge import (
    validate_directory_structure,
    REQUIRED_DIRS,
)
from rodski_agent.common.result_parser import (
    collect_screenshots,
    extract_cases_from_summary,
    parse_execution_summary,
    parse_result_xml,
)

logger = logging.getLogger(__name__)


def pre_check(state: dict) -> dict:
    """预检查 — 验证用例路径和目录结构完整性

    检查项:
    1. case_path 是否存在
    2. 如果是目录，检查 case/model/data 是否存在
    3. 如果是文件，检查上级模块目录结构

    返回: status 和 error（如果有）
    """
    case_path = state.get("case_path", "")
    p = Path(case_path)

    if not p.exists():
        return {"status": "error", "error": f"Case path not found: {case_path}"}

    # 确定模块目录
    if p.is_file():
        # case/xxx.xml → 模块目录是 case 的上级
        if p.parent.name == "case":
            module_dir = str(p.parent.parent)
        else:
            module_dir = str(p.parent)
    elif p.name == "case":
        module_dir = str(p.parent)
    else:
        module_dir = str(p)

    # 使用 rodski_knowledge 校验目录结构
    missing = validate_directory_structure(module_dir)
    if missing:
        return {
            "status": "error",
            "error": f"Missing required directories in {module_dir}: {', '.join(missing)}",
        }

    return {"status": "running"}


def execute(state: dict) -> dict:
    """执行测试 — 调用 rodski run

    通过 rodski_tools.rodski_run() 调用 rodski 执行引擎。

    exit code 语义（AGENT_INTEGRATION）:
        0 = 成功
        1 = 测试失败
        2 = 配置错误
    """
    if state.get("status") == "error":
        return {}

    from rodski_agent.common.rodski_tools import rodski_run

    case_path = state["case_path"]
    headless = state.get("headless", True)
    browser = state.get("browser", "chromium")

    result = rodski_run(
        case_path=case_path,
        headless=headless,
        browser=browser,
    )

    return {
        "execution_result": {
            "success": result.success,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "result_dir": result.result_dir,
            "result_files": result.result_files,
        },
        "status": "running",
    }


def parse_result(state: dict) -> dict:
    """解析执行结果 — 从 result XML 或 execution_summary.json 提取用例级别结果

    解析格式参考 AGENT_INTEGRATION 输出契约。
    使用 result_parser 模块中的公共函数完成实际解析。
    """
    if state.get("status") == "error":
        return {}

    exec_result = state.get("execution_result", {})
    result_dir = exec_result.get("result_dir")
    case_results: list[dict[str, Any]] = []
    screenshots: list[str] = []

    # 优先解析 execution_summary.json
    if result_dir:
        summary = exec_result.get("execution_summary") or parse_execution_summary(result_dir)
        if summary:
            case_results = extract_cases_from_summary(summary)
        else:
            # 降级解析 result_*.xml
            result_files = exec_result.get("result_files", [])
            if result_files:
                case_results = parse_result_xml(result_files[0])

        # 收集截图
        screenshots = collect_screenshots(result_dir)

    # 如果无法解析结果文件，从 exit_code 推断
    if not case_results:
        exit_code = exec_result.get("exit_code", -1)
        case_results = [{
            "id": "unknown",
            "title": "Unknown",
            "status": "PASS" if exit_code == 0 else "FAIL",
            "time": 0,
            "error": exec_result.get("stderr", "") if exit_code != 0 else "",
        }]

    return {
        "case_results": case_results,
        "screenshots": screenshots,
    }


def report(state: dict) -> dict:
    """生成报告 — 汇总执行结果

    输出 report dict: {total, passed, failed, cases, status_summary}
    """
    case_results = state.get("case_results", [])

    total = len(case_results)
    passed = sum(1 for c in case_results if c.get("status") == "PASS")
    failed = total - passed

    # 判断最终状态
    if state.get("status") == "error":
        final_status = "error"
    elif failed == 0:
        final_status = "pass"
    elif passed == 0:
        final_status = "fail"
    else:
        final_status = "partial"

    return {
        "report": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "cases": case_results,
        },
        "status": final_status,
    }


# ====================================================================
# diagnose 节点
# ====================================================================


def diagnose(state: dict) -> dict:
    """诊断失败用例 — 调用 LLM 分析失败原因。

    对 state["case_results"] 中每个 status != "PASS" 的用例，
    组装 prompt 调用 LLM 获取诊断结果。

    当 LLM 不可用时（rodski 不可导入、配置缺失、连接失败），
    返回降级诊断结果 ``{"skipped": True, "reason": "..."}``。

    Returns
    -------
    dict
        ``{"diagnosis": {...}}``，包含各用例诊断详情。
    """
    case_results = state.get("case_results", [])
    failed_cases = [c for c in case_results if c.get("status") != "PASS"]

    if not failed_cases:
        return {"diagnosis": {"skipped": True, "reason": "No failed cases"}}

    # 尝试导入 LLM 桥接层
    try:
        from rodski_agent.common.llm_bridge import call_llm_text, LLMUnavailableError
        from rodski_agent.execution.prompts import (
            DIAGNOSE_SYSTEM_PROMPT,
            DIAGNOSE_USER_TEMPLATE,
        )
    except ImportError as exc:
        logger.warning("Cannot import LLM bridge or prompts: %s", exc)
        return {"diagnosis": {"skipped": True, "reason": f"Import error: {exc}"}}

    diagnoses: list[dict] = []

    for case in failed_cases:
        case_id = case.get("id", "unknown")
        error_message = case.get("error", "")
        action = case.get("action", "unknown")
        model = case.get("model", "unknown")

        # 截图描述
        screenshots = state.get("screenshots", [])
        screenshot_desc = "无截图"
        if screenshots:
            screenshot_desc = f"共 {len(screenshots)} 张截图: {', '.join(Path(s).name for s in screenshots[:3])}"

        user_prompt = DIAGNOSE_USER_TEMPLATE.format(
            case_id=case_id,
            error_message=error_message,
            action=action,
            model=model,
            screenshot_desc=screenshot_desc,
        )
        full_prompt = DIAGNOSE_SYSTEM_PROMPT + "\n\n" + user_prompt

        try:
            response_text = call_llm_text(full_prompt)
            diagnosis = _parse_diagnosis_response(response_text)
        except LLMUnavailableError as exc:
            logger.warning("LLM unavailable for case %s: %s", case_id, exc)
            return {
                "diagnosis": {
                    "skipped": True,
                    "reason": f"LLM unavailable: {exc}",
                }
            }
        except Exception as exc:
            logger.warning("Diagnosis failed for case %s: %s", case_id, exc)
            diagnosis = _fallback_diagnosis(case_id, error_message)

        # 强制执行置信度规则
        diagnosis = _enforce_confidence_rule(diagnosis)
        diagnosis["case_id"] = case_id
        diagnoses.append(diagnosis)

    return {"diagnosis": {"cases": diagnoses, "skipped": False}}


def _parse_diagnosis_response(response_text: str) -> dict:
    """解析 LLM 返回的诊断 JSON。

    尝试从文本中提取 JSON 对象。如果解析失败，返回 UNKNOWN 降级结果。
    """
    text = response_text.strip()

    # 尝试从 markdown 代码块中提取
    if "```json" in text:
        start = text.index("```json") + len("```json")
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + len("```")
        end = text.index("```", start)
        text = text[start:end].strip()

    try:
        result = json.loads(text)
        # 验证必须字段
        required_fields = [
            "root_cause", "confidence", "category",
            "suggestion", "evidence", "recommended_action",
        ]
        for field in required_fields:
            if field not in result:
                result[field] = _default_field_value(field)
        # 验证 category
        valid_categories = {"CASE_DEFECT", "ENV_DEFECT", "PRODUCT_DEFECT", "UNKNOWN"}
        if result.get("category") not in valid_categories:
            result["category"] = "UNKNOWN"
        # 验证 recommended_action
        valid_actions = {"insert", "pause", "terminate", "escalate"}
        if result.get("recommended_action") not in valid_actions:
            result["recommended_action"] = "pause"
        # 验证 confidence
        try:
            result["confidence"] = float(result["confidence"])
            result["confidence"] = max(0.0, min(1.0, result["confidence"]))
        except (TypeError, ValueError):
            result["confidence"] = 0.3
        return result
    except (json.JSONDecodeError, ValueError):
        return {
            "root_cause": f"LLM 返回非 JSON 格式: {text[:200]}",
            "confidence": 0.2,
            "category": "UNKNOWN",
            "suggestion": "请人工审查",
            "evidence": text[:500],
            "recommended_action": "escalate",
        }


def _default_field_value(field: str) -> Any:
    """返回诊断字段的默认值。"""
    defaults = {
        "root_cause": "未知",
        "confidence": 0.3,
        "category": "UNKNOWN",
        "suggestion": "请人工审查",
        "evidence": "",
        "recommended_action": "pause",
    }
    return defaults.get(field, "")


def _fallback_diagnosis(case_id: str, error_message: str) -> dict:
    """LLM 调用异常时的降级诊断。"""
    return {
        "root_cause": f"自动诊断失败，错误信息: {error_message[:200]}",
        "confidence": 0.2,
        "category": "UNKNOWN",
        "suggestion": "请人工检查失败用例和错误日志",
        "evidence": error_message[:500],
        "recommended_action": "escalate",
    }


def _enforce_confidence_rule(diagnosis: dict) -> dict:
    """强制执行置信度规则：confidence < 0.6 时，recommended_action 只能是 pause 或 escalate。"""
    confidence = diagnosis.get("confidence", 0.0)
    action = diagnosis.get("recommended_action", "pause")

    if confidence < 0.6 and action not in ("pause", "escalate"):
        diagnosis["recommended_action"] = "pause"

    return diagnosis


# ====================================================================
# retry_decide 节点
# ====================================================================


def retry_decide(state: dict) -> dict:
    """基于诊断结果决定是否重试。

    重试条件（必须全部满足）：
    1. retry_count < max_retry
    2. diagnosis.category == "CASE_DEFECT"
    3. diagnosis.confidence > 0.7

    Returns
    -------
    dict
        ``{"retry_decision": "retry" | "give_up", ...}``
    """
    diagnosis = state.get("diagnosis", {})
    retry_count = state.get("retry_count", 0)
    max_retry = state.get("max_retry", 0)

    # Cannot retry if at limit
    if retry_count >= max_retry:
        return {"retry_decision": "give_up"}

    # Only CASE_DEFECT with high confidence is retryable
    category = diagnosis.get("category", "UNKNOWN")
    confidence = diagnosis.get("confidence", 0)

    if category == "CASE_DEFECT" and confidence > 0.7:
        return {"retry_decision": "retry", "retry_count": retry_count + 1}

    # Everything else: give up
    return {"retry_decision": "give_up"}
