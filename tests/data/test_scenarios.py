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
    # 10 scenarios, one of which (scenario 7) carries a second companion row.
    assert count == 11


def test_scenario_07_shares_accession_between_f_and_s_lines(facts_db: Path) -> None:
    scenario_07 = next(s for s in SCENARIOS if s.id == "scenario-07-f-does-not-clear-s")
    with sqlite3.connect(facts_db) as conn:
        rows = conn.execute(
            "SELECT trans_code, trans_shares FROM transactions WHERE accession_number = ?",
            (scenario_07.accession_number,),
        ).fetchall()
    codes = {code for code, _ in rows}
    assert codes == {"S", "F"}


def test_5_and_6_are_clear_and_7_is_escalate() -> None:
    by_id = {s.id: s for s in SCENARIOS}
    assert by_id["scenario-05-10b5-1-sale"].expected_disposition == "clear"
    assert by_id["scenario-06-tax-withholding"].expected_disposition == "clear"
    assert by_id["scenario-07-f-does-not-clear-s"].expected_disposition == "escalate"
