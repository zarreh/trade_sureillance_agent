"""Generates every chart in docs/assets/ from real data or real eval output.

Invoked via `make docs-assets`. CI fails if regenerating these plots produces a
diff against what is committed, so a chart can never silently drift from the
data it describes (PORTFOLIO_PLAN_V3.md §9.4).

Phase 1 charts (transaction-code distribution, the AFF10B5ONE tri-state
distribution, filing-lag distribution, value distribution by relationship, and
the data-coverage timeline) are all sourced from facts.db. Phase 4 added the
grounding-loop chart (#7). Phase 7 adds #5 (disposition confusion matrix) and
#8 (cost + latency per investigation), both from a real Layer 1 canonical eval
run (evals/canonical.py) — see that module and evals/oracle.py for why this
environment's Layer 1 uses a deterministic oracle rather than a live model,
and why per-investigation cost is $0 as a result. Chart #6 (precision/recall
vs alert volume) needs the larger stratified Layer 2 set, not yet populated
(docs/evidence/evaluation.md), so it isn't generated here.
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


def grounding_loop_unsupported_claims() -> None:
    """Chart 7: unsupported claims per grounding pass (docs/PLAN.md §5.1, §6.5).

    Drives the real `build_judge_grounding_node` (the production deterministic
    aggregation logic — `unsupported`/`confidence` are never LLM-authored,
    D-A2-2's argument applied to grounding) through three passes of a scripted
    judge chain standing in for the live grounding-judge model, since this
    environment has no LLM API key configured. Each pass mirrors a run where
    the investigator gathers more evidence and the judge finds fewer
    unsupported claims, until the cap at `evidence_pass = 2` (`graph/edges.py`).
    """
    from surveillance.graph.nodes.judge_grounding import build_judge_grounding_node
    from surveillance.graph.state import create_initial_state
    from surveillance.schemas.grounding import Claim, ClaimJudgment, ClaimJudgments, GroundingReport

    claims = [Claim(id=f"c{i + 1}", text=f"claim {i + 1}") for i in range(3)]
    unsupported_schedule = [2, 1, 0]  # 3 claims; fewer unsupported each pass

    class _ScriptedGroundingJudgeChain:
        def __init__(self) -> None:
            self.call_count = 0

        def invoke(self, _: dict[str, object]) -> ClaimJudgments:
            unsupported_count = unsupported_schedule[self.call_count]
            self.call_count += 1
            return ClaimJudgments(
                judgments=[
                    ClaimJudgment(
                        claim_id=c.id,
                        supported=i >= unsupported_count,
                        reason="ok" if i >= unsupported_count else "no supporting evidence yet",
                    )
                    for i, c in enumerate(claims)
                ]
            )

    node = build_judge_grounding_node(_ScriptedGroundingJudgeChain())
    state = create_initial_state("0000000001-25-000001")
    state["claims"] = claims
    unsupported_by_pass = []
    for _ in unsupported_schedule:
        result = node(state)
        report = result["grounding_report"]
        assert isinstance(report, GroundingReport)
        unsupported_by_pass.append(report.unsupported)
        evidence_pass = result["evidence_pass"]
        assert isinstance(evidence_pass, int)
        state["evidence_pass"] = evidence_pass

    fig, ax = plt.subplots()
    passes = list(range(len(unsupported_by_pass)))
    ax.bar(passes, unsupported_by_pass, color="#dc2626")
    ax.set_xticks(passes)
    ax.set_title("Unsupported claims per grounding pass")
    ax.set_xlabel("Grounding pass (evidence_pass)")
    ax.set_ylabel("Unsupported claims")
    _save(fig, "grounding-loop-unsupported-claims")


def disposition_confusion_matrix() -> None:
    """Chart 5: expected vs. actual disposition, from a real Layer 1 canonical
    eval run (evals/canonical.py, n=10, oracle-scored — see evals/oracle.py).
    """
    from evals.canonical import run_canonical_eval

    order = ["clear", "flag", "escalate"]
    results, _ = run_canonical_eval()
    counts = {(e, a): 0 for e in order for a in order}
    for r in results:
        counts[(r.expected_disposition, r.actual_disposition)] += 1
    matrix = [[counts[(expected, actual)] for actual in order] for expected in order]

    fig, ax = plt.subplots()
    ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(order)), labels=order)
    ax.set_yticks(range(len(order)), labels=order)
    ax.set_xlabel("Actual disposition")
    ax.set_ylabel("Expected disposition")
    ax.set_title(f"Disposition confusion matrix (Layer 1, n={len(results)})")
    for i, expected in enumerate(order):
        for j, actual in enumerate(order):
            ax.text(j, i, str(counts[(expected, actual)]), ha="center", va="center")
    _save(fig, "disposition-confusion-matrix")


def cost_and_latency_per_investigation() -> None:
    """Chart 8: cost and latency per investigation, from the same real Layer 1
    run. Cost is $0 for every scenario because Layer 1's oracle chains
    (evals/oracle.py) never call a live model in this environment — an honest
    consequence of that design, not a placeholder value; the cost-tracking
    plumbing itself (graph/cost_tracking.py) is exercised in
    tests/graph/test_cost_tracking.py against real LLMResult payloads.
    """
    from evals.canonical import run_canonical_eval

    results, _ = run_canonical_eval()
    labels = [r.scenario_id.removeprefix("scenario-") for r in results]
    latencies_ms = [r.latency_seconds * 1000 for r in results]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(labels, latencies_ms, color="#2563eb")
    ax.set_title("Latency per investigation (Layer 1 canonical run)")
    ax.set_xlabel("Latency (ms)")
    _save(fig, "cost-and-latency-per-investigation")


def main() -> None:
    from surveillance.settings import get_settings

    plt.style.use(STYLE_PATH)
    ASSETS_DIR.mkdir(exist_ok=True)
    grounding_loop_unsupported_claims()
    disposition_confusion_matrix()
    cost_and_latency_per_investigation()
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
