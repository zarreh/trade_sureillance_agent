"""Seeded generator for the synthetic firm-policy database — docs/PLAN.md §4.1,
Appendix A. Values here are synthetic firm policy, not SEC rules; the real
regulatory citations live separately in docs/regulatory_basis.md.

Corrections vs. the course source (Appendix A):
- role_limits is keyed on (relationship, authorization_level), not free-text
  titles — the source had 18 near-duplicate rows purely from string matching.
- quarterly_limit is named rolling_90d_limit so it cannot be read as a
  calendar quarter (docs/PLAN.md §4.4).
- material_events is new: a deterministic evidence source for blackout/timing
  rules, so the model is never asked to invent an earnings date.
"""

from __future__ import annotations

import random
import sqlite3
from pathlib import Path

SEED = 42

# (relationship, authorization_level) -> (single_trade_limit, rolling_90d_limit,
# blackout_restrictions)
ROLE_LIMITS: dict[tuple[str, str], tuple[int, int, str]] = {
    ("Officer", "Executive"): (10_000_000, 50_000_000, "High"),
    ("Officer", "Senior"): (3_000_000, 15_000_000, "Medium"),
    ("Director", "Board"): (3_000_000, 15_000_000, "High"),
    ("TenPercentOwner", "MajorShareholder"): (5_000_000, 25_000_000, "Medium"),
    ("Default", "Standard"): (1_000_000, 5_000_000, "Low"),
}

# Title -> (relationship, authorization_level) alias, for display and lookup refinement only.
TITLE_ALIASES: dict[str, tuple[str, str]] = {
    "President and CEO": ("Officer", "Executive"),
    "Chief Executive Officer": ("Officer", "Executive"),
    "Chief Financial Officer": ("Officer", "Executive"),
    "Chief Operating Officer": ("Officer", "Executive"),
    "Vice President": ("Officer", "Senior"),
    "Senior Vice President": ("Officer", "Senior"),
    "General Counsel": ("Officer", "Senior"),
    "Director": ("Director", "Board"),
}

COMPLIANCE_RULES = [
    ("R001", "Single Trade Limit Exceeded", None, "single_limit", "High"),
    ("R002", "Rolling 90-Day Volume Exceeded", None, "rolling_90d_limit", "High"),
    ("R003", "Unusual Sale Pattern (Rapid Trading)", 3, "pattern", "Medium"),
    ("R004", "Large Sale After Recent Acquisition", None, "timing", "Critical"),
    ("R005", "Suspicious Timing Near Earnings", 5, "timing", "Critical"),
    ("R006", "High Volume Spike vs. Own Baseline", 150_000, "volume_spike", "Medium"),
    ("R007", "Late Section 16(a) Filing (> 2 trading days)", 2, "filing_lateness", "High"),
    ("R008", "Reported Rule 10b5-1 Plan (severity reducer)", None, "exculpatory", "Low"),
    ("R009", "Tax-Withholding Disposition (Code F, severity reducer)", None, "exculpatory", "Low"),
    ("R010", "Option Exercise (Code M, severity reducer)", None, "exculpatory", "Low"),
]


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS role_limits;
        DROP TABLE IF EXISTS compliance_rules;
        DROP TABLE IF EXISTS material_events;

        CREATE TABLE role_limits (
            relationship TEXT NOT NULL,
            authorization_level TEXT NOT NULL,
            single_trade_limit INTEGER NOT NULL,
            rolling_90d_limit INTEGER NOT NULL,
            blackout_restrictions TEXT NOT NULL,
            PRIMARY KEY (relationship, authorization_level)
        );

        CREATE TABLE title_aliases (
            title TEXT PRIMARY KEY,
            relationship TEXT NOT NULL,
            authorization_level TEXT NOT NULL
        );

        CREATE TABLE compliance_rules (
            rule_id TEXT PRIMARY KEY,
            rule_name TEXT NOT NULL,
            threshold_value INTEGER,
            rule_type TEXT NOT NULL,
            severity TEXT NOT NULL
        );

        CREATE TABLE material_events (
            issuer_cik TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            blackout_start TEXT NOT NULL,
            blackout_end TEXT NOT NULL
        );
        """
    )


def _seed_material_events(conn: sqlite3.Connection, issuer_ciks: list[str], seed: int) -> None:
    """Synthetic earnings calendar: one quarterly event per issuer, with a
    blackout window opening 10 calendar days before and closing 2 days after.
    """
    rng = random.Random(seed)
    rows = []
    for cik in issuer_ciks:
        month = rng.choice([1, 4, 7, 10])
        day = rng.randint(15, 25)
        event_date = f"2025-{month:02d}-{day:02d}"
        import datetime

        event_dt = datetime.date(2025, month, day)
        blackout_start = (event_dt - datetime.timedelta(days=10)).isoformat()
        blackout_end = (event_dt + datetime.timedelta(days=2)).isoformat()
        rows.append((cik, "earnings", event_date, blackout_start, blackout_end))
    conn.executemany(
        "INSERT INTO material_events VALUES (?, ?, ?, ?, ?)",
        rows,
    )


def build_policy_db(db_path: Path, issuer_ciks: list[str] | None = None, seed: int = SEED) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        _create_schema(conn)
        conn.executemany(
            "INSERT INTO role_limits VALUES (?, ?, ?, ?, ?)",
            [
                (rel, level, single, rolling, blackout)
                for (rel, level), (single, rolling, blackout) in ROLE_LIMITS.items()
            ],
        )
        conn.executemany(
            "INSERT INTO title_aliases VALUES (?, ?, ?)",
            [(title, rel, level) for title, (rel, level) in TITLE_ALIASES.items()],
        )
        conn.executemany("INSERT INTO compliance_rules VALUES (?, ?, ?, ?, ?)", COMPLIANCE_RULES)
        if issuer_ciks:
            _seed_material_events(conn, issuer_ciks, seed)
        conn.commit()


def main() -> None:
    from surveillance.settings import get_settings

    settings = get_settings()
    build_policy_db(Path(settings.policy_db_path))
    print(f"Built {settings.policy_db_path}")


if __name__ == "__main__":
    main()
