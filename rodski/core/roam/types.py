"""Shared contracts for deterministic roaming sessions."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Protocol, Set


STOP_BUDGET_VARIANTS = "budget_variants"
STOP_BUDGET_DURATION = "budget_duration"
STOP_BUDGET_TOKEN = "budget_token"
STOP_LOW_CONFIDENCE = "low_confidence"
STOP_NO_HANDLER = "no_handler"
STOP_MANUAL = "manual_stop"


def action_fingerprint(action: Mapping[str, Any]) -> str:
    """Return the stable de-duplication key required by the roaming design."""
    identity = {
        "action": action.get("action", ""),
        "model": action.get("model", ""),
        "data": action.get("data", ""),
    }
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RoamBudget:
    """Hard limits for one roaming session.

    Both the public XML-style names and Python snake_case names are accepted by
    :meth:`from_mapping`, which keeps the executor/CLI integration mechanical.
    """

    max_variants_per_case: int = 5
    max_duration_seconds: float = 120.0
    min_confidence_to_act: float = 0.6
    max_token_budget: Optional[int] = 20000
    max_cost_usd: Optional[float] = 0.5

    def __post_init__(self) -> None:
        if self.max_variants_per_case < 0:
            raise ValueError("max_variants_per_case must be >= 0")
        if self.max_duration_seconds < 0:
            raise ValueError("max_duration_seconds must be >= 0")
        if not 0.0 <= self.min_confidence_to_act <= 1.0:
            raise ValueError("min_confidence_to_act must be between 0 and 1")
        if self.max_token_budget is not None and self.max_token_budget < 0:
            raise ValueError("max_token_budget must be >= 0 or None")
        if self.max_cost_usd is not None and self.max_cost_usd < 0:
            raise ValueError("max_cost_usd must be >= 0 or None")

    @classmethod
    def from_mapping(cls, values: Optional[Mapping[str, Any]]) -> "RoamBudget":
        if not values:
            return cls()

        def value(snake_name: str, xml_name: str, default: Any) -> Any:
            raw = values.get(snake_name, values.get(xml_name, default))
            return default if raw == "" else raw

        token_value = value("max_token_budget", "MaxTokenBudget", cls.max_token_budget)
        cost_value = value("max_cost_usd", "MaxCostUsd", cls.max_cost_usd)
        return cls(
            max_variants_per_case=int(
                value(
                    "max_variants_per_case",
                    "MaxVariantsPerCase",
                    cls.max_variants_per_case,
                )
            ),
            max_duration_seconds=float(
                value(
                    "max_duration_seconds",
                    "MaxDurationSeconds",
                    cls.max_duration_seconds,
                )
            ),
            min_confidence_to_act=float(
                value(
                    "min_confidence_to_act",
                    "MinConfidenceToAct",
                    cls.min_confidence_to_act,
                )
            ),
            max_token_budget=None if token_value is None else int(token_value),
            max_cost_usd=None if cost_value is None else float(cost_value),
        )


@dataclass(frozen=True)
class RoamDecision:
    """One decision returned by a roaming engine."""

    next_action: Optional[Dict[str, Any]] = None
    exploration_tier: str = "data"
    action_kind: str = "data_variant"
    reversible: bool = True
    confidence: float = 1.0
    rationale: str = ""
    test_map_node_ref: Optional[str] = None
    stop: bool = False
    stopped_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "next_action": dict(self.next_action) if self.next_action else None,
            "exploration_tier": self.exploration_tier,
            "action_kind": self.action_kind,
            "reversible": self.reversible,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "test_map_node_ref": self.test_map_node_ref,
            "stop": self.stop,
        }
        if self.stopped_reason:
            result["stopped_reason"] = self.stopped_reason
        result.update(self.metadata)
        return result


@dataclass(frozen=True)
class RoamActionVerdict:
    """Whether a decision may be executed by the deterministic core."""

    execute: bool
    record_only: bool = False
    reason: str = ""
    stopped_reason: str = ""
    action_hash: str = ""


class RoamSessionGuard:
    """Centralize budget, confidence, reversibility, and de-duplication rules."""

    def __init__(
        self,
        budget: Optional[RoamBudget] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.budget = budget or RoamBudget()
        self._clock = clock
        self._started_at = clock()
        self.variants_tried = 0
        self.tokens_used = 0
        self.cost_usd = 0.0
        self.stopped_reason = ""
        self._seen_action_hashes: Set[str] = set()

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self._clock() - self._started_at)

    @property
    def seen_action_hashes(self) -> Set[str]:
        return set(self._seen_action_hashes)

    def record_usage(self, tokens: int = 0, cost_usd: float = 0.0) -> None:
        self.tokens_used += max(0, int(tokens))
        self.cost_usd += max(0.0, float(cost_usd))

    def finish(self, reason: str = STOP_MANUAL) -> str:
        if not self.stopped_reason:
            self.stopped_reason = reason
        return self.stopped_reason

    def check_budget(self) -> str:
        """Return a stopped_reason when any hard budget is exhausted."""
        if self.stopped_reason:
            return self.stopped_reason
        if self.variants_tried >= self.budget.max_variants_per_case:
            return self.finish(STOP_BUDGET_VARIANTS)
        if self.duration_seconds >= self.budget.max_duration_seconds:
            return self.finish(STOP_BUDGET_DURATION)
        if (
            self.budget.max_token_budget is not None
            and self.tokens_used >= self.budget.max_token_budget
        ):
            return self.finish(STOP_BUDGET_TOKEN)
        if (
            self.budget.max_cost_usd is not None
            and self.cost_usd >= self.budget.max_cost_usd
        ):
            # The approved MVP stopped_reason vocabulary groups both LLM usage
            # limits under budget_token.
            return self.finish(STOP_BUDGET_TOKEN)
        return ""

    def consider(self, decision: Mapping[str, Any]) -> RoamActionVerdict:
        """Apply all safety gates before the executor calls ``_run_steps``."""
        budget_reason = self.check_budget()
        if budget_reason:
            return RoamActionVerdict(False, reason=budget_reason, stopped_reason=budget_reason)

        if decision.get("stop"):
            reason = str(decision.get("stopped_reason") or STOP_MANUAL)
            self.finish(reason)
            return RoamActionVerdict(False, reason=reason, stopped_reason=reason)

        action = decision.get("next_action")
        if not isinstance(action, Mapping) or not action.get("action"):
            reason = self.finish(STOP_MANUAL)
            return RoamActionVerdict(False, reason="no_action", stopped_reason=reason)

        confidence = float(decision.get("confidence", 0.0))
        action_hash = action_fingerprint(action)
        if confidence < self.budget.min_confidence_to_act:
            reason = self.finish(STOP_LOW_CONFIDENCE)
            self._seen_action_hashes.add(action_hash)
            return RoamActionVerdict(
                False,
                record_only=True,
                reason=STOP_LOW_CONFIDENCE,
                stopped_reason=reason,
                action_hash=action_hash,
            )

        if action_hash in self._seen_action_hashes:
            return RoamActionVerdict(False, reason="duplicate", action_hash=action_hash)

        self._seen_action_hashes.add(action_hash)
        if not bool(decision.get("reversible", False)):
            return RoamActionVerdict(
                False,
                record_only=True,
                reason="irreversible",
                action_hash=action_hash,
            )

        self.variants_tried += 1
        return RoamActionVerdict(True, action_hash=action_hash)

    def build_summary(
        self,
        base_case_id: str,
        triggered_by: str,
        findings: Optional[Iterable[Mapping[str, Any]]] = None,
        test_map_delta: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the minimum MVP result dictionary required by iteration-61."""
        return {
            "base_case_id": base_case_id,
            "triggered_by": triggered_by,
            "variants_tried": self.variants_tried,
            "duration_seconds": round(self.duration_seconds, 3),
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 6),
            "stopped_reason": self.stopped_reason,
            "findings": [dict(item) for item in (findings or [])],
            "test_map_delta": dict(test_map_delta or {}),
        }


# ---------------------------------------------------------------------------
# Injection contract — BaseRoamDecisionEngine (migrated from engine.py)
# ---------------------------------------------------------------------------

class BaseRoamDecisionEngine(Protocol):
    """Minimal injection contract shared by core and agent-provided engines."""

    def next_action(self, context: Mapping[str, Any]) -> Dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Context type contracts (RoamContext, BusinessRoamContext)
# ---------------------------------------------------------------------------

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # type: ignore[no-redef]


class RoamContext(TypedDict, total=False):
    """Core context dict passed by the executor to every roaming engine call."""

    case_id: str
    case_title: str
    case_description: str
    original_steps: List[Dict[str, Any]]
    model_elements: Dict[str, Any]
    screenshot_path: str
    current_url: Optional[str]
    page_identity: Optional[Dict[str, Any]]
    ax_tree: None
    test_map: Dict[str, Any]
    history: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]


class BusinessRoamContext(RoamContext, total=False):
    """Extended context for business-level roaming engines (rodski-agent layer)."""

    module_case_summaries: List[Dict[str, Any]]
    business_rules: List[Dict[str, Any]]
    state_machine: Dict[str, Any]
    code_evidence: List[Dict[str, Any]]
    source_of_truth_hints: List[Dict[str, Any]]
    current_url: str  # type: ignore[override]
    page_identity: Dict[str, Any]  # type: ignore[override]
    visible_state: Dict[str, Any]
    base_step_results: List[Dict[str, Any]]
    charter: Dict[str, Any]
    oracle_plan: List[Dict[str, Any]]
    environment_constraints: Dict[str, Any]
    forbidden_actions: List[str]
    prior_findings: List[Dict[str, Any]]
