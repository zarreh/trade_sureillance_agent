from langchain_core.messages import AIMessage, ToolMessage

from surveillance.graph.nodes.publish import publish_node
from surveillance.schemas.finding import ComplianceFinding, PublishedFinding, ToolCallRecord
from surveillance.schemas.grounding import Claim, GroundingReport

from ._state_helpers import make_state


def test_publish_is_byte_identical_to_the_judged_draft() -> None:
    draft = ComplianceFinding(
        disposition="flag", confidence="medium", finding_text="the judged finding text"
    )
    report = GroundingReport(claims=[], unsupported=0, confidence="high")
    result = publish_node(make_state(draft_finding=draft, grounding_report=report))

    published = result["published_finding"]
    assert isinstance(published, PublishedFinding)
    assert published.finding_text == draft.finding_text
    assert published.disposition == draft.disposition
    assert published.grounding_report == report


def test_publish_attaches_a_record_only_process_audit() -> None:
    draft = ComplianceFinding(disposition="escalate", confidence="low", finding_text="text")
    report = GroundingReport(claims=[], unsupported=0, confidence="high")
    published = publish_node(make_state(draft_finding=draft, grounding_report=report))[
        "published_finding"
    ]
    assert isinstance(published, PublishedFinding)
    assert published.process_audit is not None
    assert published.process_audit.coverage == 0.0
    assert published.disposition == "escalate"


def test_publish_carries_the_judged_claims() -> None:
    draft = ComplianceFinding(disposition="flag", confidence="medium", finding_text="text")
    report = GroundingReport(claims=[], unsupported=0, confidence="high")
    claims = [Claim(id="c1", text="a claim", cited_tool_call_ids=["t1"])]
    published = publish_node(
        make_state(draft_finding=draft, grounding_report=report, claims=claims)
    )["published_finding"]
    assert isinstance(published, PublishedFinding)
    assert published.claims == claims


def test_publish_carries_the_retrieved_evidence_in_call_order() -> None:
    draft = ComplianceFinding(disposition="flag", confidence="medium", finding_text="text")
    report = GroundingReport(claims=[], unsupported=0, confidence="high")
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "get_transaction_details",
                    "args": {"accession_number": "ACC-1"},
                    "id": "t1",
                }
            ],
        ),
        ToolMessage(content='{"transactions": []}', tool_call_id="t1"),
        AIMessage(
            content="",
            tool_calls=[{"name": "get_compliance_rules", "args": {}, "id": "t2"}],
        ),
        ToolMessage(content="[]", tool_call_id="t2"),
    ]
    published = publish_node(
        make_state(draft_finding=draft, grounding_report=report, messages=messages)
    )["published_finding"]

    assert isinstance(published, PublishedFinding)
    assert published.evidence == [
        ToolCallRecord(
            tool_call_id="t1",
            tool_name="get_transaction_details",
            args={"accession_number": "ACC-1"},
            result='{"transactions": []}',
        ),
        ToolCallRecord(tool_call_id="t2", tool_name="get_compliance_rules", args={}, result="[]"),
    ]
    # Evidence sits beside the draft: it never changes what was judged.
    assert published.finding_text == draft.finding_text
    assert published.disposition == draft.disposition


def test_publish_with_no_tool_calls_has_no_evidence() -> None:
    draft = ComplianceFinding(disposition="flag", confidence="medium", finding_text="text")
    report = GroundingReport(claims=[], unsupported=0, confidence="high")
    published = publish_node(make_state(draft_finding=draft, grounding_report=report))[
        "published_finding"
    ]
    assert isinstance(published, PublishedFinding)
    assert published.evidence == []
