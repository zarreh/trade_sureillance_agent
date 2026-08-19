"""Writes the draft finding, then attaches deterministically-derived
exculpatory factors — the model never authors those (docs/PLAN.md D-A2-3)."""

from __future__ import annotations

from collections.abc import Callable

from surveillance.graph.evidence import (
    derive_exculpatory_factors,
    derive_reported_under_10b5_1,
    extract_tool_call_records,
)
from surveillance.graph.protocols import FindingWriterChain
from surveillance.graph.state import SurveillanceState
from surveillance.schemas.finding import ComplianceFinding


def build_draft_finding_node(
    finding_writer_chain: FindingWriterChain,
) -> Callable[[SurveillanceState], dict[str, object]]:
    def draft_finding_node(state: SurveillanceState) -> dict[str, object]:
        draft = finding_writer_chain.invoke({"messages": state["messages"]})
        records = extract_tool_call_records(state["messages"])
        finding = ComplianceFinding(
            **draft.model_dump(),
            exculpatory_factors=derive_exculpatory_factors(records),
            reported_under_10b5_1=derive_reported_under_10b5_1(records),
        )
        return {"draft_finding": finding}

    return draft_finding_node
