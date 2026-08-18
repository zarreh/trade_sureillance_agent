from surveillance.graph.nodes.publish import publish_node
from surveillance.schemas.finding import ComplianceFinding, PublishedFinding
from surveillance.schemas.grounding import GroundingReport

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
