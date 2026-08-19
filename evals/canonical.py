"""Layer 1 — canonical regression set (docs/PLAN.md §4.5, §7 Phase 7).

Runs each of the 10 canonical scenarios through the REAL compiled graph
control flow (real nodes, real tools, real stores) with the deterministic
oracle chains from evals/oracle.py standing in for a live LLM. Gates PR CI:
`evals/run.py` exits non-zero if any scenario doesn't match its expected
disposition.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from data.build_store import build_facts_db
from data.generate_compliance_db import build_policy_db
from data.scenarios import (
    SCENARIOS,
    Scenario,
    inject_scenario_material_event,
    inject_scenarios_into,
)
from evals.metrics import EvalResult, MetricsReport, compute_metrics
from evals.oracle import (
    OracleClaimExtractorChain,
    OracleFindingWriterChain,
    OracleGroundingJudgeChain,
    OracleInvestigator,
    OraclePlannerChain,
)
from surveillance.graph.cost_tracking import CostTrackingHandler
from surveillance.graph.edges import (
    route_after_agent,
    route_after_check_plan,
    route_after_grounding,
)
from surveillance.graph.nodes.budget_exceeded import budget_exceeded_node
from surveillance.graph.nodes.check_plan import build_check_plan_node
from surveillance.graph.nodes.draft_finding import build_draft_finding_node
from surveillance.graph.nodes.extract_claims import build_extract_claims_node
from surveillance.graph.nodes.investigate import build_investigate_node
from surveillance.graph.nodes.judge_grounding import build_judge_grounding_node
from surveillance.graph.nodes.plan import build_plan_node
from surveillance.graph.nodes.publish import publish_node
from surveillance.graph.nodes.replan import build_replan_node
from surveillance.graph.state import SurveillanceState, create_initial_state
from surveillance.schemas.finding import ComplianceFinding, PublishedFinding
from surveillance.schemas.plan import PlanCheck
from surveillance.store.fact_store import FactStore
from surveillance.store.policy_store import PolicyStore
from surveillance.tools.registry import build_tools

FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "edgar_sample"

_EvalGraph = CompiledStateGraph[SurveillanceState, None, SurveillanceState, SurveillanceState]


def _build_scenario_graph(tools: list[StructuredTool], accession_number: str) -> _EvalGraph:
    planner_chain = OraclePlannerChain()
    workflow = StateGraph(SurveillanceState)
    # See src/surveillance/graph/builder.py for why these need type: ignore.
    workflow.add_node("plan", build_plan_node(planner_chain))  # type: ignore[call-overload]
    workflow.add_node(
        "check_plan",
        build_check_plan_node(frozenset(t.name for t in tools)),  # type: ignore[call-overload]
    )
    workflow.add_node("replan", build_replan_node(planner_chain))  # type: ignore[call-overload]
    workflow.add_node(
        "investigate",
        build_investigate_node(  # type: ignore[call-overload]
            OracleInvestigator(accession_number), "oracle investigator"
        ),
    )
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node(
        "draft_finding",
        build_draft_finding_node(OracleFindingWriterChain()),  # type: ignore[call-overload]
    )
    workflow.add_node(
        "extract_claims",
        build_extract_claims_node(OracleClaimExtractorChain()),  # type: ignore[call-overload]
    )
    workflow.add_node(
        "judge_grounding",
        build_judge_grounding_node(OracleGroundingJudgeChain()),  # type: ignore[call-overload]
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


def _build_eval_stores(tmp_path: Path) -> tuple[FactStore, PolicyStore]:
    facts_path = tmp_path / "facts.db"
    policy_path = tmp_path / "policy.db"
    build_facts_db(FIXTURE_DIR, facts_path)
    build_policy_db(policy_path)
    inject_scenarios_into(facts_path)
    inject_scenario_material_event(policy_path)
    return FactStore(facts_path), PolicyStore(policy_path)


def _run_scenario(scenario: Scenario, tools: list[StructuredTool]) -> EvalResult:
    graph = _build_scenario_graph(tools, scenario.accession_number)
    cost_handler = CostTrackingHandler()
    started = time.perf_counter()
    result = graph.invoke(
        create_initial_state(scenario.accession_number),
        config={"callbacks": [cost_handler], "recursion_limit": 100},
    )
    latency_seconds = time.perf_counter() - started

    plan_check = result["plan_check"]
    assert isinstance(plan_check, PlanCheck)

    published = result.get("published_finding")
    draft = result.get("draft_finding")
    if isinstance(published, PublishedFinding):
        actual_disposition = published.disposition
        unsupported_claims = published.grounding_report.unsupported
    elif isinstance(draft, ComplianceFinding):
        actual_disposition = draft.disposition
        unsupported_claims = 0
    else:
        raise AssertionError(f"{scenario.id}: no finding was produced")

    claims = result.get("claims", [])
    assert isinstance(claims, list)

    return EvalResult(
        scenario_id=scenario.id,
        expected_disposition=scenario.expected_disposition,
        actual_disposition=actual_disposition,
        plan_ok=plan_check.ok,
        total_claims=len(claims),
        claims_with_citation=sum(1 for c in claims if c.cited_tool_call_ids),
        unsupported_claims=unsupported_claims,
        cost_usd=sum(e.cost_usd for e in cost_handler.entries),
        latency_seconds=latency_seconds,
    )


def run_canonical_eval() -> tuple[list[EvalResult], MetricsReport]:
    with tempfile.TemporaryDirectory() as tmp:
        fact_store, policy_store = _build_eval_stores(Path(tmp))
        tools = build_tools(fact_store, policy_store)
        results = [_run_scenario(s, tools) for s in SCENARIOS]
    return results, compute_metrics(results)


def print_matrix(results: list[EvalResult], report: MetricsReport) -> None:
    print(f"{'scenario':40} {'expected':10} {'actual':10} {'result'}")
    for r in results:
        outcome = "OK" if r.actual_disposition == r.expected_disposition else "MISMATCH"
        print(f"{r.scenario_id:40} {r.expected_disposition:10} {r.actual_disposition:10} {outcome}")
    print()
    print(
        f"n={report.n} (Layer 1, canonical, oracle-scored — see evals/oracle.py "
        "for why this is not a live-model result)"
    )
    print(f"disposition_accuracy={report.disposition_accuracy:.2%}")
    print(f"flag_precision={report.flag_precision:.2%}")
    print(f"flag_recall={report.flag_recall:.2%}")
    print(f"severity_miss_rate={report.severity_miss_rate:.2%}")
    print(f"false_positive_rate_on_clear={report.false_positive_rate_on_clear:.2%}")
    print(f"citation_coverage_pct={report.citation_coverage_pct:.1f}%")
    print(f"unsupported_claim_rate={report.unsupported_claim_rate:.2%}")
    print(f"tool_call_accuracy={report.tool_call_accuracy:.2%}")
    print(f"cost_per_investigation_usd=${report.cost_per_investigation_usd:.4f}")
    print(f"latency_p50_seconds={report.latency_p50_seconds:.3f}")
    print(f"latency_p95_seconds={report.latency_p95_seconds:.3f}")
