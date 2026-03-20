"""任务执行器 - 加载用例、执行步骤、错误处理、重试"""
import json
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from .keyword_engine import KeywordEngine

logger = logging.getLogger("rodski")


class TaskExecutor:
    def __init__(self, engine: KeywordEngine, max_retries: int = 0, logger=None):
        self.engine = engine
        self.max_retries = max_retries
        self.logger = logger
        self.results: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def execute_steps(self, steps: List[Dict[str, Any]]) -> bool:
        self.results = []
        self.start_time = time.time()
        all_passed = True

        for i, step in enumerate(steps):
            keyword = step.get("keyword", "")
            params = step.get("params", {})
            step_name = step.get("name", f"Step {i + 1}")

            success, error_msg = self._execute_with_retry(keyword, params)
            result = {
                "step": step_name,
                "keyword": keyword,
                "params": params,
                "success": success,
                "timestamp": datetime.now().isoformat(),
            }
            if error_msg:
                result["error"] = error_msg
            self.results.append(result)

            if self.logger:
                status = "PASS" if success else "FAIL"
                log_msg = f"[{status}] {step_name}: {keyword}"
                if error_msg:
                    log_msg += f" - {error_msg}"
                self.logger.info(log_msg) if success else self.logger.error(log_msg)

            if not success:
                all_passed = False
                if not step.get("continue_on_fail", False):
                    break

        self.end_time = time.time()
        return all_passed

    def _execute_with_retry(self, keyword: str, params: Dict) -> tuple:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if self.engine.execute(keyword, params):
                    return True, None
                last_error = f"关键字 '{keyword}' 返回失败"
            except Exception as e:
                last_error = str(e)
                logger.debug(
                    f"关键字 '{keyword}' 第 {attempt + 1} 次执行异常: {e}"
                )
            if attempt < self.max_retries:
                logger.info(
                    f"关键字 '{keyword}' 第 {attempt + 1} 次失败，"
                    f"将进行第 {attempt + 2} 次重试"
                )
                time.sleep(0.5)
        if self.max_retries > 0 and last_error:
            last_error += f" (已重试 {self.max_retries} 次)"
        return False, last_error

    def get_results(self) -> List[Dict]:
        return self.results

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "duration": round(duration, 2),
            "pass_rate": round(passed / total * 100, 1) if total else 0,
        }

    def save_results(self, path: str = "logs/latest_results.json") -> None:
        output = {
            "summary": self.get_summary(),
            "results": self.results,
            "timestamp": datetime.now().isoformat(),
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    def load_case(self, case_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        steps = []
        for row in case_data:
            keyword = row.get("keyword") or row.get("Keyword") or ""
            if not keyword:
                continue
            params = {}
            for k, v in row.items():
                if k.lower() not in ("keyword", "name", "step", "continue_on_fail") and v is not None:
                    params[k.lower()] = v
            steps.append({
                "keyword": keyword.strip(),
                "params": params,
                "name": row.get("name") or row.get("Name") or row.get("step") or keyword,
                "continue_on_fail": bool(row.get("continue_on_fail", False)),
            })
        return steps
