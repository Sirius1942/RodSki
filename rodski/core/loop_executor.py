"""Loop execution support for dynamic test steps"""
import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger("rodski")


class LoopType(Enum):
    """Loop execution types"""
    FIXED = "fixed"
    FOR_EACH = "for_each"
    UNTIL = "until"
    WHILE = "while"


@dataclass
class LoopConfiguration:
    """Loop configuration"""
    loop_type: LoopType
    count: Optional[int] = None
    items: Optional[List[Any]] = None
    item_var: str = "item"
    index_var: str = "index"
    condition: Optional[str] = None
    max_iterations: int = 1000
    break_on_fail: bool = False


class LoopParser:
    """Parse loop configuration strings"""

    @staticmethod
    def parse(loop_str: str, variables: Dict[str, Any]) -> LoopConfiguration:
        """Parse loop string into configuration

        Formats:
        - "5" -> fixed count
        - "for item in ${list}" -> for each
        - "until condition max=N" -> until condition
        - "while condition max=N" -> while condition
        """
        loop_str = loop_str.strip()

        # Fixed count: "5"
        if loop_str.isdigit():
            return LoopConfiguration(
                loop_type=LoopType.FIXED,
                count=int(loop_str)
            )

        # For each: "for item in ${list}"
        for_match = re.match(r'for\s+(\w+)\s+in\s+(.+)', loop_str, re.IGNORECASE)
        if for_match:
            item_var = for_match.group(1)
            items_expr = for_match.group(2).strip()

            # Resolve variable
            if items_expr.startswith('${') and items_expr.endswith('}'):
                var_name = items_expr[2:-1]
                items = variables.get(var_name, [])
            else:
                items = variables.get(items_expr, [])

            if not isinstance(items, list):
                items = [items]

            return LoopConfiguration(
                loop_type=LoopType.FOR_EACH,
                items=items,
                item_var=item_var
            )

        # Until: "until condition max=N"
        until_match = re.match(r'until\s+(.+?)(?:\s+max=(\d+))?$', loop_str, re.IGNORECASE)
        if until_match:
            condition = until_match.group(1).strip()
            max_iter = int(until_match.group(2)) if until_match.group(2) else 1000
            return LoopConfiguration(
                loop_type=LoopType.UNTIL,
                condition=condition,
                max_iterations=max_iter
            )

        # While: "while condition max=N"
        while_match = re.match(r'while\s+(.+?)(?:\s+max=(\d+))?$', loop_str, re.IGNORECASE)
        if while_match:
            condition = while_match.group(1).strip()
            max_iter = int(while_match.group(2)) if while_match.group(2) else 1000
            return LoopConfiguration(
                loop_type=LoopType.WHILE,
                condition=condition,
                max_iterations=max_iter
            )

        raise ValueError(f"Invalid loop format: {loop_str}")


class LoopExecutor:
    """Execute steps in a loop"""

    def __init__(self, ski_executor):
        """Initialize with reference to SKIExecutor"""
        self.ski_executor = ski_executor
        from .condition_evaluator import ConditionEvaluator
        self.condition_evaluator = ConditionEvaluator()

    def execute_loop(self, step: Dict[str, Any], loop_config: LoopConfiguration) -> List[Dict[str, Any]]:
        """Execute step in a loop based on configuration"""
        results = []

        if loop_config.loop_type == LoopType.FIXED:
            results = self._execute_fixed(step, loop_config)
        elif loop_config.loop_type == LoopType.FOR_EACH:
            results = self._execute_for_each(step, loop_config)
        elif loop_config.loop_type == LoopType.UNTIL:
            results = self._execute_until(step, loop_config)
        elif loop_config.loop_type == LoopType.WHILE:
            results = self._execute_while(step, loop_config)

        return results

    def _execute_fixed(self, step: Dict[str, Any], config: LoopConfiguration) -> List[Dict[str, Any]]:
        """Execute step fixed number of times"""
        results = []
        count = config.count or 0

        for i in range(count):
            self.ski_executor._variables[config.index_var] = i
            try:
                self.ski_executor.execute_step(step, f"loop_{i+1}")
                results.append({"iteration": i, "status": "pass"})
            except Exception as e:
                results.append({"iteration": i, "status": "fail", "error": str(e)})
                if config.break_on_fail:
                    break

        return results

    def _execute_for_each(self, step: Dict[str, Any], config: LoopConfiguration) -> List[Dict[str, Any]]:
        """Execute step for each item in list"""
        results = []
        items = config.items or []

        for i, item in enumerate(items):
            self.ski_executor._variables[config.item_var] = item
            self.ski_executor._variables[config.index_var] = i
            try:
                self.ski_executor.execute_step(step, f"loop_{i+1}")
                results.append({"iteration": i, "item": item, "status": "pass"})
            except Exception as e:
                results.append({"iteration": i, "item": item, "status": "fail", "error": str(e)})
                if config.break_on_fail:
                    break

        return results

    def _execute_until(self, step: Dict[str, Any], config: LoopConfiguration) -> List[Dict[str, Any]]:
        """Execute step until condition is true"""
        results = []
        iteration = 0

        while iteration < config.max_iterations:
            if self.condition_evaluator.evaluate(config.condition, self.ski_executor._variables):
                break

            self.ski_executor._variables[config.index_var] = iteration
            try:
                self.ski_executor.execute_step(step, f"loop_{iteration+1}")
                results.append({"iteration": iteration, "status": "pass"})
            except Exception as e:
                results.append({"iteration": iteration, "status": "fail", "error": str(e)})
                if config.break_on_fail:
                    break

            iteration += 1

        return results

    def _execute_while(self, step: Dict[str, Any], config: LoopConfiguration) -> List[Dict[str, Any]]:
        """Execute step while condition is true"""
        results = []
        iteration = 0

        while iteration < config.max_iterations:
            if not self.condition_evaluator.evaluate(config.condition, self.ski_executor._variables):
                break

            self.ski_executor._variables[config.index_var] = iteration
            try:
                self.ski_executor.execute_step(step, f"loop_{iteration+1}")
                results.append({"iteration": iteration, "status": "pass"})
            except Exception as e:
                results.append({"iteration": iteration, "status": "fail", "error": str(e)})
                if config.break_on_fail:
                    break

            iteration += 1

        return results
