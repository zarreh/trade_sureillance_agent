"""Date parsing and NYSE trading-day arithmetic — docs/PLAN.md §4.4.

Two acceptance criteria live here: EDGAR dates are DD-MON-YYYY and a malformed
one must fail the build loudly (never silently coerce to NaT), and Section
16(a) lateness is measured in NYSE trading days, not calendar days or a generic
business-day calendar.
"""

from __future__ import annotations

import pandas as pd
import pandas_market_calendars as mcal

EDGAR_DATE_FORMAT = "%d-%b-%Y"  # e.g. "01-JUL-2025"

_NYSE = mcal.get_calendar("NYSE")


class DataQualityError(RuntimeError):
    """Raised when required data fails validation. The build must fail, not coerce."""


def parse_edgar_dates(series: pd.Series, column: str) -> pd.Series:
    """Parses a required DD-MON-YYYY date column.

    Raises DataQualityError listing every value that failed to parse, instead
    of the source notebook's `errors="coerce"`, which silently turned every
    date into NaT and left two of five tools permanently dead.
    """
    non_blank = series.astype(str).str.strip().replace({"nan": "", "None": ""})
    parsed = pd.to_datetime(non_blank, format=EDGAR_DATE_FORMAT, errors="coerce")
    failed_mask = parsed.isna() & (non_blank != "")
    if failed_mask.any():
        bad_values = non_blank[failed_mask].unique().tolist()
        raise DataQualityError(
            f"{failed_mask.sum()} value(s) in required date column {column!r} did not "
            f"match DD-MON-YYYY (e.g. '01-JUL-2025'): {bad_values[:5]}"
        )
    return parsed


def parse_required_edgar_dates(series: pd.Series, column: str) -> pd.Series:
    """As parse_edgar_dates, but blank values are also a failure — the column is mandatory."""
    parsed = parse_edgar_dates(series, column)
    if parsed.isna().any():
        raise DataQualityError(f"{parsed.isna().sum()} missing required value(s) in {column!r}")
    return parsed


def nyse_trading_days_between(start: pd.Series, end: pd.Series) -> pd.Series:
    """Counts NYSE trading days strictly after `start` and up to/including `end`.

    Used for the Section 16(a) two-trading-day filing deadline. Deliberately
    NOT `numpy.busday_count` with default US holidays — the SEC deadline runs
    on NYSE trading days, which differ from a generic Mon-Fri calendar around
    exchange holidays. See docs/regulatory_basis.md for the calendar citation.
    """
    if start.isna().any() or end.isna().any():
        raise DataQualityError("nyse_trading_days_between requires non-null dates")
    schedule = _NYSE.schedule(start_date=start.min(), end_date=end.max())
    trading_days = pd.DatetimeIndex(schedule.index.date)
    start_idx = trading_days.searchsorted(pd.DatetimeIndex(start.dt.date), side="right")
    end_idx = trading_days.searchsorted(pd.DatetimeIndex(end.dt.date), side="right")
    return pd.Series(end_idx - start_idx, index=start.index, dtype="int64")
