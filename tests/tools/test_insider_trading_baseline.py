import json

from surveillance.store.fact_store import FactStore
from surveillance.tools.insider_trading_baseline import build_insider_trading_baseline_tool


def test_computes_distribution_over_own_history(fact_store: FactStore) -> None:
    tool = build_insider_trading_baseline_tool(fact_store)
    result = json.loads(
        tool.invoke(
            {"rptowner_cik": "0001234571", "as_of_date": "2025-07-31", "lookback_days": 180}
        )
    )
    assert result["transaction_count"] == 2
    assert result["mean_value"] == 130_000
    assert result["max_value"] == 250_000


def test_no_history_returns_message(fact_store: FactStore) -> None:
    tool = build_insider_trading_baseline_tool(fact_store)
    result = json.loads(tool.invoke({"rptowner_cik": "9999999999", "as_of_date": "2025-07-31"}))
    assert result["transaction_count"] == 0
    assert "message" in result


def test_default_lookback_is_180_days(fact_store: FactStore) -> None:
    tool = build_insider_trading_baseline_tool(fact_store)
    result = json.loads(tool.invoke({"rptowner_cik": "0001234571", "as_of_date": "2025-07-31"}))
    assert result["lookback_days"] == 180
