from surveillance.graph.nodes.judge_grounding import build_judge_grounding_node
from surveillance.schemas.grounding import Claim, ClaimJudgment, ClaimJudgments, GroundingReport

from ._state_helpers import make_state


class _StubGroundingJudgeChain:
    def __init__(self, judgments: list[ClaimJudgment]) -> None:
        self._judgments = judgments

    def invoke(self, input_: dict[str, object]) -> ClaimJudgments:
        return ClaimJudgments(judgments=self._judgments)


_CLAIMS = [Claim(id="c1", text="claim one"), Claim(id="c2", text="claim two")]


def test_fully_supported_claims_yield_high_confidence_and_no_feedback() -> None:
    judgments = [
        ClaimJudgment(claim_id="c1", supported=True, reason="matches"),
        ClaimJudgment(claim_id="c2", supported=True, reason="matches"),
    ]
    node = build_judge_grounding_node(_StubGroundingJudgeChain(judgments))
    result = node(make_state(claims=_CLAIMS, evidence_pass=0))

    report = result["grounding_report"]
    assert isinstance(report, GroundingReport)
    assert report.unsupported == 0
    assert report.confidence == "high"
    assert result["evidence_pass"] == 1
    assert "messages" not in result


def test_unsupported_claim_yields_feedback_message_citing_it() -> None:
    judgments = [
        ClaimJudgment(claim_id="c1", supported=True, reason="matches"),
        ClaimJudgment(claim_id="c2", supported=False, reason="no supporting tool result"),
    ]
    node = build_judge_grounding_node(_StubGroundingJudgeChain(judgments))
    result = node(make_state(claims=_CLAIMS, evidence_pass=0))

    report = result["grounding_report"]
    assert isinstance(report, GroundingReport)
    assert report.unsupported == 1
    assert report.confidence == "medium"
    messages = result["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 1
    assert "claim two" in messages[0].content
    assert "no supporting tool result" in messages[0].content


def test_multiple_unsupported_claims_yield_low_confidence() -> None:
    judgments = [
        ClaimJudgment(claim_id="c1", supported=False, reason="no evidence"),
        ClaimJudgment(claim_id="c2", supported=False, reason="no evidence"),
    ]
    node = build_judge_grounding_node(_StubGroundingJudgeChain(judgments))
    result = node(make_state(claims=_CLAIMS, evidence_pass=1))

    report = result["grounding_report"]
    assert isinstance(report, GroundingReport)
    assert report.unsupported == 2
    assert report.confidence == "low"
    assert result["evidence_pass"] == 2
