"""Live-model run of the ten canonical scenarios (not gated, not part of `make eval`).

Runs the real compiled graph with real OpenAI models over the same scenario
stores the gate uses, scores each published finding with the same
`compute_reward` the RL environment uses, and records every transcript so a
later replay harness can replace the scripted stand-in with real responses.

Needs SURVEILLANCE_OPENAI_API_KEY and spends model credits. n=10 supports no
precision claim, and one run's output varies between runs.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import messages_to_dict
from zarreh_agentkit.cost import CostTrackingHandler

from data.scenarios import SCENARIOS, Scenario
from evals.canonical import _build_eval_stores
from evals.rl_env import RewardBreakdown, compute_reward, truncation_reward
from surveillance.graph.builder import build_surveillance_graph
from surveillance.graph.evidence import extract_tool_call_records
from surveillance.graph.state import create_initial_state
from surveillance.graph.trajectory_audit import audit_trajectory, extract_claimed_exemptions
from surveillance.schemas.finding import ComplianceFinding, PublishedFinding
from surveillance.settings import Settings

RECORDINGS_DIR = Path(__file__).parent / "recordings"


def _run_scenario(graph: Any, scenario: Scenario, out_dir: Path) -> dict[str, Any]:
    handler = CostTrackingHandler()
    started = time.perf_counter()
    row: dict[str, Any] = {
        "scenario_id": scenario.id,
        "expected": scenario.expected_disposition,
    }
    try:
        state = graph.invoke(
            create_initial_state(scenario.accession_number),
            config={"callbacks": [handler], "recursion_limit": 100},
        )
    except Exception as exc:  # a provider or schema failure is a result, not a crash
        row.update(error=f"{type(exc).__name__}: {exc}", reward=None, outcome_only=None)
        return row
    latency = time.perf_counter() - started

    published = state.get("published_finding")
    draft = state.get("draft_finding")
    finding = published if isinstance(published, PublishedFinding) else draft
    assert isinstance(finding, ComplianceFinding)
    records = extract_tool_call_records(state["messages"])
    claims = state.get("claims", [])

    breakdown: RewardBreakdown
    if isinstance(published, PublishedFinding) and published.process_audit is not None:
        audit = published.process_audit
        breakdown = compute_reward(
            scenario.expected_disposition, finding.disposition, audit, len(records), 0
        )
    else:
        audit = audit_trajectory(records, claims, extract_claimed_exemptions(claims))
        breakdown = truncation_reward()

    row.update(
        submitted=finding.disposition,
        published=isinstance(published, PublishedFinding),
        incomplete=finding.incomplete,
        correct=finding.disposition == scenario.expected_disposition,
        reward=breakdown.total,
        outcome_only=breakdown.outcome if not breakdown.truncated else None,
        trajectory_score=audit.trajectory_score,
        tool_calls=len(records),
        evidence_passes=state.get("evidence_pass", 0),
        unsupported_claims=(
            published.grounding_report.unsupported
            if isinstance(published, PublishedFinding)
            else None
        ),
        cost_usd=sum(e.cost_usd for e in handler.entries),
        latency_seconds=round(latency, 2),
        models=sorted({e.model for e in handler.entries}),
    )
    transcript = {
        "scenario_id": scenario.id,
        "messages": messages_to_dict(list(state["messages"])),
        "plan": state["plan"].model_dump() if state.get("plan") else None,
        "claims": [c.model_dump() for c in claims],
        "draft_finding": draft.model_dump(mode="json") if draft else None,
        "published_finding": published.model_dump(mode="json") if published else None,
        "costs": [
            {"node": e.node, "model": e.model, "cost_usd": e.cost_usd} for e in handler.entries
        ],
    }
    (out_dir / f"{scenario.id}.json").write_text(json.dumps(transcript, indent=2) + "\n")
    return row


def run_live() -> Path:
    settings = Settings()
    if not settings.openai_api_key:
        raise SystemExit("SURVEILLANCE_OPENAI_API_KEY is not set (see .env.example).")
    run_date = datetime.now(UTC).date().isoformat()
    out_dir = RECORDINGS_DIR / f"live-{run_date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        _build_eval_stores(Path(tmp))
        live_settings = settings.model_copy(
            update={
                "facts_db_path": str(Path(tmp) / "facts.db"),
                "policy_db_path": str(Path(tmp) / "policy.db"),
            }
        )
        graph = build_surveillance_graph(live_settings)
        rows = [_run_scenario(graph, scenario, out_dir) for scenario in SCENARIOS]

    scored = [r for r in rows if r.get("reward") is not None]
    summary = {
        "run_date": run_date,
        "n": len(rows),
        "n_failed_to_run": len(rows) - len(scored),
        "label_source": "canonical scenarios in data/scenarios.py, designed with their labels",
        "scorer": "live model, scored with evals.rl_env.compute_reward; not gated",
        "models": sorted({m for r in scored for m in r["models"]}),
        "disposition_accuracy": sum(1 for r in scored if r["correct"]) / len(rows),
        "reward_mean": sum(r["reward"] for r in scored) / len(rows),
        "outcome_only_mean": (
            sum(r["outcome_only"] for r in scored if r["outcome_only"] is not None) / len(rows)
        ),
        "total_cost_usd": round(sum(r["cost_usd"] for r in scored), 4),
        "mean_latency_seconds": round(
            sum(r["latency_seconds"] for r in scored) / max(1, len(scored)), 2
        ),
        "uncertainty": "none computed; n=10 supports no precision claim",
        "per_scenario": rows,
    }
    path = out_dir / "summary.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    return path


def main() -> int:
    path = run_live()
    summary = json.loads(path.read_text())
    print(f"n={summary['n']} models={summary['models']} cost=${summary['total_cost_usd']}")
    print(
        f"accuracy={summary['disposition_accuracy']:.0%} "
        f"reward_mean={summary['reward_mean']:.3f} "
        f"outcome_only_mean={summary['outcome_only_mean']:.3f}"
    )
    for row in summary["per_scenario"]:
        print(
            f"{row['scenario_id']:38} expected={row['expected']:9} "
            f"got={row.get('submitted', row.get('error', '?'))!s:9} reward={row['reward']}"
        )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
