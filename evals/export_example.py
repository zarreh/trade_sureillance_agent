"""Writes the recorded example run the home page shows on first paint.

The run is canonical scenario 1 through the real graph with the scripted
stand-in chains (evals/oracle.py), so it costs nothing to display and is
deterministic. The UI labels it as a stand-in, never as a live model result.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from data.scenarios import SCENARIOS
from evals.canonical import _build_eval_stores, _build_scenario_graph
from surveillance.graph.state import create_initial_state
from surveillance.schemas.finding import PublishedFinding
from surveillance.tools.registry import build_tools

EXAMPLE_PATH = Path(__file__).parent.parent / "frontend" / "src" / "generated" / "example-run.json"


def build_example() -> dict[str, Any]:
    scenario = SCENARIOS[0]
    with tempfile.TemporaryDirectory() as tmp:
        fact_store, policy_store = _build_eval_stores(Path(tmp))
        graph = _build_scenario_graph(
            build_tools(fact_store, policy_store), scenario.accession_number
        )
        nodes: list[str] = []
        published: PublishedFinding | None = None
        for update in graph.stream(
            create_initial_state(scenario.accession_number),
            stream_mode="updates",
            config={"recursion_limit": 100},
        ):
            for node, payload in update.items():
                nodes.append(node)
                if node == "publish":
                    published = payload["published_finding"]
    assert published is not None
    return {
        "accession_number": scenario.accession_number,
        "scorer": "scripted stand-in (evals/oracle.py); no live model",
        "events": [{"node": node} for node in nodes],
        "finding": published.model_dump(mode="json"),
    }


def main() -> int:
    EXAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXAMPLE_PATH.write_text(json.dumps(build_example(), indent=2) + "\n")
    print(f"wrote {EXAMPLE_PATH.relative_to(EXAMPLE_PATH.parents[3])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
