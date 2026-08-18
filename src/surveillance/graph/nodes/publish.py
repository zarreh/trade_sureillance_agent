"""Deterministic terminal assembly — no model call, so the published finding
is always byte-identical to the judged draft (docs/PLAN.md D-A2-1). This is
the node the "published == judged draft" test targets.
"""

from __future__ import annotations

from surveillance.graph.state import SurveillanceState
from surveillance.schemas.finding import PublishedFinding


def publish_node(state: SurveillanceState) -> dict[str, object]:
    draft = state["draft_finding"]
    assert draft is not None
    report = state["grounding_report"]
    assert report is not None
    published = PublishedFinding(**draft.model_dump(), grounding_report=report)
    return {"published_finding": published}
