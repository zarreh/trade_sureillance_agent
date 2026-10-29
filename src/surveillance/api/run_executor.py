"""Runs one investigation to completion, persisting every node event and the
final finding to the RunStore as it happens — so a run is replayable from the
store whether a client is watching live or reconnects later (docs/PLAN.md §7
Phase 5). Runs as an in-process background task: a single-instance demo
deployment doesn't need a separate task queue (same reasoning as SQLite over
Postgres for this phase, docs/PLAN.md §5.2).
"""

from __future__ import annotations

from typing import Any

from zarreh_agentkit.observability import build_tracing_callbacks
from zarreh_agentkit.runs import execute_run

from surveillance.graph.builder import SurveillanceGraph
from surveillance.graph.state import create_initial_state
from surveillance.schemas.finding import ComplianceFinding, PublishedFinding
from surveillance.settings import Settings
from surveillance.store.run_store import RunStore

# Only these are genuine node boundaries (execute_run also requires
# name == langgraph_node, which drops routing predicates and LCEL sub-steps).
_GRAPH_NODE_NAMES = frozenset(
    {
        "plan",
        "check_plan",
        "replan",
        "investigate",
        "tools",
        "draft_finding",
        "extract_claims",
        "judge_grounding",
        "publish",
        "budget_exceeded",
    }
)


async def execute_investigation(
    run_id: str,
    accession_number: str,
    graph: SurveillanceGraph,
    run_store: RunStore,
    settings: Settings,
) -> None:
    await execute_run(
        run_id=run_id,
        graph=graph,
        graph_input=create_initial_state(accession_number),
        store=run_store,
        finalize=lambda final_state: _finalize(run_store, run_id, final_state),
        callbacks=build_tracing_callbacks(settings.langsmith_api_key, settings.langsmith_project),
        node_names=_GRAPH_NODE_NAMES,
    )


def _finalize(run_store: RunStore, run_id: str, final_state: dict[str, Any]) -> None:
    published = final_state.get("published_finding")
    if isinstance(published, PublishedFinding):
        run_store.complete_run(
            run_id, finding_kind="published", finding_json=published.model_dump_json()
        )
        return

    draft = final_state.get("draft_finding")
    if isinstance(draft, ComplianceFinding):
        run_store.complete_run(
            run_id, finding_kind="incomplete", finding_json=draft.model_dump_json()
        )
        return

    run_store.fail_run(run_id, "graph completed without producing a finding")
