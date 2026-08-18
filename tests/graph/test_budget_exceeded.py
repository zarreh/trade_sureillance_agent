from surveillance.graph.nodes.budget_exceeded import budget_exceeded_node
from surveillance.schemas.finding import ComplianceFinding

from ._state_helpers import make_state


def test_emits_incomplete_finding_with_reason() -> None:
    state = make_state(messages=[], started_at=0.0)
    result = budget_exceeded_node(state)
    finding = result["draft_finding"]
    assert isinstance(finding, ComplianceFinding)
    assert finding.incomplete is True
    assert finding.disposition == "escalate"
    assert finding.incomplete_reason is not None
