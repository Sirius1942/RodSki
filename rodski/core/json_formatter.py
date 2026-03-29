"""JSON 输出格式化器 - 为 CLI 提供 JSON 格式输出"""
import json
from typing import Dict, Any, List


class JsonFormatter:
    """将执行结果格式化为 JSON 输出"""

    @staticmethod
    def format_success(results: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
        """格式化成功执行的结果

        Args:
            results: 用例执行结果列表
            summary: 执行统计摘要

        Returns:
            JSON 字符串
        """
        steps = []
        variables = {}

        for result in results:
            steps.append({
                "case_id": result.get("case_id", ""),
                "title": result.get("title", ""),
                "status": result.get("status", "FAIL").upper(),
                "execution_time": result.get("execution_time", 0),
                "error": result.get("error", ""),
                "screenshot_path": result.get("screenshot_path", ""),
            })

        output = {
            "status": "success",
            "exit_code": 0,
            "summary": summary,
            "steps": steps,
            "variables": variables,
        }

        return json.dumps(output, indent=2, ensure_ascii=False)

    @staticmethod
    def format_failure(error_type: str, error_message: str,
                      failed_case_id: str = "", failed_index: int = -1) -> str:
        """格式化失败结果

        Args:
            error_type: 错误类型
            error_message: 错误消息
            failed_case_id: 失败的用例 ID
            failed_index: 失败的步骤索引

        Returns:
            JSON 字符串
        """
        output = {
            "status": "failed",
            "exit_code": 1,
            "error": {
                "type": error_type,
                "message": error_message,
            },
            "failed_step": {
                "case_id": failed_case_id,
                "index": failed_index,
            }
        }

        return json.dumps(output, indent=2, ensure_ascii=False)

    @staticmethod
    def format_interrupt() -> str:
        """格式化用户中断结果

        Returns:
            JSON 字符串
        """
        output = {
            "status": "interrupted",
            "exit_code": 130,
            "error": {
                "type": "UserInterrupt",
                "message": "Execution interrupted by user",
            }
        }

        return json.dumps(output, indent=2, ensure_ascii=False)
