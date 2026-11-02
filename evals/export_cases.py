"""Writes the case data the frontend renders: frontend/src/generated/cases.json.

Per canonical scenario it holds two clearly separate runs:
- `reference`: the real graph with the scripted stand-in chains (evals/oracle.py),
  a rules-based answer key. Costs nothing and is deterministic. Not a model result.
- `live`: what the live model did, read from the newest evals/recordings/live-*/
  directory. Nothing here calls a model.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from langchain_core.messages import messages_from_dict
from langchain_core.tools import StructuredTool

from data.scenarios import SCENARIOS, Scenario
from evals.canonical import _build_eval_stores, _build_scenario_graph
from surveillance.graph.evidence import extract_tool_call_records
from surveillance.graph.state import create_initial_state
from surveillance.schemas.finding import PublishedFinding
from surveillance.tools.registry import build_tools

CASES_PATH = Path(__file__).parent.parent / "frontend" / "src" / "generated" / "cases.json"
RECORDINGS_DIR = Path(__file__).parent / "recordings"
REFERENCE_SCORER = "scripted stand-in (evals/oracle.py); no live model"

_ROW_KEYS = (
    "submitted",
    "correct",
    "published",
    "incomplete",
    "reward",
    "outcome_only",
    "trajectory_score",
    "tool_calls",
    "evidence_passes",
    "unsupported_claims",
    "cost_usd",
    "models",
)


def _reference_run(scenario: Scenario, tools: list[StructuredTool]) -> dict[str, Any]:
    graph = _build_scenario_graph(tools, scenario.accession_number)
    nodes: list[str] = []
    final_state: dict[str, Any] = {}
    for mode, chunk in graph.stream(
        create_initial_state(scenario.accession_number),
        stream_mode=["updates", "values"],
        config={"recursion_limit": 100},
    ):
        if mode == "updates":
            nodes.extend(chunk)
        else:
            assert isinstance(chunk, dict)
            final_state = chunk
    published = final_state["published_finding"]
    assert isinstance(published, PublishedFinding)
    evidence = extract_tool_call_records(final_state["messages"])
    # `evidence` is exported once, beside the finding, rather than twice.
    finding = published.model_dump(mode="json", exclude={"evidence"})
    return {
        "events": [{"node": node} for node in nodes],
        "finding": finding,
        "evidence": [r.model_dump(mode="json") for r in evidence],
    }


def _latest_recording_dir() -> Path | None:
    dirs = sorted(d for d in RECORDINGS_DIR.glob("live-*") if (d / "summary.json").exists())
    return dirs[-1] if dirs else None


def _live_case(recording_dir: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    transcript_path = recording_dir / f"{row['scenario_id']}.json"
    if not transcript_path.exists():
        return None  # the run errored before writing a transcript
    transcript = json.loads(transcript_path.read_text())
    finding = transcript["published_finding"] or transcript["draft_finding"]
    evidence = extract_tool_call_records(messages_from_dict(transcript["messages"]))
    return {
        **{key: row.get(key) for key in _ROW_KEYS},
        "finding_kind": "published" if transcript["published_finding"] else "draft",
        "finding": finding,
        "evidence": [r.model_dump(mode="json") for r in evidence],
    }


def build_cases() -> dict[str, Any]:
    recording_dir = _latest_recording_dir()
    summary = json.loads((recording_dir / "summary.json").read_text()) if recording_dir else None
    rows = {r["scenario_id"]: r for r in summary["per_scenario"]} if summary else {}

    with tempfile.TemporaryDirectory() as tmp:
        fact_store, policy_store = _build_eval_stores(Path(tmp))
        tools = build_tools(fact_store, policy_store)
        cases = []
        for scenario in SCENARIOS:
            row = rows.get(scenario.id)
            cases.append(
                {
                    "id": scenario.id,
                    "name": scenario.name,
                    "expected_disposition": scenario.expected_disposition,
                    "accession_number": scenario.accession_number,
                    "reference": _reference_run(scenario, tools),
                    "live": _live_case(recording_dir, row) if recording_dir and row else None,
                }
            )

    return {
        "reference_scorer": REFERENCE_SCORER,
        "live_run": (
            {
                "run_date": summary["run_date"],
                "n": summary["n"],
                "models": summary["models"],
                "disposition_accuracy": summary["disposition_accuracy"],
                "total_cost_usd": summary["total_cost_usd"],
                "scorer": summary["scorer"],
                "uncertainty": summary["uncertainty"],
            }
            if summary
            else None
        ),
        "cases": cases,
    }


def main() -> int:
    CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CASES_PATH.write_text(json.dumps(build_cases(), indent=2) + "\n")
    print(f"wrote {CASES_PATH.relative_to(CASES_PATH.parents[3])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
