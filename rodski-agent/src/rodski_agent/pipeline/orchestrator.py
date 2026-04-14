"""Pipeline 编排器 — Design → Execution 串联。

将 Design Agent 和 Execution Agent 组合成完整的 pipeline：
1. Design: 根据需求生成测试用例 XML
2. Execution: 执行生成的测试用例

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def run_pipeline(
    requirement: str,
    output_dir: str,
    target_url: str | None = None,
    max_retry: int = 3,
    headless: bool = True,
    browser: str = "chromium",
) -> Dict[str, Any]:
    """执行 Design → Execution 完整 pipeline。

    Parameters
    ----------
    requirement:
        测试需求描述。
    output_dir:
        测试用例输出目录。
    target_url:
        被测系统 URL（可选）。
    max_retry:
        最大重试次数。
    headless:
        是否无头模式。
    browser:
        浏览器类型。

    Returns
    -------
    dict
        合并的 pipeline 结果，包含 design 和 execution 两个阶段的结果。
        结构::

            {
                "status": "success" | "failure" | "error",
                "design": { ... },    # Design Agent 结果
                "execution": { ... }, # Execution Agent 结果（design 成功时）
                "error": "..."        # 错误信息（如有）
            }
    """
    result: Dict[str, Any] = {
        "status": "running",
        "design": {},
        "execution": {},
    }

    # ---- Phase 1: Design ----
    logger.info("Pipeline phase 1: Design")
    try:
        from rodski_agent.design.graph import build_design_graph

        design_state: Dict[str, Any] = {
            "requirement": requirement,
            "output_dir": output_dir,
        }
        if target_url:
            design_state["target_url"] = target_url

        design_graph = build_design_graph()
        design_result = design_graph.invoke(design_state)

        design_status = design_result.get("status", "error")
        result["design"] = {
            "status": design_status,
            "generated_files": design_result.get("generated_files", []),
            "validation_errors": design_result.get("validation_errors", []),
        }

        if design_status not in ("success",):
            result["status"] = "error"
            result["error"] = (
                design_result.get("error", "")
                or "Design failed with validation errors"
            )
            return result

    except Exception as exc:
        logger.error("Pipeline design phase failed: %s", exc)
        result["status"] = "error"
        result["error"] = f"Design phase failed: {exc}"
        return result

    # ---- Phase 2: Execution ----
    logger.info("Pipeline phase 2: Execution")
    try:
        from rodski_agent.execution.graph import build_execution_graph

        exec_state: Dict[str, Any] = {
            "case_path": output_dir,
            "max_retry": max_retry,
            "headless": headless,
            "browser": browser,
        }

        exec_graph = build_execution_graph()
        exec_result = exec_graph.invoke(exec_state)

        exec_status = exec_result.get("status", "error")
        result["execution"] = {
            "status": exec_status,
            "report": exec_result.get("report", {}),
        }

        # Map overall status
        if exec_status == "pass":
            result["status"] = "success"
        elif exec_status in ("fail", "partial"):
            result["status"] = "failure"
            result["error"] = exec_result.get("error", "")
        else:
            result["status"] = "error"
            result["error"] = exec_result.get("error", "")

    except Exception as exc:
        logger.error("Pipeline execution phase failed: %s", exc)
        result["status"] = "error"
        result["error"] = f"Execution phase failed: {exc}"

    return result
