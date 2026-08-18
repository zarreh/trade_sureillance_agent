"""Retrieves the synthetic compliance rule table with severity tiers.

Shape is unchanged from the source notebook — a severity-tiered rule table
rather than a monolithic prompt is one of the things worth keeping
(docs/PLAN.md §3.5).
"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from surveillance.store.policy_store import PolicyStore


class GetComplianceRulesArgs(BaseModel):
    pass


def build_get_compliance_rules_tool(policy_store: PolicyStore) -> StructuredTool:
    def get_compliance_rules() -> str:
        """Retrieve every compliance rule, ordered by severity.

        Returns:
            JSON array of {rule_id, rule_name, threshold_value, rule_type, severity}.
        """
        rules = policy_store.get_compliance_rules()
        return json.dumps(
            [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "threshold_value": r.threshold_value,
                    "rule_type": r.rule_type,
                    "severity": r.severity,
                }
                for r in rules
            ],
            indent=2,
        )

    return StructuredTool.from_function(
        func=get_compliance_rules,
        name="get_compliance_rules",
        args_schema=GetComplianceRulesArgs,
    )
