"""Read-only repository over facts.db — the merged, validated EDGAR transaction
store built by data/build_store.py. Every query here excludes superseded rows
unless explicitly asked for them (docs/PLAN.md §4.4).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from surveillance.store.models import Transaction

_COLUMNS = [
    "accession_number",
    "nonderiv_trans_sk",
    "issuer_cik",
    "issuer_name",
    "issuer_ticker",
    "filing_date",
    "period_of_report",
    "date_of_orig_sub",
    "document_type",
    "reported_under_10b5_1",
    "rptowner_cik",
    "rptowner_name",
    "rptowner_relationship",
    "rptowner_title",
    "trans_date",
    "trans_code",
    "trans_shares",
    "trans_priceper_share",
    "trans_value",
    "trans_acquired_disp_cd",
    "shrs_ownd_folwng_trans",
    "direct_indirect_ownership",
    "filing_lag_trading_days",
    "superseded",
    "superseded_by",
]


def _row_to_transaction(row: tuple[object, ...]) -> Transaction:
    values = dict(zip(_COLUMNS, row, strict=True))
    values["superseded"] = bool(values["superseded"])
    return Transaction(**values)  # type: ignore[arg-type]


class FactStore:
    """Read-only access to the transactions table in facts.db."""

    def __init__(self, db_path: Path) -> None:
        self._conn = sqlite3.connect(db_path)

    def close(self) -> None:
        self._conn.close()

    def get_transaction(self, accession_number: str) -> Transaction | None:
        row = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM transactions WHERE accession_number = ?",
            (accession_number,),
        ).fetchone()
        return _row_to_transaction(row) if row else None

    def transactions_for_accession(self, accession_number: str) -> list[Transaction]:
        """Every transaction line reported in one filing.

        A single Form 4 accession can report several lines (e.g. a tax
        withholding and a sale together) — an exemption established for one
        line must never be read as clearing another (docs/PLAN.md §4.3).
        """
        rows = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM transactions "
            "WHERE accession_number = ? ORDER BY nonderiv_trans_sk",
            (accession_number,),
        ).fetchall()
        return [_row_to_transaction(r) for r in rows]

    def transactions_in_window(
        self,
        rptowner_cik: str,
        end_date: str,
        window_days: int,
        *,
        include_superseded: bool = False,
    ) -> list[Transaction]:
        """Transactions for an insider in the `window_days` ending at `end_date`, inclusive."""
        superseded_clause = "" if include_superseded else "AND superseded = 0"
        rows = self._conn.execute(
            f"""
            SELECT {", ".join(_COLUMNS)} FROM transactions
            WHERE rptowner_cik = ?
              AND trans_date <= ?
              AND trans_date >= date(?, '-' || ? || ' days')
              {superseded_clause}
            ORDER BY trans_date
            """,
            (rptowner_cik, end_date, end_date, window_days),
        ).fetchall()
        return [_row_to_transaction(r) for r in rows]

    def history_for_insider(
        self,
        rptowner_cik: str,
        trans_code: str | None,
        before_date: str,
        lookback_days: int,
    ) -> list[Transaction]:
        """Historical transactions anchored to `before_date`, never `now()`.

        See docs/PLAN.md §3.1.6.
        """
        code_clause = "AND trans_code = ?" if trans_code else ""
        params: tuple[object, ...] = (
            (rptowner_cik, before_date, before_date, lookback_days, trans_code)
            if trans_code
            else (rptowner_cik, before_date, before_date, lookback_days)
        )
        rows = self._conn.execute(
            f"""
            SELECT {", ".join(_COLUMNS)} FROM transactions
            WHERE rptowner_cik = ?
              AND trans_date < ?
              AND trans_date >= date(?, '-' || ? || ' days')
              AND superseded = 0
              {code_clause}
            ORDER BY trans_date DESC
            """,
            params,
        ).fetchall()
        return [_row_to_transaction(r) for r in rows]
