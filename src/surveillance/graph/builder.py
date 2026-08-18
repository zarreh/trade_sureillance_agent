from pathlib import Path

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from surveillance.graph.agents.investigator import build_investigator
from surveillance.graph.chains.claim_extractor import build_claim_extractor_chain
from surveillance.graph.chains.finding_writer import build_finding_writer_chain
from surveillance.graph.chains.grounding_judge import build_grounding_judge_chain
from surveillance.graph.chains.planner import build_planner_chain
from surveillance.graph.edges import (
    route_after_agent,
    route_after_check_plan,
    route_after_grounding,
)
from surveillance.graph.nodes.budget_exceeded import budget_exceeded_node
from surveillance.graph.nodes.check_plan import build_check_plan_node
from surveillance.graph.nodes.done import done_node
from surveillance.graph.nodes.draft_finding import build_draft_finding_node
from surveillance.graph.nodes.echo import echo_node
from surveillance.graph.nodes.extract_claims import build_extract_claims_node
from surveillance.graph.nodes.investigate import build_investigate_node
from surveillance.graph.nodes.judge_grounding import build_judge_grounding_node
from surveillance.graph.nodes.plan import build_plan_node
from surveillance.graph.nodes.publish import publish_node
from surveillance.graph.nodes.replan import build_replan_node
from surveillance.graph.policies import build_fast_model, build_reasoning_model
from surveillance.graph.state import SkeletonState, SurveillanceState
from surveillance.prompts.loader import load_prompt
from surveillance.settings import Settings
from surveillance.store.fact_store import FactStore
from surveillance.store.policy_store import PolicyStore
from surveillance.tools.registry import build_tools

SkeletonGraph = CompiledStateGraph[SkeletonState, None, SkeletonState, SkeletonState]
SurveillanceGraph = CompiledStateGraph[
    SurveillanceState, None, SurveillanceState, SurveillanceState
]


def build_skeleton_graph() -> SkeletonGraph:
    """The only function that wires nodes and edges. Phase 0: echo -> done."""
    workflow = StateGraph(SkeletonState)
    workflow.add_node("echo", echo_node)
    workflow.add_node("done", done_node)
    workflow.set_entry_point("echo")
    workflow.add_edge("echo", "done")
    workflow.add_edge("done", END)
    return workflow.compile()


def build_surveillance_graph(settings: Settings) -> SurveillanceGraph:
    """The only function that wires the investigation graph's nodes and edges."""
    fact_store = FactStore(Path(settings.facts_db_path))
    policy_store = PolicyStore(Path(settings.policy_db_path))
    tools = build_tools(fact_store, policy_store)

    fast_model = build_fast_model(settings)
    reasoning_model = build_reasoning_model(settings)
    planner_chain = build_planner_chain(fast_model)
    finding_writer_chain = build_finding_writer_chain(reasoning_model)
    investigator = build_investigator(fast_model, tools)
    claim_extractor_chain = build_claim_extractor_chain(fast_model)
    grounding_judge_chain = build_grounding_judge_chain(reasoning_model)

    workflow = StateGraph(SurveillanceState)
    # mypy cannot resolve add_node's overloads against a factory-returned
    # Callable (vs. a plain top-level function) — confirmed upstream limitation,
    # not a real type error; each node is unit-tested directly in tests/graph/.
    workflow.add_node("plan", build_plan_node(planner_chain))  # type: ignore[arg-type]
    workflow.add_node(
        "check_plan",
        build_check_plan_node(frozenset(t.name for t in tools)),  # type: ignore[arg-type]
    )
    workflow.add_node("replan", build_replan_node(planner_chain))  # type: ignore[arg-type]
    workflow.add_node(
        "investigate",
        build_investigate_node(  # type: ignore[arg-type]
            investigator, load_prompt("investigator_v1")
        ),
    )
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node(
        "draft_finding",
        build_draft_finding_node(finding_writer_chain),  # type: ignore[arg-type]
    )
    workflow.add_node(
        "extract_claims",
        build_extract_claims_node(claim_extractor_chain),  # type: ignore[arg-type]
    )
    workflow.add_node(
        "judge_grounding",
        build_judge_grounding_node(grounding_judge_chain),  # type: ignore[arg-type]
    )
    workflow.add_node("publish", publish_node)
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
    workflow.add_edge("draft_finding", "extract_claims")
    workflow.add_edge("extract_claims", "judge_grounding")
    workflow.add_conditional_edges(
        "judge_grounding",
        route_after_grounding,
        {"investigate": "investigate", "publish": "publish"},
    )
    workflow.add_edge("publish", END)
    workflow.add_edge("budget_exceeded", END)
    return workflow.compile()
