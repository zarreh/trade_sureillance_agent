import json
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from surveillance.api.deps import get_compiled_graph, get_run_store, get_surveillance_graph
from surveillance.api.rate_limit import DEFAULT_RATE_LIMIT, limiter
from surveillance.api.run_executor import execute_investigation
from surveillance.api.schemas import (
    CostSummaryEntry,
    CreateInvestigationRequest,
    CreateInvestigationResponse,
    InvestigationResponse,
)
from surveillance.api.streaming import stream_graph_events, stream_investigation_events
from surveillance.graph.builder import SkeletonGraph, SurveillanceGraph
from surveillance.graph.state import SkeletonState
from surveillance.settings import Settings, get_settings
from surveillance.store.run_store import RunStore

router = APIRouter(prefix="/investigations", tags=["investigations"])

GraphDep = Annotated[SkeletonGraph, Depends(get_compiled_graph)]
SurveillanceGraphDep = Annotated[SurveillanceGraph, Depends(get_surveillance_graph)]
RunStoreDep = Annotated[RunStore, Depends(get_run_store)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/skeleton/events")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def skeleton_events(
    request: Request, graph: GraphDep, message: str = "hello"
) -> EventSourceResponse:
    """Phase 0 proof: streams the trivial echo -> done graph node-by-node."""
    initial_state: SkeletonState = {"message": message, "echoed": "", "done": False}
    return EventSourceResponse(stream_graph_events(graph, initial_state))


@router.post("", status_code=202)
@limiter.limit(DEFAULT_RATE_LIMIT)
async def create_investigation(
    request: Request,
    body: CreateInvestigationRequest,
    background_tasks: BackgroundTasks,
    graph: SurveillanceGraphDep,
    run_store: RunStoreDep,
    settings: SettingsDep,
) -> CreateInvestigationResponse:
    """Starts one investigation as a background task and returns immediately
    — poll `GET /{id}` or stream `GET /{id}/events` for progress."""
    run_id = str(uuid4())
    run_store.create_run(run_id, body.accession_number)
    background_tasks.add_task(
        execute_investigation, run_id, body.accession_number, graph, run_store, settings
    )
    return CreateInvestigationResponse(id=run_id, status="running")


@router.get("/{run_id}")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_investigation(
    request: Request, run_id: str, run_store: RunStoreDep
) -> InvestigationResponse:
    run = run_store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    finding = json.loads(run.finding_json) if run.finding_json else None
    costs = [
        CostSummaryEntry(
            node=c.node,
            model=c.model,
            prompt_tokens=c.prompt_tokens,
            completion_tokens=c.completion_tokens,
            cost_usd=c.cost_usd,
        )
        for c in run_store.get_costs(run_id)
    ]
    return InvestigationResponse(
        id=run.id,
        accession_number=run.accession_number,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        finding_kind=run.finding_kind,
        finding=finding,
        error=run.error,
        total_cost_usd=sum(c.cost_usd for c in costs),
        costs=costs,
    )


@router.get("/{run_id}/events")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def investigation_events(
    request: Request, run_id: str, run_store: RunStoreDep
) -> EventSourceResponse:
    if run_store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return EventSourceResponse(stream_investigation_events(run_store, run_id))
