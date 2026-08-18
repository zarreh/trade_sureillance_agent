"""Terminal node when the cost guardrail trips — emits a partial finding
marked `incomplete` rather than silently truncating (docs/PLAN.md §5.5)."""

from __future__ import annotations

from surveillance.graph.budget import budget_breach_reason
from surveillance.graph.state import SurveillanceState
from surveillance.schemas.finding import ComplianceFinding


def budget_exceeded_node(state: SurveillanceState) -> dict[str, object]:
    reason = budget_breach_reason(state["messages"], state["started_at"]) or "budget exceeded"
    finding = ComplianceFinding(
        disposition="escalate",
        confidence="low",
        finding_text=(
            "Investigation did not complete within the per-investigation cost "
            "guardrail and was stopped before reaching a grounded conclusion. "
            "Escalated for manual review rather than reporting an unsupported clearance."
        ),
        incomplete=True,
        incomplete_reason=reason,
    )
    return {"draft_finding": finding}
