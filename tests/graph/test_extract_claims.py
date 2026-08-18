from langchain_core.messages import AIMessage, ToolMessage

from surveillance.graph.nodes.extract_claims import build_extract_claims_node
from surveillance.schemas.finding import ComplianceFinding
from surveillance.schemas.grounding import Claim, ExtractedClaims

from ._state_helpers import make_state


class _StubClaimExtractorChain:
    def __init__(self, claims: list[Claim]) -> None:
        self._claims = claims
        self.last_input: dict[str, object] | None = None

    def invoke(self, input_: dict[str, object]) -> ExtractedClaims:
        self.last_input = input_
        return ExtractedClaims(claims=self._claims)


def test_passes_finding_text_and_real_tool_call_ids_to_the_chain() -> None:
    claims = [Claim(id="c1", text="x", cited_tool_call_ids=["call_1"])]
    stub = _StubClaimExtractorChain(claims)
    node = build_extract_claims_node(stub)

    draft = ComplianceFinding(disposition="clear", confidence="high", finding_text="the finding")
    messages = [
        AIMessage(
            content="",
            tool_calls=[{"name": "get_transaction_details", "args": {}, "id": "call_1"}],
        ),
        ToolMessage(content='{"reported_under_10b5_1": "true"}', tool_call_id="call_1"),
    ]
    result = node(make_state(draft_finding=draft, messages=messages))

    assert result["claims"] == claims
    assert stub.last_input == {"finding_text": "the finding", "tool_call_ids": ["call_1"]}
