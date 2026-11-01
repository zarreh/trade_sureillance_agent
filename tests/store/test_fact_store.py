from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from data.build_store import build_facts_db
from surveillance.store.fact_store import FactStore

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "edgar_sample"


@pytest.fixture
def store(tmp_path: Path) -> FactStore:
    db_path = tmp_path / "facts.db"
    build_facts_db(FIXTURE_DIR, db_path)
    return FactStore(db_path)


def test_queryable_from_a_different_thread(store: FactStore) -> None:
    """LangGraph's ToolNode runs sync tools in a worker thread pool — a store
    created on the main thread must still be queryable from there."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        txn = executor.submit(store.get_transaction, "0000000001-25-000001").result()
    assert txn is not None


def test_get_transaction_returns_typed_record(store: FactStore) -> None:
    txn = store.get_transaction("0000000001-25-000001")
    assert txn is not None
    assert txn.trans_code == "S"
    assert txn.trans_shares == 3000
    assert txn.reported_under_10b5_1 == "true"


def test_get_transaction_missing_returns_none(store: FactStore) -> None:
    assert store.get_transaction("does-not-exist") is None


def test_transactions_in_window_excludes_superseded_by_default(store: FactStore) -> None:
    # 0001234570 has an original (superseded) and an amendment (authoritative)
    # on the same trans_date; the window query should return only the amendment.
    results = store.transactions_in_window("0001234570", "2025-07-31", window_days=90)
    assert len(results) == 1
    assert results[0].accession_number == "0000000001-25-000004-A"


def test_transactions_in_window_can_include_superseded(store: FactStore) -> None:
    results = store.transactions_in_window(
        "0001234570", "2025-07-31", window_days=90, include_superseded=True
    )
    assert len(results) == 2


def test_history_for_insider_filters_by_code_and_lookback(store: FactStore) -> None:
    # NGUYEN LAN (0001234571) has a purchase (P) and a sale (S).
    sales_only = store.history_for_insider("0001234571", "S", "2025-07-31", lookback_days=90)
    assert len(sales_only) == 1
    assert sales_only[0].trans_code == "S"

    all_history = store.history_for_insider("0001234571", None, "2025-07-31", lookback_days=90)
    assert len(all_history) == 2


def test_scenario_accessions_lists_only_scenarios(tmp_path: Path) -> None:
    from data.scenarios import SCENARIOS, inject_scenarios_into

    db_path = tmp_path / "facts.db"
    build_facts_db(FIXTURE_DIR, db_path)
    assert FactStore(db_path).scenario_accessions() == []

    inject_scenarios_into(db_path)
    accessions = FactStore(db_path).scenario_accessions()
    assert accessions == sorted({s.accession_number for s in SCENARIOS})
