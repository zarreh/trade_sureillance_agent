import sqlite3
from pathlib import Path

import pytest

from data.build_store import build_facts_db
from data.scenarios import SCENARIOS, inject_scenarios_into

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "edgar_sample"


@pytest.fixture
def facts_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "facts.db"
    build_facts_db(FIXTURE_DIR, db_path)
    inject_scenarios_into(db_path)
    return db_path


def test_ten_canonical_scenarios_defined() -> None:
    assert len(SCENARIOS) == 10
    assert len({s.id for s in SCENARIOS}) == 10
    assert len({s.accession_number for s in SCENARIOS}) == 10


def test_scenarios_are_queryable_after_injection(facts_db: Path) -> None:
    with sqlite3.connect(facts_db) as conn:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE accession_number LIKE 'SCENARIO-%'"
        ).fetchone()
    # 10 scenarios, plus: scenario 7's companion F line, scenario 8's prior
    # trade (isolates the rolling-90d rule from the single-trade one), and
    # scenario 9's superseded original (isolates supersession-exclusion).
    assert count == 13


def test_scenario_07_shares_accession_between_f_and_s_lines(facts_db: Path) -> None:
    scenario_07 = next(s for s in SCENARIOS if s.id == "scenario-07-f-does-not-clear-s")
    with sqlite3.connect(facts_db) as conn:
        rows = conn.execute(
            "SELECT trans_code, trans_shares FROM transactions WHERE accession_number = ?",
            (scenario_07.accession_number,),
        ).fetchall()
    codes = {code for code, _ in rows}
    assert codes == {"S", "F"}


def test_scenario_08_prior_trade_is_within_the_rolling_90d_window(facts_db: Path) -> None:
    with sqlite3.connect(facts_db) as conn:
        row = conn.execute(
            "SELECT trans_date, rptowner_cik FROM transactions "
            "WHERE accession_number = 'SCENARIO-0000000001-25-000008-PRIOR'"
        ).fetchone()
    assert row is not None
    trans_date, rptowner_cik = row
    assert rptowner_cik == "9000000008"
    assert trans_date == "2025-06-01"


def test_scenario_09_original_is_marked_superseded_by_the_amendment(facts_db: Path) -> None:
    scenario_09 = next(s for s in SCENARIOS if s.id == "scenario-09-amend-away")
    with sqlite3.connect(facts_db) as conn:
        row = conn.execute(
            "SELECT superseded, superseded_by FROM transactions "
            "WHERE accession_number = 'SCENARIO-0000000001-25-000009'"
        ).fetchone()
    assert row is not None
    superseded, superseded_by = row
    assert bool(superseded) is True
    assert superseded_by == scenario_09.accession_number


def test_5_and_6_are_clear_and_7_is_escalate() -> None:
    by_id = {s.id: s for s in SCENARIOS}
    assert by_id["scenario-05-10b5-1-sale"].expected_disposition == "clear"
    assert by_id["scenario-06-tax-withholding"].expected_disposition == "clear"
    assert by_id["scenario-07-f-does-not-clear-s"].expected_disposition == "escalate"
