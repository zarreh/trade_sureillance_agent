from surveillance.graph.nodes.check_plan import build_check_plan_node
from surveillance.schemas.plan import InvestigationPlan, PlanCheck, PlanStep

from ._state_helpers import make_state

KNOWN_TOOLS = frozenset(
    {
        "get_transaction_details",
        "get_applicable_role_limits",
        "get_compliance_rules",
        "rolling_90d_trading_volume",
        "insider_trading_baseline",
        "get_material_events",
    }
)


def _plan(tool_names: list[str]) -> InvestigationPlan:
    return InvestigationPlan(
        steps=[
            PlanStep(order=i, objective="x", tool=name, why="y")
            for i, name in enumerate(tool_names, start=1)
        ]
    )


def _check(result: dict[str, object]) -> PlanCheck:
    check = result["plan_check"]
    assert isinstance(check, PlanCheck)
    return check


def test_complete_correctly_ordered_plan_passes() -> None:
    node = build_check_plan_node(KNOWN_TOOLS)
    plan = _plan(["get_transaction_details", *sorted(KNOWN_TOOLS - {"get_transaction_details"})])
    result = node(make_state(plan=plan))
    assert _check(result).ok is True


def test_rejects_unknown_tool() -> None:
    node = build_check_plan_node(KNOWN_TOOLS)
    plan = _plan(
        [
            "get_transaction_details",
            "made_up_tool",
            *sorted(KNOWN_TOOLS - {"get_transaction_details"}),
        ]
    )
    result = node(make_state(plan=plan))
    check = _check(result)
    assert check.ok is False
    assert "made_up_tool" in check.unknown_tools


def test_rejects_missing_mandatory_tool() -> None:
    node = build_check_plan_node(KNOWN_TOOLS)
    plan = _plan(["get_transaction_details", "get_compliance_rules"])
    result = node(make_state(plan=plan))
    check = _check(result)
    assert check.ok is False
    assert "get_applicable_role_limits" in check.missing_checks


def test_rejects_wrong_first_step() -> None:
    node = build_check_plan_node(KNOWN_TOOLS)
    plan = _plan(["get_applicable_role_limits", "get_transaction_details"])
    result = node(make_state(plan=plan))
    check = _check(result)
    assert check.ok is False
    assert check.ordering_issues
