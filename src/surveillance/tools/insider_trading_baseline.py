"""An insider's own trailing trading-history distribution, anchored to a date.

Renamed from the source notebook's `search_insider_trading_history`: the
source compared against `pd.Timestamp.now()` while investigating a fixed
historical window, making its lookback meaningless (docs/PLAN.md §3.1.6).
Anchoring to `as_of_date` is what makes a volume-spike comparison meaningful.
"""

from __future__ import annotations

import json
import statistics

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from surveillance.store.fact_store import FactStore

MAX_LISTED_TRANSACTIONS = 10
DEFAULT_LOOKBACK_DAYS = 180


class InsiderTradingBaselineArgs(BaseModel):
    rptowner_cik: str = Field(description="Insider's CIK identifier")
    as_of_date: str = Field(
        description="Anchor date in 'YYYY-MM-DD' format — the transaction date "
        "under investigation, never the current date"
    )
    lookback_days: int = Field(
        default=DEFAULT_LOOKBACK_DAYS, description="How many days before as_of_date to look back"
    )


def build_insider_trading_baseline_tool(fact_store: FactStore) -> StructuredTool:
    def insider_trading_baseline(
        rptowner_cik: str, as_of_date: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS
    ) -> str:
        """Retrieve an insider's own trailing trading history, to compare a
        new transaction against their historical baseline rather than an
        absolute threshold.

        Args:
            rptowner_cik: Insider's CIK identifier.
            as_of_date: Anchor date ('YYYY-MM-DD') — the transaction date
                under investigation, never the current date.
            lookback_days: Lookback window in days (default 180).

        Returns:
            JSON with the insider's historical transaction-value distribution
            and their most recent transactions in the window.
        """
        history = fact_store.history_for_insider(rptowner_cik, None, as_of_date, lookback_days)
        if not history:
            return json.dumps(
                {
                    "rptowner_cik": rptowner_cik,
                    "as_of_date": as_of_date,
                    "lookback_days": lookback_days,
                    "transaction_count": 0,
                    "message": "No prior transactions found in this window",
                }
            )
        values = [t.trans_value for t in history]
        result = {
            "rptowner_cik": rptowner_cik,
            "as_of_date": as_of_date,
            "lookback_days": lookback_days,
            "transaction_count": len(history),
            "mean_value": statistics.fmean(values),
            "median_value": statistics.median(values),
            "max_value": max(values),
            "recent_transactions": [
                {
                    "accession_number": t.accession_number,
                    "trans_date": t.trans_date,
                    "trans_code": t.trans_code,
                    "trans_value": t.trans_value,
                }
                for t in history[:MAX_LISTED_TRANSACTIONS]
            ],
        }
        return json.dumps(result, indent=2)

    return StructuredTool.from_function(
        func=insider_trading_baseline,
        name="insider_trading_baseline",
        args_schema=InsiderTradingBaselineArgs,
    )
