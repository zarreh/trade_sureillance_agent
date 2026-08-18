"""Retrieves every transaction line reported in one SEC Form 4 filing.

A filing can report several lines (e.g. a tax-withholding disposition and a
sale together); returning the whole accession — not one row — is what lets the
grounding judge see that an exemption on one line must not clear another
(docs/PLAN.md §4.3, canonical scenario 7).
"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from surveillance.store.fact_store import FactStore
from surveillance.store.models import Transaction

MAX_LINES = 50


class GetTransactionDetailsArgs(BaseModel):
    accession_number: str = Field(description="SEC filing identifier, e.g. '0001234567-25-000001'")


def _transaction_line(t: Transaction) -> dict[str, object]:
    return {
        "nonderiv_trans_sk": t.nonderiv_trans_sk,
        "trans_date": t.trans_date,
        "trans_code": t.trans_code,
        "trans_shares": t.trans_shares,
        "trans_priceper_share": t.trans_priceper_share,
        "trans_value": t.trans_value,
        "trans_acquired_disp_cd": t.trans_acquired_disp_cd,
        "shrs_ownd_folwng_trans": t.shrs_ownd_folwng_trans,
        "superseded": t.superseded,
        "superseded_by": t.superseded_by,
    }


def build_get_transaction_details_tool(fact_store: FactStore) -> StructuredTool:
    def get_transaction_details(accession_number: str) -> str:
        """Retrieve every transaction line reported in a SEC Form 4 filing,
        plus the filing and insider context shared by all of them.

        Args:
            accession_number: SEC filing identifier (e.g. '0001234567-25-000001').

        Returns:
            JSON with filing metadata, insider identity, and a list of
            transaction lines — a filing may report more than one line.
        """
        lines = fact_store.transactions_for_accession(accession_number)
        if not lines:
            return json.dumps({"error": f"Accession {accession_number} not found"})
        head = lines[0]
        result = {
            "accession_number": head.accession_number,
            "issuer_cik": head.issuer_cik,
            "issuer_name": head.issuer_name,
            "issuer_ticker": head.issuer_ticker,
            "filing_date": head.filing_date,
            "document_type": head.document_type,
            "reported_under_10b5_1": head.reported_under_10b5_1,
            "filing_lag_trading_days": head.filing_lag_trading_days,
            "rptowner_cik": head.rptowner_cik,
            "rptowner_name": head.rptowner_name,
            "rptowner_relationship": head.rptowner_relationship,
            "rptowner_title": head.rptowner_title,
            "transactions": [_transaction_line(t) for t in lines[:MAX_LINES]],
            "transaction_count": len(lines),
        }
        return json.dumps(result, indent=2)

    return StructuredTool.from_function(
        func=get_transaction_details,
        name="get_transaction_details",
        args_schema=GetTransactionDetailsArgs,
    )
