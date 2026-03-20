"""并发执行器 - 支持多用例并行执行"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from .task_executor import TaskExecutor
from .keyword_engine import KeywordEngine

logger = logging.getLogger("rodski")


class ParallelExecutor:
    """并发执行多个测试用例"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def execute(self, tasks: List) -> List:
        """执行任务列表"""
        if not tasks:
            return []

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(task) for task in tasks]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append(e)
        return results
    
    def execute_cases(self, cases: List[Dict[str, Any]], driver_factory) -> List[Dict]:
        """
        并发执行多个用例
        
        Args:
            cases: 用例列表，每个用例包含 steps
            driver_factory: 创建 driver 的工厂函数
            
        Returns:
            执行结果列表
        """
        results = []
        total = len(cases)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._execute_single, case, driver_factory): case
                for case in cases
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                case = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "✅" if result["success"] else "❌"
                    logger.info(f"[{completed}/{total}] {status} {case.get('name', 'Unknown')}")
                except Exception as e:
                    logger.error(f"用例执行异常: {e}")
                    results.append({
                        "case": case.get("name", "Unknown"),
                        "success": False,
                        "error": str(e)
                    })
        
        return results
    
    def _execute_single(self, case: Dict[str, Any], driver_factory) -> Dict:
        """执行单个用例（在独立线程中）"""
        driver = None
        try:
            driver = driver_factory()
            engine = KeywordEngine(driver)
            executor = TaskExecutor(engine)
            
            steps = case.get("steps", [])
            success = executor.execute_steps(steps)
            
            return {
                "case": case.get("name", "Unknown"),
                "success": success,
                "results": executor.results
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
