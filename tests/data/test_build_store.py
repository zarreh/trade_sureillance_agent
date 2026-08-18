import sqlite3
from pathlib import Path
from typing import Any

import pytest

from data.build_store import build_facts_db

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "edgar_sample"


@pytest.fixture
def facts_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "facts.db"
    build_facts_db(FIXTURE_DIR, db_path)
    return db_path


def _query(db_path: Path, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(sql, params).fetchall()


def test_builds_expected_row_count(facts_db: Path) -> None:
    (count,) = _query(facts_db, "SELECT COUNT(*) FROM transactions")[0]
    assert count == 7  # 6 distinct filings + 1 amendment


def test_zero_null_dates_after_build(facts_db: Path) -> None:
    (bad,) = _query(
        facts_db,
        "SELECT COUNT(*) FROM transactions WHERE filing_date IS NULL OR trans_date IS NULL",
    )[0]
    assert bad == 0


def test_10b5_1_tri_state_normalised(facts_db: Path) -> None:
    rows = _query(
        facts_db,
        "SELECT accession_number, reported_under_10b5_1 FROM transactions "
        "ORDER BY accession_number",
    )
    values = dict(rows)
    assert values["0000000001-25-000001"] == "true"
    assert values["0000000001-25-000002"] == "false"
    assert values["0000000001-25-000004"] == "unknown"  # blank AFF10B5ONE


def test_amendment_supersedes_original(facts_db: Path) -> None:
    rows = _query(
        facts_db,
        "SELECT accession_number, superseded, superseded_by, trans_shares "
        "FROM transactions WHERE issuer_cik = '0000789019' AND rptowner_cik = '0001234570'",
    )
    by_accession = {r[0]: r for r in rows}
    original = by_accession["0000000001-25-000004"]
    amendment = by_accession["0000000001-25-000004-A"]
    assert original[1] == 1  # superseded
    assert original[2] == "0000000001-25-000004-A"
    assert amendment[1] == 0  # authoritative
    assert amendment[3] == 1000  # the amended (corrected) share count


def test_late_filing_exceeds_two_trading_days(facts_db: Path) -> None:
    (lag,) = _query(
        facts_db,
        "SELECT filing_lag_trading_days FROM transactions WHERE accession_number = ?",
        ("0000000001-25-000003",),
    )[0]
    assert lag > 2


def test_on_time_filing_within_two_trading_days(facts_db: Path) -> None:
    (lag,) = _query(
        facts_db,
        "SELECT filing_lag_trading_days FROM transactions WHERE accession_number = ?",
        ("0000000001-25-000001",),
    )[0]
    assert lag <= 2
