"""Deterministic terminal assembly — no model call, so the published finding
is always byte-identical to the judged draft (docs/PLAN.md D-A2-1). This is
the node the "published == judged draft" test targets.

The process audit is attached beside the draft and is record-only: it never
changes the disposition or the text.
"""

from __future__ import annotations

from surveillance.graph.evidence import extract_tool_call_records
from surveillance.graph.state import SurveillanceState
from surveillance.graph.trajectory_audit import audit_trajectory, extract_claimed_exemptions
from surveillance.schemas.finding import PublishedFinding


def publish_node(state: SurveillanceState) -> dict[str, object]:
    draft = state["draft_finding"]
    assert draft is not None
    report = state["grounding_report"]
    assert report is not None
    claims = state["claims"]
    audit = audit_trajectory(
        extract_tool_call_records(state["messages"]), claims, extract_claimed_exemptions(claims)
    )
    published = PublishedFinding(**draft.model_dump(), grounding_report=report, process_audit=audit)
    return {"published_finding": published}
