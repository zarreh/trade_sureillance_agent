import json

from surveillance.store.fact_store import FactStore
from surveillance.tools.rolling_90d_trading_volume import build_rolling_90d_trading_volume_tool


def test_aggregates_by_code_within_window(fact_store: FactStore) -> None:
    # NGUYEN LAN (0001234571) has a purchase (P, 800*12.50=10000) and a sale
    # (S, 50000*5.00=250000) both within 90 days of 2025-07-31.
    tool = build_rolling_90d_trading_volume_tool(fact_store)
    result = json.loads(tool.invoke({"rptowner_cik": "0001234571", "as_of_date": "2025-07-31"}))
    assert result["purchases_volume"] == 10_000
    assert result["sales_volume"] == 250_000
    assert result["total_volume"] == 260_000
    assert result["transaction_count"] == 2


def test_anchored_to_as_of_date_not_now(fact_store: FactStore) -> None:
    # Anchoring far in the past must exclude the July 2025 transactions.
    tool = build_rolling_90d_trading_volume_tool(fact_store)
    result = json.loads(tool.invoke({"rptowner_cik": "0001234571", "as_of_date": "2020-01-01"}))
    assert result["transaction_count"] == 0


def test_unknown_insider_returns_empty_window(fact_store: FactStore) -> None:
    tool = build_rolling_90d_trading_volume_tool(fact_store)
    result = json.loads(tool.invoke({"rptowner_cik": "9999999999", "as_of_date": "2025-07-31"}))
    assert result["total_volume"] == 0
