"""Orchestration: state -> state delta. No prompts, no LLM calls directly —
delegates to the planner chain (docs/PLAN.md §9.3)."""

from __future__ import annotations

from collections.abc import Callable

from surveillance.graph.protocols import PlannerChain
from surveillance.graph.state import SurveillanceState


def build_plan_node(
    planner_chain: PlannerChain,
) -> Callable[[SurveillanceState], dict[str, object]]:
    def plan_node(state: SurveillanceState) -> dict[str, object]:
        plan = planner_chain.invoke({"accession_number": state["accession_number"], "feedback": ""})
        return {"plan": plan}

    return plan_node
