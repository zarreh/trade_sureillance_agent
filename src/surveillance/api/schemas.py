"""API-contract request/response models — separate from `schemas/`, which
holds the domain models the graph itself produces (docs/PLAN.md §5.2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
