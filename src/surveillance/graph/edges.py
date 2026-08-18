"""Routing predicates — one small function each (docs/PLAN.md §9.3)."""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage

from surveillance.graph.budget import budget_breach_reason
from surveillance.graph.state import SurveillanceState

MAX_REPLANS = 1
MAX_EVIDENCE_PASSES = 2


def route_after_check_plan(state: SurveillanceState) -> Literal["investigate", "replan"]:
    check = state["plan_check"]
    assert check is not None
    if check.ok:
        return "investigate"
    if state["replan_count"] < MAX_REPLANS:
        return "replan"
    # Replan budget spent and still imperfect: proceed best-effort rather than
    # deadlock the graph. The persisting issues are visible in plan_check.
    return "investigate"


def route_after_agent(
    state: SurveillanceState,
) -> Literal["tools", "draft_finding", "budget_exceeded"]:
    if budget_breach_reason(state["messages"], state["started_at"]) is not None:
        return "budget_exceeded"
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "draft_finding"


def route_after_grounding(state: SurveillanceState) -> Literal["investigate", "publish"]:
    report = state["grounding_report"]
    assert report is not None
    if report.unsupported == 0:
        return "publish"
    if state["evidence_pass"] < MAX_EVIDENCE_PASSES:
        return "investigate"
    # Evidence-pass budget spent and still unsupported claims remain: publish
    # anyway rather than deadlock the graph — the report documents exactly
    # what stayed unsupported (docs/PLAN.md §5.1, "capped at evidence_pass ≤ 2").
    return "publish"
