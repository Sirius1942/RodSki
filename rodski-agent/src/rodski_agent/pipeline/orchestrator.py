"""Pipeline 编排器 — Design → Validation Gate → Execution。

将 Design Agent 和 Execution Agent 组合成完整的 pipeline：
1. Design: 根据需求生成测试用例 XML
2. Validation Gate: 用 rodski_validate 二次校验所有生成的 XML
3. Execution: 执行生成的测试用例（支持多 case 并行执行）

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import glob
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def run_pipeline(
    requirement: str,
    output_dir: str,
    target_url: str = "",
    max_retry: int = 3,
    max_fix_attempts: int = 3,
    headless: bool = True,
    browser: str = "chromium",
    parallel: bool = False,
    max_workers: int = 3,
) -> Dict[str, Any]:
    """执行 Design → Validation Gate → Execution 完整 pipeline。

    Parameters
    ----------
    requirement:
        测试需求描述。
    output_dir:
        测试用例输出目录。
    target_url:
        被测系统 URL（可选）。
    max_retry:
        执行阶段最大重试次数。
    max_fix_attempts:
        设计阶段 XML 校验失败最大修复次数。
    headless:
        是否无头模式。
    browser:
        浏览器类型。
    parallel:
        是否并行执行多个 case 文件。
    max_workers:
        并行执行最大线程数。

    Returns
    -------
    dict
        合并的 pipeline 结果::

            {
                "status": "success" | "failure" | "error",
                "design": { ... },
                "validation": { ... },
                "execution": { ... },
                "error": "..."
            }
    """
    result: Dict[str, Any] = {
        "status": "running",
        "design": {},
        "validation": {},
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

    # ---- Phase 2: Validation Gate ----
    logger.info("Pipeline phase 2: Validation Gate")
    try:
        validation = _validate_generated_files(output_dir)
        result["validation"] = validation

        if not validation.get("passed", False):
            result["status"] = "error"
            result["error"] = (
                f"Validation gate failed: {len(validation.get('errors', []))} error(s)"
            )
            return result
    except Exception as exc:
        logger.warning("Validation gate skipped: %s", exc)
        result["validation"] = {"passed": True, "skipped": True, "reason": str(exc)}

    # ---- Phase 3: Execution (with debug loop) ----
    logger.info("Pipeline phase 3: Execution")
    try:
        from rodski_agent.design.debugger import analyze_failure
        from rodski_agent.common import llm_bridge as _llm_bridge

        debug_round = 0
        max_debug_rounds = 3

        while True:
            case_files = _find_case_files(output_dir)

            if parallel and len(case_files) > 1:
                exec_results = _execute_parallel(
                    case_files, max_retry, headless, browser, max_workers
                )
            else:
                exec_results = _execute_sequential(
                    case_files or [output_dir], max_retry, headless, browser
                )

            aggregated = _aggregate_execution_results(exec_results)
            exec_status = aggregated.get("status", "error")

            # Success — exit loop
            if exec_status == "pass":
                result["execution"] = aggregated
                result["status"] = "success"
                break

            # Failure — try debug loop
            if debug_round < max_debug_rounds:
                logger.info("Execution failed (round %d), running debug analysis", debug_round)
                exec_report = aggregated.get("report", {})
                # Collect screenshots from all exec results
                all_screenshots: List[str] = []
                for r in exec_results:
                    all_screenshots.extend(r.get("screenshots", []))

                try:
                    hints = analyze_failure(exec_report, all_screenshots, _llm_bridge)
                except Exception as exc:
                    logger.warning("analyze_failure raised: %s", exc)
                    hints = []

                if hints:
                    logger.info("Debug hints generated (%d), re-running design", len(hints))
                    design_state["debug_hints"] = hints
                    design_state["debug_round"] = debug_round + 1
                    design_graph = build_design_graph()
                    design_result = design_graph.invoke(design_state)
                    if design_result.get("status") not in ("success",):
                        # Design failed again — give up
                        result["execution"] = aggregated
                        result["status"] = "failure"
                        result["error"] = aggregated.get("error", "")
                        break
                    debug_round += 1
                    continue

            # No more retries
            result["execution"] = aggregated
            if exec_status in ("fail", "partial"):
                result["status"] = "failure"
                result["error"] = aggregated.get("error", "")
            else:
                result["status"] = "error"
                result["error"] = aggregated.get("error", "")
            break

    except Exception as exc:
        logger.error("Pipeline execution phase failed: %s", exc)
        result["status"] = "error"
        result["error"] = f"Execution phase failed: {exc}"

    return result


def _validate_generated_files(output_dir: str) -> Dict[str, Any]:
    """用 rodski_validate 校验 output_dir 下所有 XML 文件。"""
    from rodski_agent.common.rodski_tools import rodski_validate

    result = rodski_validate(output_dir)
    errors = [e for e in result.stderr.split("\n") if e.strip()] if result.stderr else []

    return {
        "passed": result.success,
        "errors": errors,
        "stdout": result.stdout,
    }


def _find_case_files(output_dir: str) -> List[str]:
    """在 output_dir/case/ 下找到所有 XML 文件。"""
    case_dir = os.path.join(output_dir, "case")
    if not os.path.isdir(case_dir):
        return []
    files = glob.glob(os.path.join(case_dir, "*.xml"))
    return sorted(files)


def _execute_single(
    case_path: str,
    max_retry: int,
    headless: bool,
    browser: str,
) -> Dict[str, Any]:
    """执行单个 case 文件。"""
    from rodski_agent.execution.graph import build_execution_graph

    exec_state: Dict[str, Any] = {
        "case_path": case_path,
        "max_retry": max_retry,
        "headless": headless,
        "browser": browser,
    }

    exec_graph = build_execution_graph()
    return exec_graph.invoke(exec_state)


def _execute_sequential(
    case_paths: List[str],
    max_retry: int,
    headless: bool,
    browser: str,
) -> List[Dict[str, Any]]:
    """顺序执行多个 case。"""
    results: List[Dict[str, Any]] = []
    for path in case_paths:
        try:
            r = _execute_single(path, max_retry, headless, browser)
            r["case_path"] = path
            results.append(r)
        except Exception as exc:
            results.append({
                "case_path": path,
                "status": "error",
                "error": str(exc),
            })
    return results


def _execute_parallel(
    case_paths: List[str],
    max_retry: int,
    headless: bool,
    browser: str,
    max_workers: int,
) -> List[Dict[str, Any]]:
    """并行执行多个 case 文件，每个 case 独立的 execution graph 实例。"""
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(_execute_single, path, max_retry, headless, browser): path
            for path in case_paths
        }
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                r = future.result()
                r["case_path"] = path
                results.append(r)
            except Exception as exc:
                results.append({
                    "case_path": path,
                    "status": "error",
                    "error": str(exc),
                })

    return results


def _aggregate_execution_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """聚合多个 case 的执行结果。"""
    if not results:
        return {"status": "pass", "report": {"total": 0, "passed": 0, "failed": 0}}

    # For single-result case (backward compatibility), return it directly
    if len(results) == 1:
        r = results[0]
        return {
            "status": r.get("status", "error"),
            "report": r.get("report", {}),
            "error": r.get("error", ""),
        }

    # Multi-result aggregation
    total = 0
    passed = 0
    failed = 0
    all_cases: List[Dict] = []
    errors: List[str] = []

    for r in results:
        report = r.get("report", {})
        total += report.get("total", 0)
        passed += report.get("passed", 0)
        failed += report.get("failed", 0)
        all_cases.extend(report.get("cases", []))
        if r.get("error"):
            errors.append(f"{r.get('case_path', '?')}: {r['error']}")

    if failed == 0 and not errors:
        status = "pass"
    elif passed == 0:
        status = "fail"
    else:
        status = "partial"

    return {
        "status": status,
        "report": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "cases": all_cases,
        },
        "error": "; ".join(errors) if errors else "",
    }
