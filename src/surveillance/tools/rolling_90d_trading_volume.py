"""Rolling 90-day trading volume, anchored to a given date — never `now()`.

Renamed from the source notebook's `calculate_quarterly_trading_volume`
(docs/PLAN.md §4.4): "rolling 90-day", never "quarterly", so the finding text
cannot be misread as a fiscal-quarter figure. Aggregation is transaction-code
aware so a naive total doesn't conflate sales with tax withholding.
"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from surveillance.store.fact_store import FactStore
from surveillance.store.models import Transaction

MAX_LISTED_TRANSACTIONS = 20
WINDOW_DAYS = 90


class RollingTradingVolumeArgs(BaseModel):
    rptowner_cik: str = Field(description="Insider's CIK identifier")
    as_of_date: str = Field(
        description="Anchor date in 'YYYY-MM-DD' format — the transaction date "
        "under investigation, never the current date"
    )


def _summarize(transactions: list[Transaction]) -> dict[str, object]:
    by_code: dict[str, float] = {}
    for t in transactions:
        by_code[t.trans_code] = by_code.get(t.trans_code, 0.0) + t.trans_value
    return {
        "total_volume": sum(t.trans_value for t in transactions),
        "sales_volume": sum(t.trans_value for t in transactions if t.trans_code == "S"),
        "purchases_volume": sum(t.trans_value for t in transactions if t.trans_code == "P"),
        "volume_by_code": by_code,
        "transaction_count": len(transactions),
    }


def build_rolling_90d_trading_volume_tool(fact_store: FactStore) -> StructuredTool:
    def rolling_90d_trading_volume(rptowner_cik: str, as_of_date: str) -> str:
        """Calculate an insider's rolling 90-day trading volume ending at a
        given date, broken down by transaction code.

        Args:
            rptowner_cik: Insider's CIK identifier.
            as_of_date: Anchor date ('YYYY-MM-DD') — the transaction date under
                investigation, not the current date.

        Returns:
            JSON with the rolling 90-day volume breakdown and the most recent
            transactions in that window.
        """
        transactions = fact_store.transactions_in_window(rptowner_cik, as_of_date, WINDOW_DAYS)
        if not transactions:
            return json.dumps(
                {
                    "rptowner_cik": rptowner_cik,
                    "window_end": as_of_date,
                    "window_days": WINDOW_DAYS,
                    "total_volume": 0,
                    "transaction_count": 0,
                    "message": "No transactions found in this window",
                }
            )
        summary = _summarize(transactions)
        summary["rptowner_cik"] = rptowner_cik
        summary["window_end"] = as_of_date
        summary["window_days"] = WINDOW_DAYS
        summary["accession_numbers"] = [t.accession_number for t in transactions][
            :MAX_LISTED_TRANSACTIONS
        ]
        return json.dumps(summary, indent=2)

    return StructuredTool.from_function(
        func=rolling_90d_trading_volume,
        name="rolling_90d_trading_volume",
        args_schema=RollingTradingVolumeArgs,
    )
