"""Bounded replan — one LLM call with the check_plan feedback folded in.
Capped at 1 attempt by `graph/edges.py` (docs/PLAN.md D-A2-2)."""

from __future__ import annotations

from collections.abc import Callable

from surveillance.graph.protocols import PlannerChain
from surveillance.graph.state import SurveillanceState


def _feedback_text(state: SurveillanceState) -> str:
    check = state["plan_check"]
    assert check is not None
    parts = []
    if check.unknown_tools:
        parts.append(f"unknown tools referenced: {check.unknown_tools}")
    if check.missing_checks:
        parts.append(f"missing mandatory tools: {check.missing_checks}")
    if check.ordering_issues:
        parts.append(f"ordering issues: {check.ordering_issues}")
    return "; ".join(parts)


def build_replan_node(
    planner_chain: PlannerChain,
) -> Callable[[SurveillanceState], dict[str, object]]:
    def replan_node(state: SurveillanceState) -> dict[str, object]:
        plan = planner_chain.invoke(
            {"accession_number": state["accession_number"], "feedback": _feedback_text(state)}
        )
        return {"plan": plan, "replan_count": state["replan_count"] + 1}

    return replan_node
