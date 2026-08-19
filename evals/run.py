"""CLI entry point for `make eval` (docs/PLAN.md §7 Phase 7).

Runs the Layer 1 canonical regression set and prints the metrics matrix.
Exits non-zero if any canonical scenario doesn't match its expected
disposition — this is what gates pull-request CI.
"""

from __future__ import annotations

import sys

from evals.canonical import print_matrix, run_canonical_eval


def main() -> int:
    results, report = run_canonical_eval()
    print_matrix(results, report)
    mismatches = [r for r in results if r.actual_disposition != r.expected_disposition]
    if mismatches:
        print(
            f"\n{len(mismatches)} canonical scenario(s) did not match their expected disposition."
        )
        return 1
    print("\nAll canonical scenarios matched their expected disposition.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
