from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from surveillance.api.deps import get_compiled_graph
from surveillance.api.streaming import stream_graph_events
from surveillance.graph.builder import SkeletonGraph
from surveillance.graph.state import SkeletonState

router = APIRouter(prefix="/investigations", tags=["investigations"])

GraphDep = Annotated[SkeletonGraph, Depends(get_compiled_graph)]


@router.get("/skeleton/events")
async def skeleton_events(graph: GraphDep, message: str = "hello") -> EventSourceResponse:
    """Phase 0 proof: streams the trivial echo -> done graph node-by-node."""
    initial_state: SkeletonState = {"message": message, "echoed": "", "done": False}
    return EventSourceResponse(stream_graph_events(graph, initial_state))
