import time

from langchain_core.messages import AIMessage

from surveillance.graph.edges import route_after_agent, route_after_check_plan
from surveillance.schemas.plan import PlanCheck

from ._state_helpers import make_state


def test_route_after_check_plan_ok_goes_to_investigate() -> None:
    state = make_state(plan_check=PlanCheck(ok=True), replan_count=0)
    assert route_after_check_plan(state) == "investigate"


def test_route_after_check_plan_not_ok_replans_once() -> None:
    state = make_state(plan_check=PlanCheck(ok=False, missing_checks=["x"]), replan_count=0)
    assert route_after_check_plan(state) == "replan"


def test_route_after_check_plan_gives_up_after_max_replans() -> None:
    state = make_state(plan_check=PlanCheck(ok=False, missing_checks=["x"]), replan_count=1)
    assert route_after_check_plan(state) == "investigate"


def test_route_after_agent_routes_to_tools_when_tool_calls_present() -> None:
    ai = AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "1"}])
    state = make_state(messages=[ai], started_at=time.time())
    assert route_after_agent(state) == "tools"


def test_route_after_agent_routes_to_draft_finding_when_done() -> None:
    ai = AIMessage(content="done")
    state = make_state(messages=[ai], started_at=time.time())
    assert route_after_agent(state) == "draft_finding"


def test_route_after_agent_routes_to_budget_exceeded_when_over_budget() -> None:
    ai = AIMessage(content="done")
    state = make_state(messages=[ai], started_at=0.0)
    assert route_after_agent(state) == "budget_exceeded"
