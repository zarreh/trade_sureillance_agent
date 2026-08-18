import json

from surveillance.store.fact_store import FactStore
from surveillance.tools.get_transaction_details import build_get_transaction_details_tool


def test_returns_all_lines_and_filing_context(fact_store: FactStore) -> None:
    tool = build_get_transaction_details_tool(fact_store)
    result = json.loads(tool.invoke({"accession_number": "0000000001-25-000001"}))
    assert result["issuer_ticker"] == "ACME"
    assert result["rptowner_relationship"] == "Officer"
    assert result["reported_under_10b5_1"] == "true"
    assert result["transaction_count"] == 1
    assert result["transactions"][0]["trans_code"] == "S"
    assert result["transactions"][0]["trans_shares"] == 3000


def test_missing_accession_returns_error(fact_store: FactStore) -> None:
    tool = build_get_transaction_details_tool(fact_store)
    result = json.loads(tool.invoke({"accession_number": "does-not-exist"}))
    assert "error" in result


def test_amendment_row_is_independently_queryable(fact_store: FactStore) -> None:
    tool = build_get_transaction_details_tool(fact_store)
    original = json.loads(tool.invoke({"accession_number": "0000000001-25-000004"}))
    amendment = json.loads(tool.invoke({"accession_number": "0000000001-25-000004-A"}))
    assert original["transactions"][0]["trans_shares"] == 10000
    assert original["transactions"][0]["superseded"] is True
    assert amendment["transactions"][0]["trans_shares"] == 1000
    assert amendment["transactions"][0]["superseded"] is False
