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


class PublishedFinding(ComplianceFinding):
    """The terminal artifact. `publish` (nodes/publish.py) builds this from
    the judged draft's own `model_dump()` plus the grounding report — no
    model call, so `finding_text` is always byte-identical to the judged
    draft (docs/PLAN.md D-A2-1)."""

    grounding_report: GroundingReport
