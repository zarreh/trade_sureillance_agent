import asyncio
import json
from collections.abc import AsyncIterator

from surveillance.graph.builder import SkeletonGraph
from surveillance.graph.state import SkeletonState
from surveillance.store.run_store import RunStore

_POLL_INTERVAL_SECONDS = 0.25


async def stream_graph_events(
    graph: SkeletonGraph, initial_state: SkeletonState
) -> AsyncIterator[str]:
    """Bridges a LangGraph run to Server-Sent Events, one event per node step."""
    async for event in graph.astream_events(initial_state, version="v2"):
        if event["event"] != "on_chain_end":
            continue
        payload = {
            "node": event.get("name"),
            "output": event.get("data", {}).get("output"),
        }
        yield json.dumps(payload, default=str)
    yield json.dumps({"node": "__end__", "output": None})


async def stream_investigation_events(run_store: RunStore, run_id: str) -> AsyncIterator[str]:
    """Replays every event already persisted for a run, then — if the run is
    still executing — tails newly-appended events until it reaches a
    terminal status. Works identically whether a client connects the instant
    a run starts or reconnects long after it finished (docs/PLAN.md §7 Phase 5)."""
    last_sequence = -1
    while True:
        events = run_store.get_events(run_id, after_sequence=last_sequence)
        for event in events:
            yield json.dumps({"node": event.node, "output": json.loads(event.payload_json)})
            last_sequence = event.sequence

        run = run_store.get_run(run_id)
        if run is None or run.status != "running":
            break
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    status = run.status if run is not None else "not_found"
    finding = json.loads(run.finding_json) if run is not None and run.finding_json else None
    yield json.dumps({"node": "__end__", "output": {"status": status, "finding": finding}})
