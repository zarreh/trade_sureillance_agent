import json
from collections.abc import AsyncIterator

from surveillance.graph.builder import SkeletonGraph
from surveillance.graph.state import SkeletonState


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
