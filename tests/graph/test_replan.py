from surveillance.graph.nodes.replan import build_replan_node
from surveillance.schemas.plan import InvestigationPlan, PlanCheck, PlanStep

from ._state_helpers import make_state


class _StubPlannerChain:
    def __init__(self) -> None:
        self.last_input: dict[str, str] | None = None

    def invoke(self, input_: dict[str, str]) -> InvestigationPlan:
        self.last_input = input_
        return InvestigationPlan(steps=[PlanStep(order=1, objective="x", tool="t", why="y")])


def test_replan_increments_count_and_passes_feedback() -> None:
    stub = _StubPlannerChain()
    node = build_replan_node(stub)
    state = make_state(
        plan_check=PlanCheck(ok=False, missing_checks=["get_compliance_rules"]),
        replan_count=0,
    )
    result = node(state)
    assert result["replan_count"] == 1
    assert stub.last_input is not None
    assert "get_compliance_rules" in stub.last_input["feedback"]
