import asyncio
import json
from collections.abc import AsyncIterator

from zarreh_agentkit.serialization import stream_graph_events

from surveillance.store.run_store import RunStore

_POLL_INTERVAL_SECONDS = 0.25

__all__ = ["stream_graph_events", "stream_investigation_events"]


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
