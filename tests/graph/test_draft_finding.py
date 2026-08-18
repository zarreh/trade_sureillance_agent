from langchain_core.messages import AIMessage, ToolMessage

from surveillance.graph.nodes.draft_finding import build_draft_finding_node
from surveillance.schemas.finding import ComplianceFinding, ComplianceFindingDraft

from ._state_helpers import make_state


class _StubFindingWriterChain:
    def __init__(self, draft: ComplianceFindingDraft) -> None:
        self.draft = draft
        self.last_input: dict[str, object] | None = None

    def invoke(self, input_: dict[str, object]) -> ComplianceFindingDraft:
        self.last_input = input_
        return self.draft


def test_attaches_deterministic_exculpatory_factors_to_llm_draft() -> None:
    draft = ComplianceFindingDraft(
        disposition="clear", confidence="high", finding_text="looks fine"
    )
    stub = _StubFindingWriterChain(draft)
    node = build_draft_finding_node(stub)

    messages = [
        AIMessage(
            content="",
            tool_calls=[{"name": "get_transaction_details", "args": {}, "id": "call_1"}],
        ),
        ToolMessage(
            content='{"reported_under_10b5_1": "true", "transactions": '
            '[{"nonderiv_trans_sk": 1, "trans_code": "S", "trans_value": 100}]}',
            tool_call_id="call_1",
        ),
    ]
    result = node(make_state(messages=messages))
    finding = result["draft_finding"]
    assert isinstance(finding, ComplianceFinding)
    assert finding.disposition == "clear"
    assert finding.finding_text == "looks fine"
    assert any(f.kind == "reported_under_10b5_1" for f in finding.exculpatory_factors)
    assert stub.last_input == {"messages": messages}
