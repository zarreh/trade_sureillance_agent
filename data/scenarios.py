"""Canonical regression scenarios — docs/PLAN.md §4.5, Layer 1.

Each scenario is a fully synthetic accession injected directly into facts.db
under a `SCENARIO-` prefixed accession number, so the canonical set is
deterministic and independent of whatever the live EDGAR fetch contains.
Scenarios double as the goldset consumed by evals/ in Phase 7.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

Disposition = Literal["clear", "flag", "escalate"]


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    expected_disposition: Disposition
    accession_number: str
    issuer_cik: str
    issuer_name: str
    issuer_ticker: str
    rptowner_cik: str
    rptowner_name: str
    rptowner_relationship: str
    rptowner_title: str
    trans_date: str
    filing_date: str
    trans_code: str
    trans_shares: float
    trans_priceper_share: float
    reported_under_10b5_1: str
    filing_lag_trading_days: int
    document_type: str = "4"
    superseded: bool = False
    superseded_by: str | None = None


ISSUER_CIK = "0000320193"
ISSUER_NAME = "Acme Corp"
ISSUER_TICKER = "ACME"

# A deterministic blackout window covering scenarios 1 and 5's trans_date
# (2025-07-18), injected separately from generate_compliance_db.py's random
# per-issuer seeding — the canonical set must be self-contained and not
# depend on whatever month/day that seeding happens to land on for this
# issuer (docs/PLAN.md §4.5: scenarios are deterministic goldset cases).
SCENARIO_MATERIAL_EVENT = {
    "issuer_cik": ISSUER_CIK,
    "event_type": "earnings",
    "event_date": "2025-07-20",
    "blackout_start": "2025-07-10",
    "blackout_end": "2025-07-22",
}

SCENARIOS: list[Scenario] = [
    Scenario(
        id="scenario-01-blackout-sale",
        name="Sale inside a blackout window before a seeded earnings event",
        expected_disposition="flag",
        accession_number="SCENARIO-0000000001-25-000001",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000001",
        rptowner_name="SCENARIO OFFICER ONE",
        rptowner_relationship="Officer",
        rptowner_title="Chief Financial Officer",
        trans_date="2025-07-18",
        filing_date="2025-07-19",
        trans_code="S",
        trans_shares=4000,
        trans_priceper_share=100.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=1,
    ),
    Scenario(
        id="scenario-02-volume-spike",
        name="Volume spike vs. the insider's own trailing baseline",
        expected_disposition="flag",
        accession_number="SCENARIO-0000000001-25-000002",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000002",
        rptowner_name="SCENARIO OFFICER TWO",
        rptowner_relationship="Officer",
        rptowner_title="Vice President",
        trans_date="2025-06-01",
        filing_date="2025-06-02",
        trans_code="S",
        trans_shares=200_000,
        trans_priceper_share=5.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=1,
    ),
    Scenario(
        id="scenario-03-over-limit",
        name="Single trade above the applicable role limit",
        expected_disposition="escalate",
        accession_number="SCENARIO-0000000001-25-000003",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000003",
        rptowner_name="SCENARIO EXECUTIVE THREE",
        rptowner_relationship="Officer",
        rptowner_title="President and CEO",
        trans_date="2025-06-10",
        filing_date="2025-06-11",
        trans_code="S",
        trans_shares=500_000,
        trans_priceper_share=50.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=1,
    ),
    Scenario(
        id="scenario-04-late-filing",
        name="Section 16(a) filing lag > 2 trading days",
        expected_disposition="flag",
        accession_number="SCENARIO-0000000001-25-000004",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000004",
        rptowner_name="SCENARIO DIRECTOR FOUR",
        rptowner_relationship="Director",
        rptowner_title="Director",
        trans_date="2025-06-02",
        filing_date="2025-06-16",
        trans_code="S",
        trans_shares=1000,
        trans_priceper_share=30.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=10,
    ),
    Scenario(
        id="scenario-05-10b5-1-sale",
        name="Sale reported under a 10b5-1 plan, otherwise identical to scenario 1",
        expected_disposition="clear",
        accession_number="SCENARIO-0000000001-25-000005",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000005",
        rptowner_name="SCENARIO OFFICER FIVE",
        rptowner_relationship="Officer",
        rptowner_title="Chief Financial Officer",
        trans_date="2025-07-18",
        filing_date="2025-07-19",
        trans_code="S",
        trans_shares=4000,
        trans_priceper_share=100.0,
        reported_under_10b5_1="true",
        filing_lag_trading_days=1,
    ),
    Scenario(
        id="scenario-06-tax-withholding",
        name="Code F tax-withholding disposition at high value",
        expected_disposition="clear",
        accession_number="SCENARIO-0000000001-25-000006",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000006",
        rptowner_name="SCENARIO OFFICER SIX",
        rptowner_relationship="Officer",
        rptowner_title="Chief Operating Officer",
        trans_date="2025-06-15",
        filing_date="2025-06-16",
        trans_code="F",
        trans_shares=50_000,
        trans_priceper_share=100.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=1,
    ),
    Scenario(
        id="scenario-07-f-does-not-clear-s",
        name=(
            "A Code F line must not clear an unrelated oversized Code S line in the same accession"
        ),
        expected_disposition="escalate",
        accession_number="SCENARIO-0000000001-25-000007",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000007",
        rptowner_name="SCENARIO OFFICER SEVEN",
        rptowner_relationship="Officer",
        rptowner_title="President and CEO",
        trans_date="2025-06-20",
        filing_date="2025-06-21",
        trans_code="S",
        trans_shares=1_000_000,
        trans_priceper_share=60.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=1,
    ),
    Scenario(
        id="scenario-08-rolling-90d-over-limit",
        name="Rolling 90-day volume above the role's limit",
        expected_disposition="flag",
        accession_number="SCENARIO-0000000001-25-000008",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000008",
        rptowner_name="SCENARIO OFFICER EIGHT",
        rptowner_relationship="Officer",
        rptowner_title="Vice President",
        trans_date="2025-07-01",
        filing_date="2025-07-02",
        trans_code="S",
        trans_shares=50_000,
        trans_priceper_share=40.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=1,
    ),
    Scenario(
        id="scenario-09-amend-away",
        name="A 4/A that amends away the transaction driving a flag",
        expected_disposition="clear",
        accession_number="SCENARIO-0000000001-25-000009-A",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000009",
        rptowner_name="SCENARIO OFFICER NINE",
        rptowner_relationship="Officer",
        rptowner_title="Vice President",
        trans_date="2025-06-05",
        filing_date="2025-06-20",
        trans_code="S",
        trans_shares=100,
        trans_priceper_share=30.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=1,
        document_type="4/A",
    ),
    Scenario(
        id="scenario-10-ordinary-purchase",
        name="Ordinary in-limit purchase",
        expected_disposition="clear",
        accession_number="SCENARIO-0000000001-25-000010",
        issuer_cik=ISSUER_CIK,
        issuer_name=ISSUER_NAME,
        issuer_ticker=ISSUER_TICKER,
        rptowner_cik="9000000010",
        rptowner_name="SCENARIO OWNER TEN",
        rptowner_relationship="TenPercentOwner",
        rptowner_title="",
        trans_date="2025-06-12",
        filing_date="2025-06-13",
        trans_code="P",
        trans_shares=500,
        trans_priceper_share=20.0,
        reported_under_10b5_1="unknown",
        filing_lag_trading_days=1,
    ),
]


_INSERT_TRANSACTION_SQL = """
INSERT INTO transactions (
    accession_number, nonderiv_trans_sk, issuer_cik, issuer_name, issuer_ticker,
    filing_date, period_of_report, date_of_orig_sub, document_type,
    reported_under_10b5_1, rptowner_cik, rptowner_name, rptowner_relationship,
    rptowner_title, trans_date, trans_code, trans_shares, trans_priceper_share,
    trans_value, trans_acquired_disp_cd, shrs_ownd_folwng_trans,
    direct_indirect_ownership, filing_lag_trading_days, superseded, superseded_by
) VALUES (
    :accession_number, :nonderiv_trans_sk, :issuer_cik, :issuer_name, :issuer_ticker,
    :filing_date, :period_of_report, :date_of_orig_sub, :document_type,
    :reported_under_10b5_1, :rptowner_cik, :rptowner_name, :rptowner_relationship,
    :rptowner_title, :trans_date, :trans_code, :trans_shares, :trans_priceper_share,
    :trans_value, :trans_acquired_disp_cd, :shrs_ownd_folwng_trans,
    :direct_indirect_ownership, :filing_lag_trading_days, :superseded, :superseded_by
)
"""


def _scenario_row(s: Scenario, *, nonderiv_trans_sk: int = 1) -> dict[str, object]:
    return {
        "accession_number": s.accession_number,
        "nonderiv_trans_sk": nonderiv_trans_sk,
        "issuer_cik": s.issuer_cik,
        "issuer_name": s.issuer_name,
        "issuer_ticker": s.issuer_ticker,
        "filing_date": s.filing_date,
        "period_of_report": s.trans_date,  # approximated by trans_date
        "date_of_orig_sub": None,
        "document_type": s.document_type,
        "reported_under_10b5_1": s.reported_under_10b5_1,
        "rptowner_cik": s.rptowner_cik,
        "rptowner_name": s.rptowner_name,
        "rptowner_relationship": s.rptowner_relationship,
        "rptowner_title": s.rptowner_title,
        "trans_date": s.trans_date,
        "trans_code": s.trans_code,
        "trans_shares": s.trans_shares,
        "trans_priceper_share": s.trans_priceper_share,
        "trans_value": s.trans_shares * s.trans_priceper_share,
        "trans_acquired_disp_cd": "D" if s.trans_code in {"S", "F"} else "A",
        "shrs_ownd_folwng_trans": None,
        "direct_indirect_ownership": "D",
        "filing_lag_trading_days": s.filing_lag_trading_days,
        "superseded": int(s.superseded),
        "superseded_by": s.superseded_by,
    }


def inject_scenarios_into(db_path: Path, scenarios: list[Scenario] = SCENARIOS) -> None:
    """Appends the canonical scenarios to an existing facts.db (built by build_store.py)."""
    with sqlite3.connect(db_path) as conn:
        for s in scenarios:
            conn.execute(_INSERT_TRANSACTION_SQL, _scenario_row(s))
        _inject_scenario_07_companion_row(conn)
        _inject_scenario_08_prior_trade(conn)
        _inject_scenario_09_superseded_original(conn)
        conn.commit()


def inject_scenario_material_event(policy_db_path: Path) -> None:
    """Appends the deterministic scenario blackout window to an existing
    policy.db (built by generate_compliance_db.py)."""
    with sqlite3.connect(policy_db_path) as conn:
        conn.execute(
            "INSERT INTO material_events "
            "(issuer_cik, event_type, event_date, blackout_start, blackout_end) "
            "VALUES (:issuer_cik, :event_type, :event_date, :blackout_start, :blackout_end)",
            SCENARIO_MATERIAL_EVENT,
        )
        conn.commit()


def _inject_scenario_07_companion_row(conn: sqlite3.Connection) -> None:
    """Scenario 7 needs a small Code F line sharing scenario 7's accession, so the
    grounding judge can be tested on whether the F exemption incorrectly bleeds
    over onto the unrelated oversized S line in the same filing (docs/PLAN.md §4.3)."""
    scenario_07 = next(s for s in SCENARIOS if s.id == "scenario-07-f-does-not-clear-s")
    companion = _scenario_row(scenario_07, nonderiv_trans_sk=2)
    companion.update(
        trans_code="F",
        trans_shares=500,
        trans_priceper_share=60.0,
        trans_value=30_000,
    )
    conn.execute(_INSERT_TRANSACTION_SQL, companion)


def _inject_scenario_08_prior_trade(conn: sqlite3.Connection) -> None:
    """Scenario 8 needs a separate prior filing for the same insider, 30 days
    before the transaction under investigation: $2M (this transaction) plus
    $14M (this prior one) clears the $15M rolling 90-day limit while neither
    trade alone clears the $3M single-trade limit — so the scenario actually
    isolates the rolling-volume rule rather than also tripping the single-trade
    one (docs/PLAN.md §4.5)."""
    scenario_08 = next(s for s in SCENARIOS if s.id == "scenario-08-rolling-90d-over-limit")
    prior = replace(
        scenario_08,
        accession_number="SCENARIO-0000000001-25-000008-PRIOR",
        trans_date="2025-06-01",
        filing_date="2025-06-02",
        trans_shares=350_000,
        trans_priceper_share=40.0,
    )
    conn.execute(_INSERT_TRANSACTION_SQL, _scenario_row(prior))


def _inject_scenario_09_superseded_original(conn: sqlite3.Connection) -> None:
    """Scenario 9's amendment (already in SCENARIOS) is small and in-limit on
    its own; to actually exercise supersession-exclusion (docs/PLAN.md §4.4:
    "aggregates read only non-superseded rows") rather than just an ordinary
    small trade, inject the ORIGINAL large, over-limit filing it amends —
    marked superseded so FactStore's rolling-volume aggregate must exclude it
    for the scenario to clear."""
    scenario_09 = next(s for s in SCENARIOS if s.id == "scenario-09-amend-away")
    original = replace(
        scenario_09,
        accession_number="SCENARIO-0000000001-25-000009",
        document_type="4",
        trans_shares=500_000,
        trans_priceper_share=30.0,
        superseded=True,
        superseded_by=scenario_09.accession_number,
    )
    conn.execute(_INSERT_TRANSACTION_SQL, _scenario_row(original))


def main() -> None:
    from surveillance.settings import get_settings

    settings = get_settings()
    inject_scenarios_into(Path(settings.facts_db_path))
    inject_scenario_material_event(Path(settings.policy_db_path))
    print(f"Injected {len(SCENARIOS)} canonical scenarios into {settings.facts_db_path}")
    print(f"Injected the scenario blackout window into {settings.policy_db_path}")


if __name__ == "__main__":
    main()
