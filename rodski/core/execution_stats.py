"""执行统计模块 - 分析历史执行结果"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


class ExecutionStats:
    """分析测试执行统计数据"""

    @staticmethod
    def calculate_case_success_rate(result_dir: Path, case_id: str, last_n: int = 10) -> Optional[float]:
        """计算指定用例的成功率

        Args:
            result_dir: result/ 目录路径
            case_id: 用例 ID
            last_n: 统计最近 N 次执行

        Returns:
            成功率（0-100），如果没有历史记录返回 None
        """
        results = ExecutionStats._get_case_results(result_dir, case_id, last_n)
        if not results:
            return None

        passed = sum(1 for r in results if r == "PASS")
        return (passed / len(results)) * 100

    @staticmethod
    def get_all_case_stats(result_dir: Path, last_n: int = 10) -> Dict[str, Dict]:
        """获取所有用例的统计信息

        Returns:
            {case_id: {success_rate: float, total_runs: int, last_status: str}}
        """
        stats = defaultdict(lambda: {"statuses": [], "last_status": ""})

        for run_dir in sorted(result_dir.glob("*_*"), reverse=True):
            result_file = run_dir / "result.xml"
            if not result_file.exists():
                continue

            tree = ET.parse(result_file)
            for result_node in tree.findall(".//result"):
                case_id = result_node.get("case_id", "")
                status = result_node.get("status", "")
                if case_id and len(stats[case_id]["statuses"]) < last_n:
                    stats[case_id]["statuses"].append(status)
                    if not stats[case_id]["last_status"]:
                        stats[case_id]["last_status"] = status

        output = {}
        for case_id, data in stats.items():
            statuses = data["statuses"]
            passed = sum(1 for s in statuses if s == "PASS")
            output[case_id] = {
                "success_rate": (passed / len(statuses) * 100) if statuses else 0.0,
                "total_runs": len(statuses),
                "last_status": data["last_status"]
            }

        return output

    @staticmethod
    def _get_case_results(result_dir: Path, case_id: str, last_n: int) -> List[str]:
        """获取指定用例的历史执行状态"""
        results = []
        for run_dir in sorted(result_dir.glob("*_*"), reverse=True):
            result_file = run_dir / "result.xml"
            if not result_file.exists():
                continue

            tree = ET.parse(result_file)
            for result_node in tree.findall(".//result"):
                if result_node.get("case_id") == case_id:
                    results.append(result_node.get("status", ""))
                    if len(results) >= last_n:
                        return results

        return results
