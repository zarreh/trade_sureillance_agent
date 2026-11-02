from langchain_core.messages import AIMessage, ToolMessage

from surveillance.graph.evidence import format_evidence_index
from surveillance.graph.nodes.extract_claims import build_extract_claims_node
from surveillance.schemas.finding import ComplianceFinding, ToolCallRecord
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
    assert stub.last_input is not None
    assert stub.last_input["finding_text"] == "the finding"
    assert stub.last_input["tool_call_ids"] == ["call_1"]
    index = stub.last_input["evidence_index"]
    assert isinstance(index, str)
    assert "call_1: get_transaction_details({})" in index
    assert "reported_under_10b5_1" in index


def test_evidence_index_truncates_long_results_and_handles_no_calls() -> None:
    record = ToolCallRecord(
        tool_call_id="call_9", tool_name="get_compliance_rules", args={"x": 1}, result="a " * 1000
    )
    line = format_evidence_index([record], excerpt_chars=20)
    assert line.startswith('- call_9: get_compliance_rules({"x": 1}) -> ')
    assert line.endswith(" …")
    assert len(line) < 80
    assert format_evidence_index([]) == "(no tool calls were made)"


def test_invented_ids_are_kept_for_the_process_audit() -> None:
    claims = [Claim(id="c1", text="x", cited_tool_call_ids=["call_invented"])]
    node = build_extract_claims_node(_StubClaimExtractorChain(claims))
    draft = ComplianceFinding(disposition="clear", confidence="high", finding_text="t")
    result = node(make_state(draft_finding=draft, messages=[]))
    assert result["claims"] == claims
