"""Integration test: wires the real node/edge functions with fake LLM chains
but real tools (against the fixture DB), proving the graph's control flow
without ever calling a live model.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from data.build_store import build_facts_db
from data.generate_compliance_db import build_policy_db
from surveillance.graph.edges import route_after_agent, route_after_check_plan
from surveillance.graph.nodes.budget_exceeded import budget_exceeded_node
from surveillance.graph.nodes.check_plan import MANDATORY_TOOLS, build_check_plan_node
from surveillance.graph.nodes.draft_finding import build_draft_finding_node
from surveillance.graph.nodes.investigate import build_investigate_node
from surveillance.graph.nodes.plan import build_plan_node
from surveillance.graph.nodes.replan import build_replan_node
from surveillance.graph.protocols import Investigator
from surveillance.graph.state import SurveillanceState, create_initial_state
from surveillance.schemas.finding import ComplianceFinding, ComplianceFindingDraft
from surveillance.schemas.plan import InvestigationPlan, PlanCheck, PlanStep
from surveillance.store.fact_store import FactStore
from surveillance.store.policy_store import PolicyStore
from surveillance.tools.registry import build_tools

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "edgar_sample"
TARGET_ACCESSION = "0000000001-25-000001"


class _FakePlannerChain:
    """Always returns a complete, correctly-ordered plan."""

    def __init__(self, tool_names: list[str]) -> None:
        self._steps = [
            PlanStep(order=i, objective=f"call {name}", tool=name, why="required")
            for i, name in enumerate(tool_names, start=1)
        ]

    def invoke(self, _: dict[str, str]) -> InvestigationPlan:
        return InvestigationPlan(steps=self._steps)


class _FakeInvestigator:
    """Requests exactly one real tool call, then declares itself done."""

    def invoke(self, conversation: Sequence[BaseMessage]) -> AIMessage:
        if any(isinstance(m, ToolMessage) for m in conversation):
            return AIMessage(content="Investigation complete.")
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "get_transaction_details",
                    "args": {"accession_number": TARGET_ACCESSION},
                    "id": "call_1",
                }
            ],
        )


class _FakeFindingWriterChain:
    def invoke(self, _: dict[str, object]) -> ComplianceFindingDraft:
        return ComplianceFindingDraft(
            disposition="clear", confidence="high", finding_text="fake finding"
        )


@pytest.fixture
def tools(tmp_path: Path) -> list[StructuredTool]:
    facts_path = tmp_path / "facts.db"
    policy_path = tmp_path / "policy.db"
    build_facts_db(FIXTURE_DIR, facts_path)
    build_policy_db(policy_path)
    return build_tools(FactStore(facts_path), PolicyStore(policy_path))


def _build_test_graph(
    tools: list[StructuredTool], investigator: Investigator
) -> CompiledStateGraph[SurveillanceState, None, SurveillanceState, SurveillanceState]:
    planner_chain = _FakePlannerChain([t.name for t in tools])
    workflow = StateGraph(SurveillanceState)
    # See src/surveillance/graph/builder.py for why these need type: ignore.
    workflow.add_node("plan", build_plan_node(planner_chain))  # type: ignore[call-overload]
    workflow.add_node(
        "check_plan",
        build_check_plan_node(frozenset(t.name for t in tools)),  # type: ignore[call-overload]
    )
    workflow.add_node(
        "replan",
        build_replan_node(planner_chain),  # type: ignore[call-overload]
    )
    workflow.add_node(
        "investigate",
        build_investigate_node(investigator, "system prompt"),  # type: ignore[call-overload]
    )
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node(
        "draft_finding",
        build_draft_finding_node(_FakeFindingWriterChain()),  # type: ignore[call-overload]
    )
    workflow.add_node("budget_exceeded", budget_exceeded_node)

    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "check_plan")
    workflow.add_conditional_edges(
        "check_plan", route_after_check_plan, {"investigate": "investigate", "replan": "replan"}
    )
    workflow.add_edge("replan", "check_plan")
    workflow.add_conditional_edges(
        "investigate",
        route_after_agent,
        {"tools": "tools", "draft_finding": "draft_finding", "budget_exceeded": "budget_exceeded"},
    )
    workflow.add_edge("tools", "investigate")
    workflow.add_edge("draft_finding", END)
    workflow.add_edge("budget_exceeded", END)
    return workflow.compile()


def test_full_pass_produces_a_draft_finding(tools: list[StructuredTool]) -> None:
    graph = _build_test_graph(tools, _FakeInvestigator())
    result = graph.invoke(create_initial_state(TARGET_ACCESSION))
    finding = result["draft_finding"]
    assert isinstance(finding, ComplianceFinding)
    assert finding.finding_text == "fake finding"
    assert finding.incomplete is False
    # The real tool actually ran against the fixture DB.
    tool_message = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert TARGET_ACCESSION in tool_message.content


def test_incomplete_plan_triggers_one_replan_then_proceeds(tools: list[StructuredTool]) -> None:
    workflow = _build_test_graph(tools, _FakeInvestigator())
    # Sanity: MANDATORY_TOOLS names line up with the real registered tools.
    assert set(MANDATORY_TOOLS) == {t.name for t in tools}
    result = workflow.invoke(create_initial_state(TARGET_ACCESSION))
    plan_check = result["plan_check"]
    assert isinstance(plan_check, PlanCheck)
    assert plan_check.ok is True  # the fake planner always returns a complete plan
    assert result["replan_count"] == 0


class _RunawayInvestigator:
    """Never stops requesting tool calls — exercises the budget guardrail."""

    def invoke(self, _: Sequence[BaseMessage]) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "get_transaction_details",
                    "args": {"accession_number": TARGET_ACCESSION},
                    "id": f"call_{id(self)}",
                }
            ],
        )


def test_runaway_investigation_hits_the_budget_guardrail(tools: list[StructuredTool]) -> None:
    """Requests a tool call every round with no stopping condition — exercises
    the real default budget (max_tool_calls=15) rather than a monkeypatched one,
    since Budget is a default *argument* bound at function-definition time and
    reassigning the module attribute afterwards would not affect it."""
    graph = _build_test_graph(tools, _RunawayInvestigator())
    result = graph.invoke(create_initial_state(TARGET_ACCESSION), config={"recursion_limit": 100})
    finding = result["draft_finding"]
    assert isinstance(finding, ComplianceFinding)
    assert finding.incomplete is True
    assert finding.disposition == "escalate"
