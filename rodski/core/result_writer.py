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

        RodskiXmlValidator.validate_element(
            root, RodskiXmlValidator.KIND_RESULT, source_path=self.result_dir / "<result_output>"
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.result_dir / f"result_{timestamp}.xml"

        xml_str = minidom.parseString(ET.tostring(root, encoding='unicode')).toprettyxml(indent="  ")
        lines = [line for line in xml_str.split('\n') if line.strip()]
        result_file.write_text('\n'.join(lines), encoding='utf-8')

        logger.info(
            f"结果已写入 {result_file.name}: "
            f"总计 {summary['total']} 条, "
            f"通过 {summary['passed']} 条, "
            f"失败 {summary['failed']} 条, "
            f"通过率 {summary['pass_rate']}"
        )

    def get_summary(self) -> ExecutionSummary:
        return self._summary
