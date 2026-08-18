import json

from surveillance.store.policy_store import PolicyStore
from surveillance.tools.get_applicable_role_limits import build_get_applicable_role_limits_tool


def test_resolves_by_title_alias(policy_store: PolicyStore) -> None:
    tool = build_get_applicable_role_limits_tool(policy_store)
    result = json.loads(
        tool.invoke({"relationship": "Officer", "title": "Chief Financial Officer"})
    )
    assert result["authorization_level"] == "Executive"
    assert result["single_trade_limit"] == 10_000_000


def test_resolves_by_relationship_without_title(policy_store: PolicyStore) -> None:
    tool = build_get_applicable_role_limits_tool(policy_store)
    result = json.loads(tool.invoke({"relationship": "Director"}))
    assert result["relationship"] == "Director"


def test_never_asserts_authorization_in_shape(policy_store: PolicyStore) -> None:
    """The response describes an applicable limit — it must not contain an
    'authorized' or 'pre_cleared' field asserting the trade itself was cleared."""
    tool = build_get_applicable_role_limits_tool(policy_store)
    result = json.loads(tool.invoke({"relationship": "Officer", "title": "CEO"}))
    assert "authorized" not in result
    assert "pre_cleared" not in result
