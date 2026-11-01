"""Writes frontend/src/generated/live-runs.json: every recorded live-model run
(evals/recordings/live-*/summary.json), newest first, for the /evaluation page.

Nothing here calls a model. The numbers are whatever `make eval-live` recorded,
scored with the same `compute_reward`. They are not gated (D-A2-6).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

RECORDINGS_DIR = Path(__file__).parent / "recordings"
OUTPUT_PATH = Path(__file__).parent.parent / "frontend" / "src" / "generated" / "live-runs.json"

# The recordings don't store the prompt version, so the change that separates
# runs is recorded here, next to the data it explains.
CLAIM_EXTRACTOR_BY_RUN = {"2026-10-29": "v1", "2026-10-31": "v1"}
CURRENT_CLAIM_EXTRACTOR = "v2"

_SCENARIO_KEYS = (
    "scenario_id",
    "expected",
    "submitted",
    "correct",
    "reward",
    "outcome_only",
    "trajectory_score",
    "unsupported_claims",
)


def _run(summary: dict[str, Any]) -> dict[str, Any]:
    scenarios = summary["per_scenario"]
    return {
        "run_date": summary["run_date"],
        "n": summary["n"],
        "models": summary["models"],
        "claim_extractor": CLAIM_EXTRACTOR_BY_RUN.get(summary["run_date"], CURRENT_CLAIM_EXTRACTOR),
        "disposition_accuracy": summary["disposition_accuracy"],
        "reward_mean": round(summary["reward_mean"], 4),
        "outcome_only_mean": round(summary["outcome_only_mean"], 4),
        "audit_zero_runs": sum(1 for s in scenarios if s["trajectory_score"] == 0),
        "unsupported_claims_mean": round(
            sum(s["unsupported_claims"] for s in scenarios) / len(scenarios), 2
        ),
        "total_cost_usd": round(summary["total_cost_usd"], 4),
        "mean_latency_seconds": summary["mean_latency_seconds"],
        "uncertainty": summary["uncertainty"],
        "scenarios": [
            {k: (round(s[k], 4) if isinstance(s[k], float) else s[k]) for k in _SCENARIO_KEYS}
            for s in scenarios
        ],
    }


def build_document() -> dict[str, Any]:
    summaries = [
        json.loads((d / "summary.json").read_text())
        for d in sorted(RECORDINGS_DIR.glob("live-*"), reverse=True)
        if (d / "summary.json").exists()
    ]
    return {
        "scorer": "live model, scored with compute_reward; not gated",
        "label_source": "canonical scenarios in data/scenarios.py, designed with their labels",
        "runs": [_run(s) for s in summaries],
    }


def main() -> int:
    OUTPUT_PATH.write_text(json.dumps(build_document(), indent=2) + "\n")
    print(f"wrote {OUTPUT_PATH.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
