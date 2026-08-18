"""Builds the six tools the investigator agent can call.

One store connection each, injected once — not reopened per call, unlike the
source notebook (docs/PLAN.md §3.2).
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from surveillance.store.fact_store import FactStore
from surveillance.store.policy_store import PolicyStore
from surveillance.tools.get_applicable_role_limits import build_get_applicable_role_limits_tool
from surveillance.tools.get_compliance_rules import build_get_compliance_rules_tool
from surveillance.tools.get_material_events import build_get_material_events_tool
from surveillance.tools.get_transaction_details import build_get_transaction_details_tool
from surveillance.tools.insider_trading_baseline import build_insider_trading_baseline_tool
from surveillance.tools.rolling_90d_trading_volume import build_rolling_90d_trading_volume_tool


def build_tools(fact_store: FactStore, policy_store: PolicyStore) -> list[StructuredTool]:
    """Returns all six tools, bound to the given store instances."""
    return [
        build_get_transaction_details_tool(fact_store),
        build_get_applicable_role_limits_tool(policy_store),
        build_get_compliance_rules_tool(policy_store),
        build_rolling_90d_trading_volume_tool(fact_store),
        build_insider_trading_baseline_tool(fact_store),
        build_get_material_events_tool(policy_store),
    ]
