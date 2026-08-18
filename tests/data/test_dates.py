import pandas as pd
import pytest

from data.dates import DataQualityError, nyse_trading_days_between, parse_required_edgar_dates


def test_parses_dd_mon_yyyy() -> None:
    parsed = parse_required_edgar_dates(pd.Series(["01-JUL-2025", "31-DEC-2024"]), "TRANS_DATE")
    assert parsed.tolist() == [pd.Timestamp("2025-07-01"), pd.Timestamp("2024-12-31")]


def test_rejects_iso_format_instead_of_silently_coercing() -> None:
    """The source notebook's exact bug: %Y-%m-%d against DD-MON-YYYY data -> all NaT."""
    with pytest.raises(DataQualityError, match="TRANS_DATE"):
        parse_required_edgar_dates(pd.Series(["2025-07-01"]), "TRANS_DATE")


def test_rejects_missing_required_date() -> None:
    with pytest.raises(DataQualityError):
        parse_required_edgar_dates(pd.Series(["01-JUL-2025", ""]), "FILING_DATE")


def test_nyse_trading_days_between_skips_weekends_and_holidays() -> None:
    # Tue 1-Jul-2025 -> Thu 3-Jul-2025: Wed + Thu = 2 trading days.
    # Fri 4-Jul-2025 is an NYSE holiday (Independence Day), so it never counts.
    start = pd.Series([pd.Timestamp("2025-07-01")])
    end = pd.Series([pd.Timestamp("2025-07-03")])
    assert nyse_trading_days_between(start, end).iloc[0] == 2


def test_nyse_trading_days_between_rejects_null_dates() -> None:
    with pytest.raises(DataQualityError):
        nyse_trading_days_between(pd.Series([pd.NaT]), pd.Series([pd.Timestamp("2025-07-01")]))
