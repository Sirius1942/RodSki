"""JSON 输出格式化器 - Agent 集成"""
import json
from typing import Dict, Any, List, Optional


class JSONFormatter:
    """将执行结果格式化为 Agent 友好的 JSON 输出"""

    @staticmethod
    def format_success(results: List[Dict[str, Any]], duration: float) -> Dict[str, Any]:
        """格式化成功执行结果"""
        total = len(results)
        passed = sum(1 for r in results if r.get('status', '').upper() == 'PASS')
        failed = sum(1 for r in results if r.get('status', '').upper() == 'FAIL')
        skipped = sum(1 for r in results if r.get('status', '').upper() == 'SKIP')

        return {
            "status": "success" if failed == 0 else "failed",
            "exit_code": 0 if failed == 0 else 1,
            "summary": {
                "total_steps": total,
                "executed": total - skipped,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "duration": f"{duration:.2f}s"
            },
            "steps": [JSONFormatter._format_step(r, i) for i, r in enumerate(results)],
            "variables": {}
        }

    @staticmethod
    def format_error(error: Exception, case_id: Optional[str] = None,
                    step_index: Optional[int] = None, context: Optional[Dict] = None) -> Dict[str, Any]:
        """格式化错误信息"""
        result = {
            "status": "failed",
            "exit_code": 1,
            "error": {
                "type": type(error).__name__,
                "message": str(error)
            }
        }

        if case_id or step_index is not None:
            result["failed_step"] = {}
            if case_id:
                result["failed_step"]["case_id"] = case_id
            if step_index is not None:
                result["failed_step"]["index"] = step_index

        if context:
            result["context"] = context

        return result

    @staticmethod
    def _format_step(result: Dict[str, Any], index: int) -> Dict[str, Any]:
        """格式化单个步骤结果"""
        return {
            "index": index,
            "case_id": result.get('case_id', ''),
            "title": result.get('title', ''),
            "status": result.get('status', '').lower(),
            "duration": f"{result.get('execution_time', 0):.2f}s",
            "error": result.get('error') if result.get('error') else None,
            "screenshot": result.get('screenshot_path') if result.get('screenshot_path') else None
        }

    @staticmethod
    def to_json(data: Dict[str, Any], pretty: bool = False) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(data, indent=2 if pretty else None, ensure_ascii=False)
