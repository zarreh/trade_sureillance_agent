"""Decomposes the draft finding's `finding_text` into discrete claims, each
citing the real tool_call_ids available in this run — never the conversation
itself, so extraction can't smuggle in facts the finding didn't state
(docs/PLAN.md §5.1)."""

from __future__ import annotations

from collections.abc import Callable

from surveillance.graph.evidence import extract_tool_call_records
from surveillance.graph.protocols import ClaimExtractorChain
from surveillance.graph.state import SurveillanceState


def build_extract_claims_node(
    claim_extractor_chain: ClaimExtractorChain,
) -> Callable[[SurveillanceState], dict[str, object]]:
    def extract_claims_node(state: SurveillanceState) -> dict[str, object]:
        draft = state["draft_finding"]
        assert draft is not None
        tool_call_ids = [r.tool_call_id for r in extract_tool_call_records(state["messages"])]
        result = claim_extractor_chain.invoke(
            {"finding_text": draft.finding_text, "tool_call_ids": tool_call_ids}
        )
        return {"claims": result.claims}

    return extract_claims_node
