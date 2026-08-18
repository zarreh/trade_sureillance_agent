"""Generates every chart in docs/assets/ from real data or real eval output.

Invoked via `make docs-assets`. CI fails if regenerating these plots produces a
diff against what is committed, so a chart can never silently drift from the
data it describes (PORTFOLIO_PLAN_V3.md §9.4).

Implemented incrementally: charts 1-4 and 9 in Phase 1, chart 7 in Phase 4,
charts 5/6/8 in Phase 7. Empty in Phase 0 — there is no data yet.
"""

from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets"


def main() -> None:
    ASSETS_DIR.mkdir(exist_ok=True)
    print("No plots to generate yet — see Phase 1 in docs/PLAN.md.")


if __name__ == "__main__":
    main()
