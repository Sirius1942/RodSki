"""结果回填模块 - 将测试执行结果写入 XML 文件

替代原来写入 Excel TestResult/TestSummary Sheet 的方式。
XML 格式参见 schemas/result.xsd。
"""
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter

from core.xml_schema_validator import RodskiXmlValidator

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
        run_dir_name = f"rodski_{timestamp}"
        self.current_run_dir = self.result_dir / run_dir_name
        self.current_run_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir = self.current_run_dir / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)

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
            result_elem.set("updated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # 添加步骤详情
            steps_data = result.get("steps", [])
            if steps_data:
                steps_elem = ET.SubElement(result_elem, "steps")
                for step in steps_data:
                    step_elem = ET.SubElement(steps_elem, "step")
                    step_elem.set("phase", str(step.get("phase", "")))
                    step_elem.set("index", str(step.get("index", 0)))
                    step_elem.set("action", str(step.get("action", "")))
                    step_elem.set("model", str(step.get("model", "")))
                    step_elem.set("data", str(step.get("data", "")))
                    step_elem.set("status", str(step.get("status", "FAIL")).upper())
                    step_elem.set("execution_time", str(step.get("execution_time", "")))
                    step_elem.set("error_message", str(step.get("error_message", "")))

            # 添加变量信息
            variables = result.get("variables", {})
            if variables:
                vars_elem = ET.SubElement(result_elem, "variables")
                for name, value in variables.items():
                    var_elem = ET.SubElement(vars_elem, "variable")
                    var_elem.set("name", str(name))
                    var_elem.set("value", str(value))

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
