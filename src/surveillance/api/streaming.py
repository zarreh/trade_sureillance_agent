import json
from collections.abc import AsyncIterator
from functools import partial
from typing import Any

from zarreh_agentkit.runs import replay_and_tail
from zarreh_agentkit.serialization import stream_graph_events

from surveillance.store.run_store import RunStore

__all__ = ["stream_graph_events", "stream_investigation_events"]


def stream_investigation_events(run_store: RunStore, run_id: str) -> AsyncIterator[str]:
    """Replays every event already persisted for a run, then — if the run is
    still executing — tails newly-appended events until it reaches a
    terminal status. Works identically whether a client connects the instant
    a run starts or reconnects long after it finished (docs/PLAN.md §7 Phase 5)."""

    def poll_end() -> dict[str, Any] | None:
        run = run_store.get_run(run_id)
        if run is not None and run.status == "running":
            return None
        status = run.status if run is not None else "not_found"
        finding = json.loads(run.finding_json) if run is not None and run.finding_json else None
        return {"status": status, "finding": finding}

    return replay_and_tail(partial(run_store.get_events, run_id), poll_end)
