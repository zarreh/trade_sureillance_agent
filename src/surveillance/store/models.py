"""Typed row models for the fact and policy stores. Plain dataclasses, not
Pydantic — these are internal read models, not API/tool boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Transaction:
    accession_number: str
    nonderiv_trans_sk: int
    issuer_cik: str
    issuer_name: str
    issuer_ticker: str
    filing_date: str
    period_of_report: str
    date_of_orig_sub: str | None
    document_type: str
    reported_under_10b5_1: str  # "true" | "false" | "unknown"
    rptowner_cik: str
    rptowner_name: str
    rptowner_relationship: str
    rptowner_title: str
    trans_date: str
    trans_code: str
    trans_shares: float
    trans_priceper_share: float
    trans_value: float
    trans_acquired_disp_cd: str
    shrs_ownd_folwng_trans: float | None
    direct_indirect_ownership: str
    filing_lag_trading_days: int
    superseded: bool
    superseded_by: str | None


@dataclass(frozen=True)
class RoleLimit:
    relationship: str
    authorization_level: str
    single_trade_limit: int
    rolling_90d_limit: int
    blackout_restrictions: str


@dataclass(frozen=True)
class ComplianceRule:
    rule_id: str
    rule_name: str
    threshold_value: int | None
    rule_type: str
    severity: str


@dataclass(frozen=True)
class MaterialEvent:
    issuer_cik: str
    event_type: str
    event_date: str
    blackout_start: str
    blackout_end: str
