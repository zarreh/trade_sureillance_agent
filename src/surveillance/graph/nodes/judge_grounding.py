"""Scores each claim against the recorded tool evidence, then aggregates
deterministically: `unsupported` and `confidence` are computed here, in code,
never authored by the judge model (same argument as `check_plan`, D-A2-2).

On any unsupported claim, folds specific, actionable feedback back into the
conversation as a `HumanMessage` so the next `investigate` pass targets the
gap directly rather than retrying blindly.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from langchain_core.messages import HumanMessage

from surveillance.graph.evidence import extract_tool_call_records
from surveillance.graph.protocols import GroundingJudgeChain
from surveillance.graph.state import SurveillanceState
from surveillance.schemas.grounding import ClaimJudgment, GroundingReport


def _confidence_for(unsupported: int) -> Literal["high", "medium", "low"]:
    if unsupported == 0:
        return "high"
    if unsupported == 1:
        return "medium"
    return "low"


def _feedback_text(claims_by_id: dict[str, str], judgments: list[ClaimJudgment]) -> str:
    lines = [
        f'- "{claims_by_id.get(j.claim_id, j.claim_id)}" — {j.reason}'
        for j in judgments
        if not j.supported
    ]
    header = (
        "The following claims in the draft finding are not supported by evidence "
        "gathered so far. Investigate further to either substantiate or drop them:"
    )
    return header + "\n" + "\n".join(lines)


def build_judge_grounding_node(
    grounding_judge_chain: GroundingJudgeChain,
) -> Callable[[SurveillanceState], dict[str, object]]:
    def judge_grounding_node(state: SurveillanceState) -> dict[str, object]:
        claims = state["claims"]
        records = extract_tool_call_records(state["messages"])
        result = grounding_judge_chain.invoke(
            {
                "claims": [c.model_dump() for c in claims],
                "evidence": [r.model_dump() for r in records],
            }
        )
        judgments = result.judgments
        unsupported = sum(1 for j in judgments if not j.supported)
        report = GroundingReport(
            claims=judgments,
            unsupported=unsupported,
            confidence=_confidence_for(unsupported),
        )
        delta: dict[str, object] = {
            "grounding_report": report,
            "evidence_pass": state["evidence_pass"] + 1,
        }
        if unsupported > 0:
            claims_by_id = {c.id: c.text for c in claims}
            delta["messages"] = [HumanMessage(content=_feedback_text(claims_by_id, judgments))]
        return delta

    return judge_grounding_node
