"""v11.6.0 JUnit XML 报告（设计文档 §7 E1）：``rodski run ... --report junit``。

从本次运行目录的 ``result.xml`` 生成 ``junit.xml``（失败信息取自结果 XML）：

- ``<testsuites>`` 汇总；每个用例文件（``case_file``）一个 ``<testsuite>``；
- ``<testcase classname="<case_file>" name="<case_id>" time="秒">``；
- FAIL → ``<failure>``，ERROR → ``<error>``，SKIP → ``<skipped>``；失败信息附截图相对路径
  （相对运行目录），并在 ``<system-out>`` 中写 ``[[ATTACHMENT|路径]]``（Jenkins / GitLab
  均可识别的附件约定）。

输出遵循通用的 JUnit XML 结构（Jenkins xunit ``junit-10.xsd``，GitLab / GitHub Actions
的 JUnit 解析器均兼容）。
"""
from __future__ import annotations

import socket
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from xml.dom import minidom

__all__ = ["build_junit_tree", "write_junit_report", "JUNIT_FILE_NAME"]

JUNIT_FILE_NAME = "junit.xml"
_DEFAULT_CLASSNAME = "rodski"


def _seconds(raw: Any) -> float:
    try:
        return max(0.0, float(str(raw).strip().rstrip("s") or 0))
    except (TypeError, ValueError):
        return 0.0


def _fmt_time(value: float) -> str:
    return f"{value:.3f}"


def _iso_timestamp(raw: str) -> str:
    raw = (raw or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _failure_details(result: ET.Element) -> Dict[str, Any]:
    """从 <result> 提取失败信息：错误、失败步骤、截图（相对运行目录）。"""
    message = result.get("error_message", "") or ""
    error_type = result.get("error_type", "") or ""
    screenshots: List[str] = []
    main_shot = (result.get("screenshot_path") or "").strip()
    if main_shot:
        screenshots.append(main_shot)
    failed_steps: List[str] = []
    for step in result.iter("step"):
        if (step.get("status") or "").upper() in ("FAIL", "ERROR"):
            desc = (
                f"[{step.get('phase', '')}#{step.get('index', '')}] "
                f"{step.get('action', '')} {step.get('model', '')} {step.get('data', '')}".rstrip()
            )
            if step.get("error_message"):
                desc += f" -> {step.get('error_message')}"
            failed_steps.append(desc)
            shot = (step.get("screenshot") or "").strip()
            if shot and shot not in screenshots:
                screenshots.append(shot)
    return {"message": message, "type": error_type, "steps": failed_steps, "screenshots": screenshots}


def build_junit_tree(result_xml: Union[str, Path]) -> ET.Element:
    """读取 result.xml，返回 JUnit ``<testsuites>`` 根元素。"""
    root = ET.parse(str(result_xml)).getroot()
    summary = root.find("summary")
    starts = sorted(s for s in (r.get("start_time", "").strip() for r in root.iter("result")) if s)
    timestamp = _iso_timestamp(starts[0] if starts else (summary.get("start_time", "") if summary is not None else ""))
    hostname = socket.gethostname() or "localhost"

    suites: "OrderedDict[str, List[ET.Element]]" = OrderedDict()
    for res in root.iter("result"):
        suites.setdefault(res.get("case_file") or _DEFAULT_CLASSNAME, []).append(res)

    testsuites = ET.Element("testsuites", name="rodski")
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    for suite_id, (case_file, results) in enumerate(suites.items()):
        counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
        suite = ET.SubElement(testsuites, "testsuite")
        for res in results:
            status = (res.get("status") or "FAIL").upper()
            seconds = _seconds(res.get("execution_time"))
            counts["tests"] += 1
            counts["time"] += seconds
            case = ET.SubElement(
                suite, "testcase",
                classname=case_file, name=res.get("case_id", ""), time=_fmt_time(seconds),
            )
            if status == "SKIP":
                counts["skipped"] += 1
                ET.SubElement(case, "skipped", message=res.get("error_message", "") or "skipped")
            elif status in ("FAIL", "ERROR"):
                d = _failure_details(res)
                tag = "error" if status == "ERROR" else "failure"
                counts["errors" if status == "ERROR" else "failures"] += 1
                el = ET.SubElement(case, tag, message=d["message"] or status, type=d["type"] or status)
                lines = []
                if res.get("title"):
                    lines.append(f"用例: {res.get('case_id', '')} {res.get('title')}")
                if d["message"]:
                    lines.append(f"错误: {d['message']}")
                lines += [f"失败步骤: {s}" for s in d["steps"]]
                lines += [f"截图: {p}" for p in d["screenshots"]]
                el.text = "\n".join(lines)
                if d["screenshots"]:
                    out = ET.SubElement(case, "system-out")
                    out.text = "\n".join(f"[[ATTACHMENT|{p}]]" for p in d["screenshots"])
        suite.set("name", case_file)
        suite.set("tests", str(counts["tests"]))
        suite.set("failures", str(counts["failures"]))
        suite.set("errors", str(counts["errors"]))
        suite.set("skipped", str(counts["skipped"]))
        suite.set("time", _fmt_time(counts["time"]))
        suite.set("timestamp", timestamp)
        suite.set("hostname", hostname)
        suite.set("id", str(suite_id))
        for k in totals:
            totals[k] += counts[k]

    testsuites.set("tests", str(totals["tests"]))
    testsuites.set("failures", str(totals["failures"]))
    testsuites.set("errors", str(totals["errors"]))
    testsuites.set("skipped", str(totals["skipped"]))
    testsuites.set("time", _fmt_time(totals["time"]))
    return testsuites


def write_junit_report(run_dir: Union[str, Path], output: Optional[Union[str, Path]] = None) -> Path:
    """由 ``<run_dir>/result.xml`` 生成 ``<run_dir>/junit.xml``（或 ``output``），返回路径。"""
    run_dir = Path(run_dir)
    result_xml = run_dir / "result.xml"
    if not result_xml.is_file():
        raise FileNotFoundError(f"未找到结果文件 {result_xml}，无法生成 JUnit 报告（本次运行没有产生用例结果？）")
    tree = build_junit_tree(result_xml)
    out_path = Path(output) if output else run_dir / JUNIT_FILE_NAME
    pretty = minidom.parseString(ET.tostring(tree, encoding="unicode")).toprettyxml(indent="  ", encoding="UTF-8")
    out_path.write_bytes(pretty)
    return out_path
