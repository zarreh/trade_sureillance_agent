"""Grounding-loop schemas (docs/PLAN.md §5.1, §5.3).

`Claim`/`ExtractedClaims` are the claim extractor's output. `ClaimJudgment`/
`ClaimJudgments` are the grounding judge's raw per-claim output — the judge
scores each claim; it never authors the aggregate `unsupported` count or
`confidence`, both of which are computed deterministically in
`nodes/judge_grounding.py` (same "don't spend a model call on a decision an
`if` can make" argument as `check_plan`, D-A2-2).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Claim(BaseModel):
    id: str
    text: str
    cited_tool_call_ids: list[str] = Field(default_factory=list)


class ExtractedClaims(BaseModel):
    claims: list[Claim]


class ClaimJudgment(BaseModel):
    claim_id: str
    supported: bool
    evidence_span: str | None = None
    reason: str


class ClaimJudgments(BaseModel):
    """The grounding judge's raw structured output, before aggregation."""

    judgments: list[ClaimJudgment]


class GroundingReport(BaseModel):
    claims: list[ClaimJudgment]
    unsupported: int
    confidence: Literal["high", "medium", "low"]
