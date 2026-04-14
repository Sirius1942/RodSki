"""结果解析器 — 从 rodski 输出文件中提取结构化结果。

将原先散落在 ``execution/nodes.py`` 中的私有解析函数提炼为可复用的公共 API。

主要函数:
  - ``parse_execution_summary`` — 解析 execution_summary.json
  - ``parse_result_xml``        — 解析 result_*.xml
  - ``find_latest_result``      — 找到 result 目录下最新的 result_*.xml
  - ``collect_screenshots``     — 收集截图文件路径

Python 3.9 兼容：使用 ``from __future__ import annotations`` 延迟求值。
"""

from __future__ import annotations

import glob
import json
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


def parse_execution_summary(path: str) -> Dict[str, Any]:
    """解析 execution_summary.json，返回其内容。

    Parameters
    ----------
    path : str
        execution_summary.json 的完整路径，或包含该文件的目录路径。

    Returns
    -------
    dict
        解析后的 JSON 内容。如果文件不存在或解析失败，返回空字典。
    """
    if os.path.isdir(path):
        path = os.path.join(path, "execution_summary.json")

    if not os.path.isfile(path):
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def extract_cases_from_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 execution_summary 字典中提取用例级结果列表。

    兼容两种格式：``summary.cases`` 和 ``summary.results``。

    Returns
    -------
    list[dict]
        每个元素包含 ``id, title, status, time, error`` 字段。
    """
    results: List[Dict[str, Any]] = []
    for case in summary.get("cases", summary.get("results", [])):
        results.append({
            "id": case.get("case_id", case.get("id", "unknown")),
            "title": case.get("title", ""),
            "status": case.get("status", "UNKNOWN"),
            "time": case.get("execution_time", case.get("time", 0)),
            "error": case.get("error", case.get("error_message", "")),
        })
    return results


def parse_result_xml(path: str) -> List[Dict[str, Any]]:
    """解析 result_*.xml，提取用例级结果。

    支持的 XML 结构::

        <testresult>
          <summary total="2" passed="1" failed="1" .../>
          <results>
            <result case_id="c001" title="..." status="PASS"
                    execution_time="2.3" .../>
          </results>
        </testresult>

    Parameters
    ----------
    path : str
        result_*.xml 文件的完整路径。

    Returns
    -------
    list[dict]
        每个元素包含 ``id, title, status, time, error`` 字段。
        解析失败时返回空列表。
    """
    results: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return results

    try:
        tree = ET.parse(path)
        root = tree.getroot()
        for result_elem in root.findall(".//result"):
            results.append({
                "id": result_elem.get("case_id", "unknown"),
                "title": result_elem.get("title", ""),
                "status": result_elem.get("status", "UNKNOWN"),
                "time": float(result_elem.get("execution_time", "0")),
                "error": result_elem.get(
                    "error_message", result_elem.get("error", "")
                ),
            })
    except (ET.ParseError, OSError):
        pass

    return results


def find_latest_result(result_dir: str) -> Optional[str]:
    """在 result 目录下找到最新的 result_*.xml 文件。

    Parameters
    ----------
    result_dir : str
        result/ 目录路径。

    Returns
    -------
    str | None
        最新 result_*.xml 的完整路径，如果找不到则返回 ``None``。
    """
    if not os.path.isdir(result_dir):
        return None

    pattern = os.path.join(result_dir, "result_*.xml")
    files = glob.glob(pattern)
    if not files:
        return None

    return sorted(files, key=os.path.getmtime, reverse=True)[0]


def collect_screenshots(result_dir: str) -> List[str]:
    """收集 result 目录下的截图文件路径。

    查找 ``result_dir/screenshots/`` 子目录中的 ``.png`` 和 ``.jpg`` 文件。

    Parameters
    ----------
    result_dir : str
        result/ 目录路径。

    Returns
    -------
    list[str]
        截图文件的完整路径列表。
    """
    screenshot_dir = os.path.join(result_dir, "screenshots")
    if not os.path.isdir(screenshot_dir):
        return []

    return [
        os.path.join(screenshot_dir, f)
        for f in sorted(os.listdir(screenshot_dir))
        if f.endswith((".png", ".jpg"))
    ]
