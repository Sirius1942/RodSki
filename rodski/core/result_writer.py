"""结果回填模块 - 将测试执行结果写入 XML 文件

XML 格式参见 schemas/result.xsd。
"""
import json
import logging
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections.abc import Mapping
from collections import Counter

from .xml_schema_validator import RodskiXmlValidator

logger = logging.getLogger("rodski")


class ExecutionSummary:
    """执行结果统计"""

    def __init__(self):
        self.total: int = 0
        self.passed: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.errors: int = 0
        self.total_time: float = 0.0
        self.error_types: Counter = Counter()
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def add_result(self, result: Dict[str, Any]) -> None:
        """添加单个结果到统计"""
        self.total += 1
        status = result.get("status", "FAIL").upper()

        if status == "PASS":
            self.passed += 1
        elif status == "SKIP":
            self.skipped += 1
        elif status == "ERROR":
            self.errors += 1
        else:
            self.failed += 1

        exec_time = result.get("execution_time", 0)
        if isinstance(exec_time, (int, float)):
            self.total_time += exec_time

        error_type = result.get("error_type", "")
        if error_type:
            self.error_types[error_type] += 1

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    @property
    def average_time(self) -> float:
        if self.total == 0:
            return 0.0
        return self.total_time / self.total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "pass_rate": f"{self.pass_rate:.1f}%",
            "total_time": f"{self.total_time:.2f}s",
            "average_time": f"{self.average_time:.2f}s",
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else "",
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else "",
        }


class ResultWriter:
    """将测试结果写入 XML 文件"""

    def __init__(self, result_dir: str):
        """初始化结果写入器

        Args:
            result_dir: result/ 目录路径
        """
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self._summary = ExecutionSummary()
        self.current_run_dir: Optional[Path] = None

    def _init_run_dir(self) -> None:
        """初始化本次执行的结果目录"""
        if self.current_run_dir:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # RODSKI_RUN_DIR_SUFFIX 由 `rodski queue` 的调度器按「计划+设备」注入：
        # 时间戳只到秒，两个子进程同秒启动会落到同一目录，后者的日志 FileHandler
        # 会把前者的 execution.log 摘掉、screenshots/<case_id>.png 也会互相覆盖。
        # 未设置该环境变量时目录名与既有行为完全一致。
        suffix = os.environ.get("RODSKI_RUN_DIR_SUFFIX", "").strip()
        run_dir_name = f"rodski_{timestamp}" + (f"_{suffix}" if suffix else "")
        self.current_run_dir = self.result_dir / run_dir_name
        self.current_run_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir = self.current_run_dir / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        recordings_dir = self.current_run_dir / "recordings"
        recordings_dir.mkdir(exist_ok=True)

        # 同步日志目录到 Logger
        rodski_logger = logging.getLogger("rodski")

        # 设置 logger 级别为 DEBUG，确保所有日志都能被记录
        rodski_logger.setLevel(logging.DEBUG)

        for handler in rodski_logger.handlers:
            if hasattr(handler, '__class__') and handler.__class__.__name__ == 'FileHandler':
                rodski_logger.removeHandler(handler)
                handler.close()

        log_file = self.current_run_dir / "execution.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        rodski_logger.addHandler(fh)

    @staticmethod
    def _business_value(value: Any) -> str:
        """将业务结果中的值稳定地编码为 XML 属性字符串。

        actual/expected/node 输出仍然是普通结构化数据；标量保持可读文本，
        list/dict 使用 JSON，避免因为 Python repr 造成不可逆或不稳定的结果文件。
        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        return str(value)

    @classmethod
    def _write_business_fields(cls, parent: ET.Element, values: Any) -> None:
        """写入映射字段；非映射值按 value 字段保留。"""
        if isinstance(values, Mapping):
            items = values.items()
        else:
            items = (("value", values),)
        for name, value in items:
            field_elem = ET.SubElement(parent, "field")
            field_elem.set("name", str(name))
            field_elem.set("value", cls._business_value(value))

    @classmethod
    def _write_business_path(cls, parent: ET.Element, path: Any) -> None:
        """写入路径节点，兼容 list/tuple 以及单个字符串路径。"""
        if isinstance(path, (str, bytes)):
            path = [path]
        for item in path or []:
            node_elem = ET.SubElement(parent, "node")
            node_elem.set("id", cls._business_value(item))

    @classmethod
    def _write_business_result(cls, parent: ET.Element, business_result: Any) -> None:
        """将 business_call 的结构化结果写入 result XML。

        该结构是 StepType 下的可选扩展；没有 business_result 的旧结果完全不变。
        """
        if not isinstance(business_result, Mapping):
            raise TypeError("business_result must be a mapping")

        result_elem = ET.SubElement(parent, "business_result")
        for attr in ("id", "ref", "flow", "input", "expect"):
            if attr in business_result and business_result[attr] is not None:
                result_elem.set(attr, cls._business_value(business_result[attr]))
        if "passed" in business_result and business_result["passed"] is not None:
            result_elem.set("passed", "true" if business_result["passed"] else "false")

        for path_name in ("actual_path", "expected_path"):
            if path_name not in business_result or business_result[path_name] is None:
                continue
            path_elem = ET.SubElement(result_elem, path_name)
            cls._write_business_path(path_elem, business_result[path_name])

        for map_name in ("actual", "expected"):
            if map_name not in business_result or business_result[map_name] is None:
                continue
            map_elem = ET.SubElement(result_elem, map_name)
            cls._write_business_fields(map_elem, business_result[map_name])

        if "nodes" in business_result and business_result["nodes"] is not None:
            nodes_elem = ET.SubElement(result_elem, "nodes")
            for index, node in enumerate(business_result["nodes"] or [], 1):
                node_elem = ET.SubElement(nodes_elem, "node")
                if isinstance(node, Mapping):
                    node_id = node.get("node_id", node.get("id", index))
                    node_elem.set("id", cls._business_value(node_id))
                    node_steps = node.get("steps")
                    if node_steps is not None:
                        node_steps_elem = ET.SubElement(node_elem, "steps")
                        for step_index, step_output in enumerate(node_steps or [], 1):
                            output_elem = ET.SubElement(node_steps_elem, "step")
                            output_elem.set("index", str(step_index))
                            cls._write_business_fields(output_elem, step_output)
                    extra = {
                        key: value
                        for key, value in node.items()
                        if key not in {"node_id", "id", "steps"}
                    }
                    if extra:
                        fields_elem = ET.SubElement(node_elem, "fields")
                        cls._write_business_fields(fields_elem, extra)
                else:
                    node_elem.set("id", cls._business_value(node))

        if "assertion_errors" in business_result and business_result["assertion_errors"] is not None:
            errors_elem = ET.SubElement(result_elem, "assertion_errors")
            errors = business_result["assertion_errors"]
            if isinstance(errors, (str, bytes)):
                errors = [errors]
            for error in errors or []:
                error_elem = ET.SubElement(errors_elem, "error")
                error_elem.text = cls._business_value(error)

    @staticmethod
    def _normalize_recordings(result: Dict[str, Any]) -> List[Dict[str, str]]:
        recordings: List[Dict[str, str]] = []
        for idx, item in enumerate(result.get("recordings") or [], 1):
            if isinstance(item, dict):
                path = str(item.get("path", ""))
                if not path:
                    continue
                recordings.append({
                    "index": str(item.get("index", idx)),
                    "path": path,
                    "backend": str(item.get("backend", "")),
                })
            elif item:
                recordings.append({"index": str(idx), "path": str(item), "backend": ""})

        legacy_path = str(result.get("recording_path", ""))
        if legacy_path and not any(item.get("path") == legacy_path for item in recordings):
            recordings.insert(0, {"index": "1", "path": legacy_path, "backend": ""})
            for idx, item in enumerate(recordings, 1):
                item["index"] = str(idx)
        return recordings

    def write_result(self, result: Dict[str, Any]) -> None:
        self.write_results([result])

    def write_results(self, results: List[Dict[str, Any]]) -> None:
        """批量写入用例结果到 XML 文件"""
        if not results:
            return

        self._summary = ExecutionSummary()
        self._summary.start_time = datetime.now()
        for result in results:
            self._summary.add_result(result)
        self._summary.end_time = datetime.now()

        self._init_run_dir()

        root = ET.Element("testresult")

        summary = self._summary.to_dict()
        summary_elem = ET.SubElement(root, "summary")
        summary_elem.set("total", str(summary["total"]))
        summary_elem.set("passed", str(summary["passed"]))
        summary_elem.set("failed", str(summary["failed"]))
        summary_elem.set("skipped", str(summary["skipped"]))
        summary_elem.set("errors", str(summary["errors"]))
        summary_elem.set("pass_rate", summary["pass_rate"])
        summary_elem.set("total_time", summary["total_time"])
        summary_elem.set("average_time", summary["average_time"])
        summary_elem.set("start_time", summary["start_time"])
        summary_elem.set("end_time", summary["end_time"])

        results_elem = ET.SubElement(root, "results")
        for result in results:
            result_elem = ET.SubElement(results_elem, "result")
            result_elem.set("case_id", str(result.get("case_id", "")))
            result_elem.set("title", str(result.get("title", "")))
            result_elem.set("status", str(result.get("status", "FAIL")).upper())
            result_elem.set("execution_time", str(result.get("execution_time", "")))
            result_elem.set("retries", str(result.get("retries", 0)))
            result_elem.set("start_time", str(result.get("start_time", "")))
            result_elem.set("end_time", str(result.get("end_time", "")))
            result_elem.set("error_type", str(result.get("error_type", "")))
            result_elem.set("error_message", str(result.get("error", "")))
            result_elem.set("screenshot_path", str(result.get("screenshot_path", "")))
            recordings = self._normalize_recordings(result)
            primary_recording_path = str(
                result.get("recording_path", "") or (recordings[0]["path"] if recordings else "")
            )
            result_elem.set("recording_path", primary_recording_path)
            result_elem.set("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # 添加步骤详情
            steps_data = result.get("steps", [])
            if steps_data:
                # 步骤日志状态用 ok/fail，结果 schema 用 PASS/FAIL/SKIP/ERROR，做映射
                _step_status_map = {"OK": "PASS", "FAIL": "FAIL", "SKIP": "SKIP", "ERROR": "ERROR"}
                steps_elem = ET.SubElement(result_elem, "steps")
                for step in steps_data:
                    step_elem = ET.SubElement(steps_elem, "step")
                    step_elem.set("phase", str(step.get("phase", "")))
                    step_elem.set("index", str(step.get("index", 0)))
                    step_elem.set("action", str(step.get("action", "")))
                    step_elem.set("model", str(step.get("model", "")))
                    step_elem.set("data", str(step.get("data", "")))
                    raw_status = str(step.get("status", "FAIL")).upper()
                    step_elem.set("status", _step_status_map.get(raw_status, "PASS"))
                    step_elem.set("execution_time", str(step.get("execution_time", "")))
                    step_elem.set("error_message", str(step.get("error", step.get("error_message", "")) or ""))
                    screenshot = step.get("screenshot", "")
                    if screenshot:
                        step_elem.set("screenshot", str(screenshot))
                    if "business_result" in step and step.get("business_result") is not None:
                        self._write_business_result(step_elem, step.get("business_result"))

            # 添加变量信息
            variables = result.get("variables", {})
            if variables:
                vars_elem = ET.SubElement(result_elem, "variables")
                for name, value in variables.items():
                    var_elem = ET.SubElement(vars_elem, "variable")
                    var_elem.set("name", str(name))
                    var_elem.set("value", str(value))

            # 添加录制分段信息
            if recordings:
                recordings_elem = ET.SubElement(result_elem, "recordings")
                for item in recordings:
                    rec_elem = ET.SubElement(recordings_elem, "recording")
                    rec_elem.set("index", item.get("index", ""))
                    rec_elem.set("path", item.get("path", ""))
                    if item.get("backend"):
                        rec_elem.set("backend", item.get("backend", ""))

        RodskiXmlValidator.validate_element(
            root, RodskiXmlValidator.KIND_RESULT, source_path=self.result_dir / "<result_output>"
        )

        result_file = self.current_run_dir / "result.xml"

        xml_str = minidom.parseString(ET.tostring(root, encoding='unicode')).toprettyxml(indent="  ")
        lines = [line for line in xml_str.split('\n') if line.strip()]
        result_file.write_text('\n'.join(lines), encoding='utf-8')

        logger.info(
            f"结果已写入 {self.current_run_dir.name}/result.xml: "
            f"总计 {summary['total']} 条, "
            f"通过 {summary['passed']} 条, "
            f"失败 {summary['failed']} 条, "
            f"通过率 {summary['pass_rate']}"
        )

    def get_summary(self) -> ExecutionSummary:
        return self._summary


def write_execution_summary(result_dir: Path, case_id: str, steps: list, context_named: dict) -> None:
    """写入 execution_summary.json 到结果目录"""
    import json
    summary = {
        "case": case_id,
        "steps": steps,
        "context_snapshot": {"named": context_named},
    }
    out_path = Path(result_dir) / "execution_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"execution_summary.json 已写入: {out_path}")
