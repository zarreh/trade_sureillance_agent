from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage

from surveillance.graph.nodes.investigate import build_investigate_node
from surveillance.schemas.plan import InvestigationPlan, PlanStep

from ._state_helpers import make_state


class _StubInvestigator:
    def __init__(self, response: AIMessage) -> None:
        self.response = response
        self.last_conversation: Sequence[BaseMessage] | None = None

    def invoke(self, conversation: Sequence[BaseMessage]) -> AIMessage:
        self.last_conversation = conversation
        return self.response


_PLAN = InvestigationPlan(steps=[PlanStep(order=1, objective="x", tool="t", why="y")])


def test_first_call_seeds_system_and_human_messages() -> None:
    stub = _StubInvestigator(AIMessage(content="ok"))
    node = build_investigate_node(stub, system_prompt="be careful")
    result = node(make_state(messages=[], plan=_PLAN))
    seeded = result["messages"]
    assert isinstance(seeded, list)
    assert len(seeded) == 3  # system, human, response
    assert seeded[0].content == "be careful"
    assert "ACC-1" in seeded[1].content
    assert stub.last_conversation == seeded[:2]


def test_subsequent_call_does_not_reseed() -> None:
    stub = _StubInvestigator(AIMessage(content="ok"))
    node = build_investigate_node(stub, system_prompt="be careful")
    existing: list[BaseMessage] = [AIMessage(content="prior")]
    result = node(make_state(messages=existing, plan=_PLAN))
    assert result["messages"] == [stub.response]
    assert stub.last_conversation == existing
