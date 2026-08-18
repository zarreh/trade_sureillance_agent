import json

from surveillance.store.policy_store import PolicyStore
from surveillance.tools.get_compliance_rules import build_get_compliance_rules_tool


def test_includes_exemption_and_late_filing_rules(policy_store: PolicyStore) -> None:
    tool = build_get_compliance_rules_tool(policy_store)
    rules = json.loads(tool.invoke({}))
    rule_ids = {r["rule_id"] for r in rules}
    assert {"R007", "R008", "R009", "R010"} <= rule_ids


def test_ordered_by_severity(policy_store: PolicyStore) -> None:
    tool = build_get_compliance_rules_tool(policy_store)
    rules = json.loads(tool.invoke({}))
    severities = [r["severity"] for r in rules]
    assert severities == sorted(severities, reverse=True)
