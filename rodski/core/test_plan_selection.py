"""Selection utilities for applying parsed Plan XML to parsed RodSki cases."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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


def _is_active(value) -> bool:
    """判断 selector filter 值是否活跃（非空、非 None、非空列表）。"""
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    return bool(value)


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
        if _is_active(selector_filters.get(k))
    ]
    if not active_keys:
        return

    raise ValueError(
        "@plan_id 与 --tag/--group/--exclude-tag/--priority 是两类执行范围来源，不能同时使用。\n"
        "请使用以下方式之一：\n"
        "  1. rodski run @<plan_id>\n"
        "  2. rodski run --tag <tag>\n"
        "  3. rodski plan create <plan_id> --from-tag <tag> 后再 rodski run @<plan_id>"
    )


@dataclass
class TestPlanSelection:
    """Apply a parsed test plan to parsed CaseParser output."""

    __test__ = False

    cases: List[Dict[str, Any]]
    plan: Dict[str, Any]
    disabled_case_ids: Set[str] = field(default_factory=set)
    disabled_scenario_ids: Set[Tuple[str, str]] = field(default_factory=set)
    module_dir: Optional[Path] = None

    def __init__(
        self,
        cases: List[Dict[str, Any]],
        plan: Dict[str, Any],
        disabled_case_ids: Optional[Iterable[str]] = None,
        disabled_scenario_ids: Optional[Iterable[Tuple[str, str]]] = None,
        module_dir: Optional[Path] = None,
    ):
        self.cases = cases
        self.plan = plan
        self.disabled_case_ids = set(disabled_case_ids or [])
        self.disabled_scenario_ids = set(disabled_scenario_ids or [])
        self.module_dir = Path(module_dir) if module_dir else None

    def _module_case_file_count(self) -> int:
        """Number of case files in the module.

        Counted from disk when module_dir is known, so files holding only
        execute="否" cases (absent from parsed cases) still count.
        """
        if self.module_dir is not None and (self.module_dir / "case").is_dir():
            from .case_discovery import discover_case_files
            return len(discover_case_files(self.module_dir / "case"))
        return len({case.get("case_file", "") for case in self.cases})

    def select(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return selected executable entries, skipped entries, and stale references."""
        selected: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        stale_references: List[Dict[str, Any]] = []

        if self.plan.get("execute", "是") == "否":
            for case in self.cases:
                skipped.append(self._skip_case(case, "plan_execute_false"))
            return {"selected": selected, "skipped": skipped, "stale_references": stale_references}

        # Build case_uid -> case index (v11.5.0: case_uid = f"{case_file}::{case_id}")
        case_index = {self._case_uid(case): case for case in self.cases}
        # Build case_id -> [case_uid, ...] for single-file compatibility
        case_id_to_uids: Dict[str, List[str]] = {}
        for case in self.cases:
            case_id = self._case_id(case)
            case_uid = self._case_uid(case)
            case_id_to_uids.setdefault(case_id, []).append(case_uid)

        module_case_file_count = self._module_case_file_count()

        # Handle case_dir elements (v11.5.0)
        case_dir_selected = self._handle_case_dirs(selected, skipped, stale_references)

        plan_cases = self.plan.get("cases", []) or []
        plan_case_index = {}
        for plan_case in plan_cases:
            case_id = plan_case.get("id", "")
            file_attr = plan_case.get("file", "")
            if file_attr:
                # Explicit file: use case_uid
                case_uid = f"{file_attr}::{case_id}"
                plan_case_index[case_uid] = plan_case
            else:
                # No file: store by case_id for compatibility check
                plan_case_index[case_id] = plan_case

        for plan_case in plan_cases:
            case_id = plan_case.get("id", "")
            file_attr = plan_case.get("file", "")

            if file_attr:
                # Explicit file specified
                case_uid = f"{file_attr}::{case_id}"
                case = case_index.get(case_uid)
                if case is None:
                    stale_references.append({
                        "type": "case",
                        "case_id": case_id,
                        "case_file": file_attr,
                        "reason": "not_found",
                    })
                    continue
                self._apply_plan_case(case, plan_case, selected, skipped, stale_references)
            else:
                # No file: only compatible when the module has exactly one case file
                # (Owner decision C2); otherwise SKI207 asks for an explicit file.
                # An id found in no file is a stale reference, not an ambiguity.
                candidate_uids = case_id_to_uids.get(case_id, [])
                if not candidate_uids:
                    stale_references.append({
                        "type": "case",
                        "case_id": case_id,
                        "reason": "not_found",
                    })
                    continue
                if module_case_file_count > 1:
                    from .exceptions import PlanCaseFileRequiredError
                    candidates = [uid.split("::", 1)[0] for uid in candidate_uids]
                    raise PlanCaseFileRequiredError(case_id=case_id, candidates=candidates)
                case = case_index[candidate_uids[0]]
                self._apply_plan_case(case, plan_case, selected, skipped, stale_references)

        if self.plan.get("kind") == "suite" and self.plan.get("default_execute", "否") == "是":
            for case in self.cases:
                case_uid = self._case_uid(case)
                case_id = self._case_id(case)
                # Check if already selected by case_dir or explicit case
                if case_uid in case_dir_selected:
                    continue
                # Check explicit case entries
                if case_uid in plan_case_index:
                    self._include_unmentioned_in_explicit_case(
                        case,
                        plan_case_index[case_uid],
                        selected,
                        skipped,
                    )
                elif case_id in plan_case_index and len(case_id_to_uids.get(case_id, [])) == 1:
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
        if case_id in self.disabled_case_ids:
            skipped.append(self._skip_case(case, "xml_case_execute_false"))
            return
        if plan_case.get("execute", "是") == "否":
            skipped.append(self._skip_case(case, "plan_case_execute_false"))
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
            selected.append({
                "type": "case",
                "case_id": case_id,
                "case_file": case.get("case_file", ""),
                "case": case,
                "reason": reason_prefix
            })

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
            "case_file": case.get("case_file", ""),
            "scenario_id": scenario_id,
            "case": case,
            "scenario": scenario,
            "reason": reason_prefix,
        })

    def _handle_case_dirs(
        self,
        selected: List[Dict[str, Any]],
        skipped: List[Dict[str, Any]],
        stale_references: List[Dict[str, Any]],
    ) -> Set[str]:
        """处理 case_dir 元素，返回已选中的 case_uid 集合。"""
        case_dir_selected: Set[str] = set()
        case_dirs = self.plan.get("case_dirs", []) or []
        if not case_dirs or not self.module_dir:
            return case_dir_selected

        from pathlib import Path
        try:
            from .case_discovery import discover_case_files
        except ImportError:
            from rodski.core.case_discovery import discover_case_files

        for case_dir_entry in case_dirs:
            dir_path = case_dir_entry.get("path", "").strip()
            execute = case_dir_entry.get("execute", "是").strip()

            if execute == "否":
                continue

            # Resolve directory path
            if dir_path == "":
                # Empty string means entire case/ directory
                target_dir = self.module_dir / "case"
            else:
                target_dir = self.module_dir / "case" / dir_path

            if not target_dir.is_dir():
                stale_references.append({
                    "type": "case_dir",
                    "path": dir_path,
                    "reason": "not_found",
                })
                continue

            # Discover cases in this directory
            case_files = discover_case_files(target_dir)
            for case_file_path in case_files:
                # Match by case_file (确保跨平台路径一致：统一转为 POSIX)
                try:
                    rel_path = case_file_path.relative_to(self.module_dir / "case").as_posix()
                except ValueError:
                    # 兜底：绝对路径比较
                    rel_path = case_file_path.resolve().relative_to((self.module_dir / "case").resolve()).as_posix()

                # 一个文件可能包含多个 execute="是" 的用例，全部纳入（不能 break 提前退出）
                already_selected_uids = {self._case_uid(c.get("case", {})) for c in selected}
                for case in self.cases:
                    case_file = case.get("case_file", "")
                    if case_file != rel_path:
                        continue
                    case_uid = self._case_uid(case)
                    case_dir_selected.add(case_uid)
                    if case_uid not in already_selected_uids:
                        self._select_whole_case(case, selected, skipped, reason_prefix="case_dir")
                        already_selected_uids.add(case_uid)

        return case_dir_selected

    @staticmethod
    def _case_uid(case: Dict[str, Any]) -> str:
        """Return case_uid (case_file::case_id) for v11.5.0 nested directory support."""
        case_file = case.get("case_file", "")
        case_id = case.get("case_id") or case.get("id") or ""
        if case_file:
            return f"{case_file}::{case_id}"
        # Fallback for cases without case_file (should not happen in v11.5.0+)
        return case_id

    @staticmethod
    def _case_id(case: Dict[str, Any]) -> str:
        return case.get("case_id") or case.get("id") or ""

    @staticmethod
    def _case_scenarios(case: Dict[str, Any]) -> List[Dict[str, Any]]:
        return list(case.get("scenarios", []) or [])

    def _skip_case(self, case: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "type": "case",
            "case_id": self._case_id(case),
            "case_file": case.get("case_file", ""),
            "case": case,
            "reason": reason
        }

    def _skip_scenario(self, case: Dict[str, Any], scenario: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "type": "scenario",
            "case_id": self._case_id(case),
            "case_file": case.get("case_file", ""),
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
            "case_file": case.get("case_file", ""),
            "scenario_id": scenario.get("id", ""),
            "step_no": step_no,
            "case": case,
            "scenario": scenario,
            "step": step,
            "reason": reason,
        }
