"""Generates every chart in docs/assets/ from real data or real eval output.

Invoked via `make docs-assets`. CI fails if regenerating these plots produces a
diff against what is committed, so a chart can never silently drift from the
data it describes (PORTFOLIO_PLAN_V3.md §9.4).

Phase 1 charts (this file, today): transaction-code distribution, the
AFF10B5ONE tri-state distribution, filing-lag distribution, value distribution
by relationship, and the data-coverage timeline — all sourced from facts.db.
Chart 7 (grounding passes) lands in Phase 4; charts 5/6/8 (evaluation) in
Phase 7.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ASSETS_DIR = Path(__file__).parent / "assets"
STYLE_PATH = ASSETS_DIR / "plot_style.mplstyle"


def _save(fig: plt.Figure, name: str) -> None:
    for theme, colors in (
        ("light", {"fig": "white", "text": "#111827"}),
        ("dark", {"fig": "#0d1117", "text": "#e5e7eb"}),
    ):
        fig.patch.set_facecolor(colors["fig"])
        for ax in fig.axes:
            ax.set_facecolor(colors["fig"])
            ax.tick_params(colors=colors["text"])
            ax.xaxis.label.set_color(colors["text"])
            ax.yaxis.label.set_color(colors["text"])
            ax.title.set_color(colors["text"])
            for spine in ax.spines.values():
                spine.set_color(colors["text"])
        fig.savefig(ASSETS_DIR / f"{name}-{theme}.svg", facecolor=colors["fig"])
    plt.close(fig)


def transaction_code_distribution(conn: sqlite3.Connection) -> None:
    """Chart 1: transaction-code distribution, F and M highlighted (docs/PLAN.md §3.3.8)."""
    df = pd.read_sql(
        "SELECT trans_code, COUNT(*) AS n FROM transactions GROUP BY trans_code ORDER BY n DESC",
        conn,
    )
    highlight = {"F": "#dc2626", "M": "#dc2626"}
    colors = [highlight.get(code, "#2563eb") for code in df["trans_code"]]
    fig, ax = plt.subplots()
    ax.bar(df["trans_code"], df["n"], color=colors)
    ax.set_title("Transaction code distribution (F/M highlighted)")
    ax.set_xlabel("Transaction code")
    ax.set_ylabel("Count")
    _save(fig, "transaction-code-distribution")


def reported_10b5_1_distribution(conn: sqlite3.Connection) -> None:
    """Chart 2: AFF10B5ONE tri-state distribution, including the unknown share."""
    df = pd.read_sql(
        "SELECT reported_under_10b5_1, COUNT(*) AS n FROM transactions GROUP BY 1", conn
    )
    fig, ax = plt.subplots()
    ax.bar(df["reported_under_10b5_1"], df["n"], color=["#059669", "#dc2626", "#d97706"])
    ax.set_title("Reported under a Rule 10b5-1 plan (tri-state)")
    ax.set_ylabel("Count")
    _save(fig, "reported-10b5-1-distribution")


def filing_lag_distribution(conn: sqlite3.Connection) -> None:
    """Chart 3: filing-lag distribution with the 2-trading-day Section 16(a) line."""
    df = pd.read_sql("SELECT filing_lag_trading_days AS lag FROM transactions", conn)
    fig, ax = plt.subplots()
    ax.hist(df["lag"].clip(upper=20), bins=21, color="#2563eb")
    ax.axvline(2, color="#dc2626", linestyle="--", label="Section 16(a) 2-day threshold")
    ax.set_title("Filing lag (NYSE trading days)")
    ax.set_xlabel("Trading days (clipped at 20)")
    ax.set_ylabel("Count")
    ax.legend()
    _save(fig, "filing-lag-distribution")


def value_by_relationship(conn: sqlite3.Connection) -> None:
    """Chart 4: transaction value distribution by relationship, log scale."""
    df = pd.read_sql(
        "SELECT rptowner_relationship, trans_value FROM transactions "
        "WHERE trans_value > 0 AND superseded = 0",
        conn,
    )
    df["primary_relationship"] = df["rptowner_relationship"].str.split(",").str[0]
    top = df["primary_relationship"].value_counts().head(5).index
    fig, ax = plt.subplots()
    ax.boxplot(
        [df.loc[df["primary_relationship"] == r, "trans_value"] for r in top],
        tick_labels=list(top),
        showfliers=False,  # thousands of individual outlier dots is chartjunk, not signal
    )
    ax.set_yscale("log")
    ax.set_title("Transaction value by relationship (log scale)")
    ax.set_ylabel("Transaction value ($, log scale)")
    _save(fig, "value-by-relationship")


def data_coverage_timeline(conn: sqlite3.Connection) -> None:
    """Chart 9: why three quarters are needed for a full 180-day lookback."""
    df = pd.read_sql(
        "SELECT trans_date, COUNT(*) AS n FROM transactions "
        "GROUP BY trans_date ORDER BY trans_date",
        conn,
    )
    df["trans_date"] = pd.to_datetime(df["trans_date"])
    fig, ax = plt.subplots()
    ax.plot(df["trans_date"], df["n"], color="#2563eb")
    ax.set_title("Data coverage: transactions per day across fetched quarters")
    ax.set_xlabel("Transaction date")
    ax.set_ylabel("Transactions")
    _save(fig, "data-coverage-timeline")


def main() -> None:
    from surveillance.settings import get_settings

    plt.style.use(STYLE_PATH)
    ASSETS_DIR.mkdir(exist_ok=True)
    settings = get_settings()
    facts_db_path = Path(settings.facts_db_path)
    if not facts_db_path.exists():
        print(f"{facts_db_path} does not exist yet - run `make data` first. Skipping.")
        return
    with sqlite3.connect(facts_db_path) as conn:
        transaction_code_distribution(conn)
        reported_10b5_1_distribution(conn)
        filing_lag_distribution(conn)
        value_by_relationship(conn)
        data_coverage_timeline(conn)
    print(f"Wrote charts to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
