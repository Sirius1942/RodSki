"""Execution Agent 节点实现 — MVP 版本

每个节点函数签名: fn(state: dict) -> dict
接收当前 state，返回需要更新的字段。
"""

from __future__ import annotations

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

from rodski_agent.common.rodski_knowledge import (
    validate_directory_structure,
    REQUIRED_DIRS,
)


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
    """
    if state.get("status") == "error":
        return {}

    exec_result = state.get("execution_result", {})
    result_dir = exec_result.get("result_dir")
    case_results = []
    screenshots = []

    # 优先解析 execution_summary.json
    if result_dir:
        summary = exec_result.get("execution_summary") or _try_parse_summary(result_dir)
        if summary:
            case_results = _extract_from_summary(summary)
        else:
            # 降级解析 result_*.xml
            result_files = exec_result.get("result_files", [])
            if result_files:
                case_results = _parse_result_xml(result_files[0])

        # 收集截图
        screenshot_dir = os.path.join(result_dir, "screenshots")
        if os.path.isdir(screenshot_dir):
            screenshots = [
                os.path.join(screenshot_dir, f)
                for f in os.listdir(screenshot_dir)
                if f.endswith((".png", ".jpg"))
            ]

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


# ---- 内部辅助函数 ----

def _try_parse_summary(result_dir: str) -> Optional[dict]:
    """尝试解析 execution_summary.json"""
    path = os.path.join(result_dir, "execution_summary.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _extract_from_summary(summary: dict) -> list[dict]:
    """从 execution_summary.json 提取用例结果"""
    results = []
    for case in summary.get("cases", summary.get("results", [])):
        results.append({
            "id": case.get("case_id", case.get("id", "unknown")),
            "title": case.get("title", ""),
            "status": case.get("status", "UNKNOWN"),
            "time": case.get("execution_time", case.get("time", 0)),
            "error": case.get("error", case.get("error_message", "")),
        })
    return results


def _parse_result_xml(xml_path: str) -> list[dict]:
    """解析 result_*.xml 提取用例结果

    result.xsd 结构:
    <testresult>
      <summary total="2" passed="1" failed="1" .../>
      <results>
        <result case_id="c001" title="..." status="PASS" execution_time="2.3" .../>
      </results>
    </testresult>
    """
    results = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for result_elem in root.findall(".//result"):
            results.append({
                "id": result_elem.get("case_id", "unknown"),
                "title": result_elem.get("title", ""),
                "status": result_elem.get("status", "UNKNOWN"),
                "time": float(result_elem.get("execution_time", "0")),
                "error": result_elem.get("error_message", result_elem.get("error", "")),
            })
    except (ET.ParseError, OSError):
        pass
    return results
