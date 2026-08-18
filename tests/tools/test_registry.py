from surveillance.store.fact_store import FactStore
from surveillance.store.policy_store import PolicyStore
from surveillance.tools.registry import build_tools


def test_returns_all_six_tools(fact_store: FactStore, policy_store: PolicyStore) -> None:
    tools = build_tools(fact_store, policy_store)
    names = {t.name for t in tools}
    assert names == {
        "get_transaction_details",
        "get_applicable_role_limits",
        "get_compliance_rules",
        "rolling_90d_trading_volume",
        "insider_trading_baseline",
        "get_material_events",
    }


def test_each_tool_is_invokable_with_no_llm(
    fact_store: FactStore, policy_store: PolicyStore
) -> None:
    tools = {t.name: t for t in build_tools(fact_store, policy_store)}
    assert "0000000001-25-000001" in tools["get_transaction_details"].invoke(
        {"accession_number": "0000000001-25-000001"}
    )
    assert "single_trade_limit" in tools["get_applicable_role_limits"].invoke(
        {"relationship": "Officer"}
    )
    assert "rule_id" in tools["get_compliance_rules"].invoke({})
    assert "total_volume" in tools["rolling_90d_trading_volume"].invoke(
        {"rptowner_cik": "0001234571", "as_of_date": "2025-07-31"}
    )
    assert "transaction_count" in tools["insider_trading_baseline"].invoke(
        {"rptowner_cik": "0001234571", "as_of_date": "2025-07-31"}
    )
    assert "in_blackout" in tools["get_material_events"].invoke(
        {"issuer_cik": "0000320193", "on_date": "2025-07-01"}
    )
