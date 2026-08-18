"""Deterministic plan validation — makes no model call (docs/PLAN.md D-A2-2).

Verifies the plan references only real tools, covers every mandatory check,
and puts get_transaction_details first (every later step depends on facts
only it provides).
"""

from __future__ import annotations

from collections.abc import Callable

from surveillance.graph.state import SurveillanceState
from surveillance.schemas.plan import PlanCheck

MANDATORY_TOOLS = (
    "get_transaction_details",
    "get_applicable_role_limits",
    "get_compliance_rules",
    "rolling_90d_trading_volume",
    "insider_trading_baseline",
    "get_material_events",
)


def build_check_plan_node(
    known_tool_names: frozenset[str],
) -> Callable[[SurveillanceState], dict[str, object]]:
    def check_plan_node(state: SurveillanceState) -> dict[str, object]:
        plan = state["plan"]
        assert plan is not None
        tool_sequence = [step.tool for step in plan.steps]

        unknown_tools = sorted({t for t in tool_sequence if t not in known_tool_names})
        missing_checks = [t for t in MANDATORY_TOOLS if t not in tool_sequence]
        ordering_issues = []
        if tool_sequence and tool_sequence[0] != "get_transaction_details":
            ordering_issues.append("get_transaction_details must be the first step")

        ok = not unknown_tools and not missing_checks and not ordering_issues
        return {
            "plan_check": PlanCheck(
                ok=ok,
                missing_checks=missing_checks,
                unknown_tools=unknown_tools,
                ordering_issues=ordering_issues,
            )
        }

    return check_plan_node
