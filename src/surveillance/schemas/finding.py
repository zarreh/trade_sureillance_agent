"""Finding schemas (docs/PLAN.md §5.3).

`ComplianceFindingDraft` is what the LLM authors. `ComplianceFinding` adds
`exculpatory_factors`, which are derived deterministically from tool results
in `graph/evidence.py` — never authored by the model. Claims and grounding
(Phase 4) attach to this same finding once the grounding loop exists.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from surveillance.schemas.grounding import GroundingReport

ExculpatoryKind = Literal[
    "reported_under_10b5_1", "tax_withholding", "option_exercise", "below_all_thresholds"
]


class ToolCallRecord(BaseModel):
    tool_call_id: str
    tool_name: str
    args: dict[str, object]
    result: str


class RuleCitation(BaseModel):
    rule_id: str
    rule_name: str
    severity: str


class ExculpatoryFactor(BaseModel):
    kind: ExculpatoryKind
    evidence_tool_call_id: str
    applies_to_transaction_sk: int


class ComplianceFindingDraft(BaseModel):
    disposition: Literal["clear", "flag", "escalate"]
    severity: Literal["Low", "Medium", "High", "Critical"] | None = None
    rules_cited: list[RuleCitation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    finding_text: str


class ComplianceFinding(ComplianceFindingDraft):
    exculpatory_factors: list[ExculpatoryFactor] = Field(default_factory=list)
    reported_under_10b5_1: Literal["true", "false", "unknown"] = "unknown"
    incomplete: bool = False
    incomplete_reason: str | None = None


class ClaimedExemption(BaseModel):
    kind: ExculpatoryKind
    transaction_sk: int | None = None


class ProcessAudit(BaseModel):
    """Deterministic audit of how the investigation reached its finding
    (graph/trajectory_audit.py). Record-only: it never changes a disposition."""

    mandatory_tools_called: list[str]
    mandatory_tools_missing: list[str]
    coverage: float
    details_first: bool
    fabricated_citation_ids: list[str]
    citation_validity: float
    claimed_exemptions: list[ClaimedExemption]
    unsupported_exemptions: list[ClaimedExemption]
    exemption_validity: float
    trajectory_score: float


class PublishedFinding(ComplianceFinding):
    """The terminal artifact. `publish` (nodes/publish.py) builds this from
    the judged draft's own `model_dump()` plus the grounding report — no
    model call, so `finding_text` is always byte-identical to the judged
    draft (docs/PLAN.md D-A2-1). `process_audit` sits beside the draft, not
    inside it."""

    grounding_report: GroundingReport
    process_audit: ProcessAudit | None = None
