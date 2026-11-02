"""Case-review queue: the labelled scenarios plus every investigated accession,
each with the AI's latest suggestion and the analyst's record-only decision
(docs/architecture/decisions/D-A2-11, D-A2-12). Expected labels never appear here.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from surveillance.api.deps import get_fact_store, get_run_store
from surveillance.api.rate_limit import DEFAULT_RATE_LIMIT, limiter
from surveillance.api.schemas import (
    AnalystDecisionRequest,
    AnalystDecisionResponse,
    CaseListResponse,
    CaseRow,
    CaseRunSummary,
    FilingSummary,
)
from surveillance.store.fact_store import FactStore
from surveillance.store.models import AnalystDecision, RunRecord
from surveillance.store.run_store import RunStore

router = APIRouter(prefix="/cases", tags=["cases"])

RunStoreDep = Annotated[RunStore, Depends(get_run_store)]
FactStoreDep = Annotated[FactStore, Depends(get_fact_store)]


def _filing_summary(fact_store: FactStore, accession: str) -> FilingSummary | None:
    lines = fact_store.transactions_for_accession(accession)
    if not lines:
        return None
    first = lines[0]
    return FilingSummary(
        insider_name=first.rptowner_name,
        relationship=first.rptowner_relationship or None,
        issuer_name=first.issuer_name,
        issuer_ticker=first.issuer_ticker or None,
        trade_date=first.trans_date,
        transaction_codes=sorted({t.trans_code for t in lines}),
        total_shares=sum(t.trans_shares for t in lines),
        total_value=sum(t.trans_value for t in lines),
        lines=len(lines),
    )


def _run_summary(run: RunRecord) -> CaseRunSummary:
    finding: dict[str, object] = json.loads(run.finding_json) if run.finding_json else {}
    audit = finding.get("process_audit")
    report = finding.get("grounding_report")
    disposition = finding.get("disposition")
    severity = finding.get("severity")
    return CaseRunSummary(
        id=run.id,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        finding_kind=run.finding_kind,
        disposition=disposition if disposition in ("clear", "flag", "escalate") else None,
        severity=severity if isinstance(severity, str) else None,
        trajectory_score=audit.get("trajectory_score") if isinstance(audit, dict) else None,
        unsupported_claims=report.get("unsupported") if isinstance(report, dict) else None,
    )


def _decision_response(decision: AnalystDecision, runs: list[RunRecord]) -> AnalystDecisionResponse:
    latest_completed = next((r for r in runs if r.status == "completed"), None)
    return AnalystDecisionResponse(
        run_id=decision.run_id,
        decision=decision.decision,  # type: ignore[arg-type]
        override_disposition=decision.override_disposition,  # type: ignore[arg-type]
        note=decision.note,
        updated_at=decision.updated_at,
        # A newer run that is still running or failed leaves the decision current.
        stale=latest_completed is not None and latest_completed.id != decision.run_id,
    )


def _case_row(fact_store: FactStore, run_store: RunStore, accession: str) -> CaseRow:
    runs = run_store.list_runs(accession)
    decision = run_store.get_decision(accession)
    return CaseRow(
        accession_number=accession,
        is_scenario=accession.startswith("SCENARIO-"),
        filing=_filing_summary(fact_store, accession),
        latest_run=_run_summary(runs[0]) if runs else None,
        run_count=len(runs),
        decision=_decision_response(decision, runs) if decision else None,
    )


@router.get("")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def list_cases(
    request: Request, run_store: RunStoreDep, fact_store: FactStoreDep
) -> CaseListResponse:
    """The ten labelled scenarios plus every accession that has been investigated,
    most recently investigated first, then the untouched scenarios."""
    accessions = list(
        dict.fromkeys([*run_store.investigated_accessions(), *fact_store.scenario_accessions()])
    )
    return CaseListResponse(cases=[_case_row(fact_store, run_store, a) for a in accessions])


@router.get("/{accession_number}")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_case(
    request: Request, accession_number: str, run_store: RunStoreDep, fact_store: FactStoreDep
) -> CaseRow:
    if fact_store.get_transaction(accession_number) is None:
        raise HTTPException(status_code=404, detail="Accession not found")
    return _case_row(fact_store, run_store, accession_number)


@router.put("/{accession_number}/decision")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def put_decision(
    request: Request,
    accession_number: str,
    body: AnalystDecisionRequest,
    run_store: RunStoreDep,
    fact_store: FactStoreDep,
) -> CaseRow:
    """Records the analyst's accept or override for one completed run. Record-only:
    the AI finding is never changed and the decision never feeds the evaluations."""
    if fact_store.get_transaction(accession_number) is None:
        raise HTTPException(status_code=404, detail="Accession not found")
    run = run_store.get_run(body.run_id)
    if run is None or run.accession_number != accession_number:
        raise HTTPException(status_code=422, detail="run_id is not a run of this accession")
    if run.status != "completed":
        raise HTTPException(status_code=409, detail="Only a completed run can be decided on")
    run_store.set_decision(
        accession_number, run.id, body.decision, body.override_disposition, body.note.strip()
    )
    return _case_row(fact_store, run_store, accession_number)
