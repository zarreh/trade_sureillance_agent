"""CLI entry point for `make eval` (docs/PLAN.md §7 Phase 7).

Runs the Layer 1 canonical regression set and prints the metrics matrix.
The run/print/gate shell is `zarreh_agentkit.evals.run_eval_cli` (shared
with A3); the scenario definitions and metrics stay local, per HARVEST #14.
"""

from __future__ import annotations

import sys

from zarreh_agentkit.evals import EvalOutcome, run_eval_cli

from evals.canonical import print_matrix, run_canonical_eval
from evals.metrics import EvalResult, MetricsReport

_Results = tuple[list[EvalResult], MetricsReport]


def _outcomes(results: _Results) -> list[EvalOutcome]:
    rows, _ = results
    return [
        EvalOutcome(case_id=r.scenario_id, passed=r.actual_disposition == r.expected_disposition)
        for r in rows
    ]


def _print_report(results: _Results) -> None:
    rows, report = results
    print_matrix(rows, report)


def main() -> int:
    return run_eval_cli(run_canonical_eval, _print_report, _outcomes)


if __name__ == "__main__":
    sys.exit(main())
