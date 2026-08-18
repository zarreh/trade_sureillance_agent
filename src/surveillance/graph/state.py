import time
from collections.abc import Sequence
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from surveillance.schemas.finding import ComplianceFinding, PublishedFinding
from surveillance.schemas.grounding import Claim, GroundingReport
from surveillance.schemas.plan import InvestigationPlan, PlanCheck


class SkeletonState(TypedDict):
    """Phase 0 walking-skeleton state — kept as the template's trivial proof graph."""

    message: str
    echoed: str
    done: bool


class SurveillanceState(TypedDict):
    """State for the real investigation graph (docs/PLAN.md §5.1–§5.3)."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    accession_number: str
    plan: InvestigationPlan | None
    plan_check: PlanCheck | None
    replan_count: int
    started_at: float
    draft_finding: ComplianceFinding | None
    claims: list[Claim]
    grounding_report: GroundingReport | None
    evidence_pass: int
    published_finding: PublishedFinding | None


def create_initial_state(accession_number: str) -> SurveillanceState:
    """The only place default field values are decided — never scattered
    across nodes."""
    return SurveillanceState(
        messages=[],
        accession_number=accession_number,
        plan=None,
        plan_check=None,
        replan_count=0,
        started_at=time.time(),
        draft_finding=None,
        claims=[],
        grounding_report=None,
        evidence_pass=0,
        published_finding=None,
    )
