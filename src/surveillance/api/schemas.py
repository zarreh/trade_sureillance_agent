"""API-contract request/response models — separate from `schemas/`, which
holds the domain models the graph itself produces (docs/PLAN.md §5.2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CreateInvestigationRequest(BaseModel):
    accession_number: str = Field(min_length=1, max_length=64)


class CreateInvestigationResponse(BaseModel):
    id: str
    status: str


class CostSummaryEntry(BaseModel):
    node: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class InvestigationResponse(BaseModel):
    id: str
    accession_number: str
    status: str
    created_at: str
    updated_at: str
    finding_kind: str | None
    finding: dict[str, object] | None
    error: str | None
    total_cost_usd: float
    costs: list[CostSummaryEntry]


Disposition = Literal["clear", "flag", "escalate"]


class FilingSummary(BaseModel):
    insider_name: str
    relationship: str | None
    issuer_name: str
    issuer_ticker: str | None
    trade_date: str
    transaction_codes: list[str]
    total_shares: float
    total_value: float | None
    lines: int


class CaseRunSummary(BaseModel):
    id: str
    status: str
    created_at: str
    updated_at: str
    finding_kind: str | None
    disposition: Disposition | None
    severity: str | None
    trajectory_score: float | None
    unsupported_claims: int | None


class AnalystDecisionResponse(BaseModel):
    run_id: str
    decision: Literal["accept", "override"]
    override_disposition: Disposition | None
    note: str
    updated_at: str
    stale: bool = Field(
        description="True when a newer completed run exists than the one the decision was made on."
    )


class CaseRow(BaseModel):
    accession_number: str
    is_scenario: bool
    filing: FilingSummary | None
    latest_run: CaseRunSummary | None
    run_count: int
    decision: AnalystDecisionResponse | None


class CaseListResponse(BaseModel):
    cases: list[CaseRow]


class AnalystDecisionRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=64)
    decision: Literal["accept", "override"]
    override_disposition: Disposition | None = None
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _override_needs_a_disposition(self) -> AnalystDecisionRequest:
        if self.decision == "override" and self.override_disposition is None:
            raise ValueError("override requires override_disposition")
        if self.decision == "accept" and self.override_disposition is not None:
            raise ValueError("accept must not set override_disposition")
        return self
