"""Runs one investigation to completion, persisting every node event and the
final finding to the RunStore as it happens — so a run is replayable from the
store whether a client is watching live or reconnects later (docs/PLAN.md §7
Phase 5). Runs as an in-process background task: a single-instance demo
deployment doesn't need a separate task queue (same reasoning as SQLite over
Postgres for this phase, docs/PLAN.md §5.2).
"""

from __future__ import annotations

import json

import structlog
from langchain_core.callbacks.base import BaseCallbackHandler
from pydantic import BaseModel

from surveillance.graph.builder import SurveillanceGraph
from surveillance.graph.cost_tracking import CostTrackingHandler
from surveillance.graph.state import create_initial_state
from surveillance.observability import get_logger
from surveillance.schemas.finding import ComplianceFinding, PublishedFinding
from surveillance.settings import Settings
from surveillance.store.models import CostEntry
from surveillance.store.run_store import RunStore

logger = get_logger(__name__)

# Only these are genuine node boundaries: astream_events also emits
# on_chain_end for internal LCEL sub-steps (prompt templates, parsers, the
# routing predicates themselves) which happen to share event names with
# real nodes' `langgraph_node` tag in some LangGraph versions, so filtering
# on name alone is not enough — see the name == langgraph_node check below.
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


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return str(value)


def _build_tracing_callbacks(settings: Settings) -> list[BaseCallbackHandler]:
    if not settings.langsmith_api_key:
        return []
    from langchain_core.tracers.langchain import LangChainTracer

    return [LangChainTracer(project_name=settings.langsmith_project)]


async def execute_investigation(
    run_id: str,
    accession_number: str,
    graph: SurveillanceGraph,
    run_store: RunStore,
    settings: Settings,
) -> None:
    structlog.contextvars.bind_contextvars(correlation_id=run_id)
    try:
        cost_handler = CostTrackingHandler()
        callbacks = [cost_handler, *_build_tracing_callbacks(settings)]
        final_state: dict[str, object] = {}
        sequence = 0

        async for event in graph.astream_events(
            create_initial_state(accession_number),
            version="v2",
            config={"callbacks": callbacks, "metadata": {"correlation_id": run_id}},
        ):
            if event["event"] != "on_chain_end":
                continue
            metadata = event.get("metadata") or {}
            node_name = metadata.get("langgraph_node")
            if node_name not in _GRAPH_NODE_NAMES or event.get("name") != node_name:
                continue

            output = event.get("data", {}).get("output")
            if isinstance(output, dict):
                final_state.update(output)
            run_store.append_event(
                run_id, sequence, node_name, json.dumps(output, default=_json_default)
            )
            sequence += 1

        run_store.record_costs(
            run_id,
            [
                CostEntry(e.node, e.model, e.prompt_tokens, e.completion_tokens, e.cost_usd)
                for e in cost_handler.entries
            ],
        )
        _finalize(run_store, run_id, final_state)
    except Exception as exc:
        logger.error("investigation_failed", run_id=run_id, error=str(exc))
        run_store.fail_run(run_id, str(exc))
    finally:
        structlog.contextvars.unbind_contextvars("correlation_id")


def _finalize(run_store: RunStore, run_id: str, final_state: dict[str, object]) -> None:
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
