"""Selection utilities for applying parsed Plan XML to parsed RodSki cases."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


def compile_from_selector(
    scenario_metadata: List[Dict[str, Any]],
    *,
    filter_tags: Optional[List[str]] = None,
    filter_group: Optional[str] = None,
    exclude_tags: Optional[List[str]] = None,
    filter_priority: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Compile a selection result from CLI selector filters.

    Args:
        scenario_metadata: Output of CaseParser.collect_scenario_metadata_from_cases().
        filter_tags: OR-match against effective_tags (--tag smoke,p0).
        filter_group: Exact match against scenario_group (--group negative).
        exclude_tags: Exclude scenarios whose effective_tags hit any of these (--exclude-tag slow).
        filter_priority: Filter by case_priority first (--priority P0).

    Returns:
        Dict with 'selected', 'skipped', 'stale_references' (stale always empty).
    """
    selected: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    candidates = list(scenario_metadata)

    # Step 1: filter by priority at case level
    if filter_priority:
        priority_upper = filter_priority.upper()
        candidates = [m for m in candidates if (m.get("case_priority") or "").upper() == priority_upper]

    # Step 2: filter by tags (OR match)
    if filter_tags:
        tags_set = set(filter_tags)
        candidates = [m for m in candidates if tags_set & set(m.get("effective_tags") or [])]

    # Step 3: filter by group (exact match)
    if filter_group:
        candidates = [m for m in candidates if m.get("scenario_group") == filter_group]

    # Step 4: exclude tags
    if exclude_tags:
        exclude_set = set(exclude_tags)
        candidates = [m for m in candidates if not (exclude_set & set(m.get("effective_tags") or []))]

    for m in candidates:
        selected.append({
            "type": "scenario",
            "case_id": m["case_id"],
            "scenario_id": m["scenario_id"],
            "reason": "selector",
        })

    return {"selected": selected, "skipped": skipped, "stale_references": []}


def check_plan_selector_conflict(
    plan_path: Optional[str],
    selector_filters: Dict[str, Any],
) -> None:
    """Raise ValueError if plan_path and selector filters are both specified.

    Args:
        plan_path: The @plan_id path (None or empty means no plan).
        selector_filters: Dict with keys filter_tags, filter_group, exclude_tags, filter_priority.

    Raises:
        ValueError: When plan_path is non-empty and any selector filter is active.
    """
    if not plan_path:
        return

    active_keys = [
        k for k in ("filter_tags", "filter_group", "exclude_tags", "filter_priority")
        if selector_filters.get(k)
    ]
    if not active_keys:
        return

    raise ValueError(
        "@plan_id 与 --tag/--group/--exclude-tag/--priority 是两类执行范围来源，不能同时使用。\n"
        "替代方式：\n"
        "  1. 仅使用 @plan_id 指定执行范围（在 plan XML 中配置 case/scenario）\n"
        "  2. 仅使用 --tag/--group/--exclude-tag/--priority 动态筛选\n"
        "  3. 在 plan XML 中为 scenario 设置 tag，然后仅用 @plan_id 执行"
    )


@dataclass
class TestPlanSelection:
    """Apply a parsed test plan to parsed CaseParser output."""

    __test__ = False

    cases: List[Dict[str, Any]]
    plan: Dict[str, Any]
    disabled_case_ids: Set[str] = field(default_factory=set)
    disabled_scenario_ids: Set[Tuple[str, str]] = field(default_factory=set)

    def __init__(
        self,
        cases: List[Dict[str, Any]],
        plan: Dict[str, Any],
        disabled_case_ids: Optional[Iterable[str]] = None,
        disabled_scenario_ids: Optional[Iterable[Tuple[str, str]]] = None,
    ):
        self.cases = cases
        self.plan = plan
        self.disabled_case_ids = set(disabled_case_ids or [])
        self.disabled_scenario_ids = set(disabled_scenario_ids or [])

    def select(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return selected executable entries, skipped entries, and stale references."""
        selected: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        stale_references: List[Dict[str, Any]] = []

        if self.plan.get("execute", "是") == "否":
            for case in self.cases:
                skipped.append(self._skip_case(case, "plan_execute_false"))
            return {"selected": selected, "skipped": skipped, "stale_references": stale_references}

        case_index = {self._case_id(case): case for case in self.cases}
        plan_cases = self.plan.get("cases", []) or []
        plan_case_index = {case.get("id", ""): case for case in plan_cases}

        for plan_case in plan_cases:
            case_id = plan_case.get("id", "")
            case = case_index.get(case_id)
            if case is None:
                stale_references.append({"type": "case", "case_id": case_id, "reason": "not_found"})
                continue
            self._apply_plan_case(case, plan_case, selected, skipped, stale_references)

        if self.plan.get("kind") == "suite" and self.plan.get("default_execute", "否") == "是":
            for case in self.cases:
                case_id = self._case_id(case)
                if case_id in plan_case_index:
                    self._include_unmentioned_in_explicit_case(
                        case,
                        plan_case_index[case_id],
                        selected,
                        skipped,
                    )
                else:
                    self._select_whole_case(case, selected, skipped, reason_prefix="default_execute")

        return {"selected": selected, "skipped": skipped, "stale_references": stale_references}

    def _apply_plan_case(
        self,
        case: Dict[str, Any],
        plan_case: Dict[str, Any],
        selected: List[Dict[str, Any]],
        skipped: List[Dict[str, Any]],
        stale_references: List[Dict[str, Any]],
    ) -> None:
        case_id = self._case_id(case)
        if plan_case.get("execute", "是") == "否":
            skipped.append(self._skip_case(case, "plan_case_execute_false"))
            return
        if case_id in self.disabled_case_ids:
            skipped.append(self._skip_case(case, "case_execute_false"))
            return

        plan_scenarios = plan_case.get("scenarios", []) or []
        if not plan_scenarios:
            self._select_whole_case(case, selected, skipped, reason_prefix="plan_case")
            return

        scenario_index = {scenario.get("id", ""): scenario for scenario in self._case_scenarios(case)}
        for plan_scenario in plan_scenarios:
            scenario_id = plan_scenario.get("id", "")
            scenario = scenario_index.get(scenario_id)
            if scenario is None:
                stale_references.append({
                    "type": "scenario",
                    "case_id": case_id,
                    "scenario_id": scenario_id,
                    "reason": "not_found",
                })
                continue
            self._apply_plan_scenario(case, scenario, plan_scenario, selected, skipped, stale_references)

    def _include_unmentioned_in_explicit_case(
        self,
        case: Dict[str, Any],
        plan_case: Dict[str, Any],
        selected: List[Dict[str, Any]],
        skipped: List[Dict[str, Any]],
    ) -> None:
        case_id = self._case_id(case)
        if plan_case.get("execute", "是") == "否" or case_id in self.disabled_case_ids:
            return
        mentioned = {scenario.get("id", "") for scenario in (plan_case.get("scenarios", []) or [])}
        for scenario in self._case_scenarios(case):
            scenario_id = scenario.get("id", "")
            if scenario_id not in mentioned:
                self._select_scenario(case, scenario, selected, skipped, reason_prefix="default_execute")

    def _apply_plan_scenario(
        self,
        case: Dict[str, Any],
        scenario: Dict[str, Any],
        plan_scenario: Dict[str, Any],
        selected: List[Dict[str, Any]],
        skipped: List[Dict[str, Any]],
        stale_references: List[Dict[str, Any]],
    ) -> None:
        case_id = self._case_id(case)
        scenario_id = scenario.get("id", "")
        if plan_scenario.get("execute", "是") == "否":
            skipped.append(self._skip_scenario(case, scenario, "plan_scenario_execute_false"))
            return
        if (case_id, scenario_id) in self.disabled_scenario_ids:
            skipped.append(self._skip_scenario(case, scenario, "scenario_execute_false"))
            return

        plan_steps = plan_scenario.get("steps", []) or []
        if not plan_steps:
            self._select_scenario(case, scenario, selected, skipped, reason_prefix="plan_scenario")
            return

        steps = scenario.get("steps", []) or []
        for plan_step in plan_steps:
            step_no = plan_step.get("no")
            if not isinstance(step_no, int) or step_no < 1 or step_no > len(steps):
                stale_references.append({
                    "type": "step",
                    "case_id": case_id,
                    "scenario_id": scenario_id,
                    "step_no": step_no,
                    "reason": "not_found",
                })
                continue
            step = steps[step_no - 1]
            if plan_step.get("execute", "是") == "否":
                skipped.append(self._skip_step(case, scenario, step_no, step, "plan_step_execute_false"))
                continue
            selected.append(self._step_entry(case, scenario, step_no, step, "plan_step"))

    def _select_whole_case(
        self,
        case: Dict[str, Any],
        selected: List[Dict[str, Any]],
        skipped: List[Dict[str, Any]],
        reason_prefix: str,
    ) -> None:
        case_id = self._case_id(case)
        if case_id in self.disabled_case_ids:
            skipped.append(self._skip_case(case, "case_execute_false"))
            return
        scenarios = self._case_scenarios(case)
        if scenarios:
            for scenario in scenarios:
                self._select_scenario(case, scenario, selected, skipped, reason_prefix=reason_prefix)
        else:
            selected.append({"type": "case", "case_id": case_id, "case": case, "reason": reason_prefix})

    def _select_scenario(
        self,
        case: Dict[str, Any],
        scenario: Dict[str, Any],
        selected: List[Dict[str, Any]],
        skipped: List[Dict[str, Any]],
        reason_prefix: str,
    ) -> None:
        case_id = self._case_id(case)
        scenario_id = scenario.get("id", "")
        if (case_id, scenario_id) in self.disabled_scenario_ids:
            skipped.append(self._skip_scenario(case, scenario, "scenario_execute_false"))
            return
        selected.append({
            "type": "scenario",
            "case_id": case_id,
            "scenario_id": scenario_id,
            "case": case,
            "scenario": scenario,
            "reason": reason_prefix,
        })

    @staticmethod
    def _case_id(case: Dict[str, Any]) -> str:
        return case.get("case_id") or case.get("id") or ""

    @staticmethod
    def _case_scenarios(case: Dict[str, Any]) -> List[Dict[str, Any]]:
        return list(case.get("scenarios", []) or [])

    def _skip_case(self, case: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {"type": "case", "case_id": self._case_id(case), "case": case, "reason": reason}

    def _skip_scenario(self, case: Dict[str, Any], scenario: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "type": "scenario",
            "case_id": self._case_id(case),
            "scenario_id": scenario.get("id", ""),
            "case": case,
            "scenario": scenario,
            "reason": reason,
        }

    def _skip_step(
        self,
        case: Dict[str, Any],
        scenario: Dict[str, Any],
        step_no: int,
        step: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        entry = self._step_entry(case, scenario, step_no, step, reason)
        entry["reason"] = reason
        return entry

    def _step_entry(
        self,
        case: Dict[str, Any],
        scenario: Dict[str, Any],
        step_no: int,
        step: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "type": "step",
            "case_id": self._case_id(case),
            "scenario_id": scenario.get("id", ""),
            "step_no": step_no,
            "case": case,
            "scenario": scenario,
            "step": step,
            "reason": reason,
        }
