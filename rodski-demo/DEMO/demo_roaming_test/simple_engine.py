"""Demo roaming engine for --roam-engine acceptance test.

Exports create_engine() as required by the --roam-engine CLI option.
Tries D002 as a data variant of any step that currently uses D001,
then stops after one variant (keeps the demo deterministic and fast).
"""
from __future__ import annotations

from typing import Any, Dict, List


class DemoDataVariantEngine:
    """Replace D001 → D002 in the first matching step, then stop."""

    def __init__(self) -> None:
        self._tried = False

    def next_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._tried:
            return {"stop": True, "stopped_reason": "manual_stop"}
        original_steps: List[Dict[str, Any]] = list(context.get("original_steps") or [])
        for step in original_steps:
            if str(step.get("data", "")) == "D001":
                self._tried = True
                return {
                    "next_action": {
                        "action": str(step.get("action", "type")),
                        "model": str(step.get("model", "")),
                        "data": "D002",
                    },
                    "confidence": 1.0,
                    "reversible": True,
                }
        return {"stop": True, "stopped_reason": "manual_stop"}


def create_engine() -> DemoDataVariantEngine:
    return DemoDataVariantEngine()
