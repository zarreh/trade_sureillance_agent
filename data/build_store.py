"""EDGAR bulk TSVs -> typed SQLite facts.db. See docs/PLAN.md §4.4 for every
acceptance criterion enforced here: date parsing, AFF10B5ONE normalisation,
NYSE filing-lag, 4/A supersession, and aggregate scoping to non-superseded rows.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from data.dates import DataQualityError, nyse_trading_days_between, parse_required_edgar_dates

TRUE_TOKENS = {"1", "true"}
FALSE_TOKENS = {"0", "false"}

REQUIRED_SUBMISSION_COLUMNS = [
    "ACCESSION_NUMBER",
    "FILING_DATE",
    "PERIOD_OF_REPORT",
    "DATE_OF_ORIG_SUB",
    "DOCUMENT_TYPE",
    "ISSUERCIK",
    "ISSUERNAME",
    "ISSUERTRADINGSYMBOL",
    "AFF10B5ONE",
]


def normalize_10b5_1(series: pd.Series) -> pd.Series:
    """Tri-state normalisation. Unknown means 'not established', never 'no plan'."""

    def _one(value: object) -> str:
        text = str(value).strip().lower()
        if text in TRUE_TOKENS:
            return "true"
        if text in FALSE_TOKENS:
            return "false"
        return "unknown"

    return series.map(_one)


def _quarter_dirs(raw_dir: Path) -> list[Path]:
    """Each quarter fetched by fetch_edgar.py lives in its own subdirectory
    (raw_dir/<quarter>/), since every quarter's zip has identically-named
    TSVs. Falls back to treating raw_dir itself as a single quarter, so the
    fixture-based tests (which have no quarter subdirectory) still work.
    """
    subdirs = sorted(p for p in raw_dir.iterdir() if p.is_dir() and (p / "SUBMISSION.tsv").exists())
    return subdirs if subdirs else [raw_dir]


def load_raw_tsvs(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Loads and concatenates SUBMISSION/REPORTINGOWNER/NONDERIV_TRANS across
    every quarter subdirectory under raw_dir."""
    submission_frames, owner_frames, transaction_frames = [], [], []
    for quarter_dir in _quarter_dirs(raw_dir):
        submission_frames.append(
            pd.read_csv(quarter_dir / "SUBMISSION.tsv", sep="\t", dtype=str, keep_default_na=False)
        )
        owner_frames.append(
            pd.read_csv(
                quarter_dir / "REPORTINGOWNER.tsv", sep="\t", dtype=str, keep_default_na=False
            )
        )
        transaction_frames.append(
            pd.read_csv(
                quarter_dir / "NONDERIV_TRANS.tsv", sep="\t", dtype=str, keep_default_na=False
            )
        )
    submissions = pd.concat(submission_frames, ignore_index=True)
    owners = pd.concat(owner_frames, ignore_index=True)
    transactions = pd.concat(transaction_frames, ignore_index=True)

    missing = [c for c in REQUIRED_SUBMISSION_COLUMNS if c not in submissions.columns]
    if missing:
        raise DataQualityError(f"SUBMISSION.tsv is missing required column(s): {missing}")
    return submissions, owners, transactions


def resolve_supersession(merged: pd.DataFrame) -> pd.DataFrame:
    """Marks amended (4/A) filings as superseding their original.

    Identity is (ISSUERCIK, RPTOWNERCIK, PERIOD_OF_REPORT); the latest
    FILING_DATE within that group is authoritative. Superseded rows are kept,
    not dropped, so the audit trail still shows what was amended away.
    """
    merged = merged.copy()
    group_keys = ["ISSUERCIK", "RPTOWNERCIK", "PERIOD_OF_REPORT"]
    latest_filing = merged.groupby(group_keys)["FILING_DATE"].transform("max")
    latest_accession = (
        merged.sort_values("FILING_DATE").groupby(group_keys)["ACCESSION_NUMBER"].transform("last")
    )
    merged["superseded"] = merged["FILING_DATE"] != latest_filing
    merged["superseded_by"] = latest_accession.where(merged["superseded"])
    return merged


def build_facts_db(raw_dir: Path, db_path: Path) -> None:
    """Builds facts.db from raw EDGAR TSVs. Raises DataQualityError on bad input."""
    submissions, owners, transactions = load_raw_tsvs(raw_dir)

    submissions = submissions.copy()
    submissions["FILING_DATE"] = parse_required_edgar_dates(
        submissions["FILING_DATE"], "FILING_DATE"
    )
    submissions["PERIOD_OF_REPORT"] = parse_required_edgar_dates(
        submissions["PERIOD_OF_REPORT"], "PERIOD_OF_REPORT"
    )
    submissions["reported_under_10b5_1"] = normalize_10b5_1(submissions["AFF10B5ONE"])
    submissions = submissions[submissions["DOCUMENT_TYPE"].isin(["4", "4/A"])]

    transactions = transactions.copy()
    transactions["TRANS_DATE"] = parse_required_edgar_dates(
        transactions["TRANS_DATE"], "TRANS_DATE"
    )
    transactions["TRANS_SHARES"] = pd.to_numeric(transactions["TRANS_SHARES"])
    transactions["TRANS_PRICEPERSHARE"] = pd.to_numeric(transactions["TRANS_PRICEPERSHARE"])
    transactions["TRANS_VALUE"] = transactions["TRANS_SHARES"] * transactions["TRANS_PRICEPERSHARE"]
    transactions["SHRS_OWND_FOLWNG_TRANS"] = pd.to_numeric(
        transactions["SHRS_OWND_FOLWNG_TRANS"], errors="coerce"
    )

    merged = transactions.merge(submissions, on="ACCESSION_NUMBER", how="inner")
    merged = merged.merge(owners, on="ACCESSION_NUMBER", how="left")

    merged = resolve_supersession(merged)
    merged["filing_lag_trading_days"] = nyse_trading_days_between(
        merged["TRANS_DATE"], merged["FILING_DATE"]
    )

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS transactions")
        conn.execute(
            """
            CREATE TABLE transactions (
                accession_number TEXT NOT NULL,
                nonderiv_trans_sk INTEGER,
                issuer_cik TEXT NOT NULL,
                issuer_name TEXT,
                issuer_ticker TEXT,
                filing_date TEXT NOT NULL,
                period_of_report TEXT NOT NULL,
                date_of_orig_sub TEXT,
                document_type TEXT NOT NULL,
                reported_under_10b5_1 TEXT NOT NULL,
                rptowner_cik TEXT NOT NULL,
                rptowner_name TEXT,
                rptowner_relationship TEXT,
                rptowner_title TEXT,
                trans_date TEXT NOT NULL,
                trans_code TEXT NOT NULL,
                trans_shares REAL,
                trans_priceper_share REAL,
                trans_value REAL,
                trans_acquired_disp_cd TEXT,
                shrs_ownd_folwng_trans REAL,
                direct_indirect_ownership TEXT,
                filing_lag_trading_days INTEGER,
                superseded INTEGER NOT NULL,
                superseded_by TEXT
            )
            """
        )
        out = pd.DataFrame(
            {
                "accession_number": merged["ACCESSION_NUMBER"],
                "nonderiv_trans_sk": merged["NONDERIV_TRANS_SK"],
                "issuer_cik": merged["ISSUERCIK"],
                "issuer_name": merged["ISSUERNAME"],
                "issuer_ticker": merged["ISSUERTRADINGSYMBOL"],
                "filing_date": merged["FILING_DATE"].dt.strftime("%Y-%m-%d"),
                "period_of_report": merged["PERIOD_OF_REPORT"].dt.strftime("%Y-%m-%d"),
                "date_of_orig_sub": merged["DATE_OF_ORIG_SUB"].replace("", None),
                "document_type": merged["DOCUMENT_TYPE"],
                "reported_under_10b5_1": merged["reported_under_10b5_1"],
                "rptowner_cik": merged["RPTOWNERCIK"],
                "rptowner_name": merged["RPTOWNERNAME"],
                "rptowner_relationship": merged["RPTOWNER_RELATIONSHIP"],
                "rptowner_title": merged["RPTOWNER_TITLE"],
                "trans_date": merged["TRANS_DATE"].dt.strftime("%Y-%m-%d"),
                "trans_code": merged["TRANS_CODE"],
                "trans_shares": merged["TRANS_SHARES"],
                "trans_priceper_share": merged["TRANS_PRICEPERSHARE"],
                "trans_value": merged["TRANS_VALUE"],
                "trans_acquired_disp_cd": merged["TRANS_ACQUIRED_DISP_CD"],
                "shrs_ownd_folwng_trans": merged["SHRS_OWND_FOLWNG_TRANS"],
                "direct_indirect_ownership": merged["DIRECT_INDIRECT_OWNERSHIP"],
                "filing_lag_trading_days": merged["filing_lag_trading_days"],
                "superseded": merged["superseded"].astype(int),
                "superseded_by": merged["superseded_by"],
            }
        )
        out.to_sql("transactions", conn, if_exists="append", index=False)
        conn.execute("CREATE INDEX idx_transactions_accession ON transactions(accession_number)")
        conn.execute("CREATE INDEX idx_transactions_rptowner ON transactions(rptowner_cik)")
        conn.execute("CREATE INDEX idx_transactions_trans_date ON transactions(trans_date)")
        conn.commit()


def main() -> None:
    from surveillance.settings import get_settings

    settings = get_settings()
    build_facts_db(Path(settings.data_dir) / "raw", Path(settings.facts_db_path))
    print(f"Built {settings.facts_db_path}")


if __name__ == "__main__":
    main()
