"""Structural test: build_surveillance_graph must compile without ever
calling a live model — no network, no real API key required."""

from pathlib import Path

import pytest

from data.build_store import build_facts_db
from data.generate_compliance_db import build_policy_db
from surveillance.graph.builder import build_surveillance_graph
from surveillance.settings import Settings

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "edgar_sample"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    facts_path = tmp_path / "facts.db"
    policy_path = tmp_path / "policy.db"
    build_facts_db(FIXTURE_DIR, facts_path)
    build_policy_db(policy_path)
    return Settings(
        openai_api_key="sk-test-placeholder-not-a-real-key",
        facts_db_path=str(facts_path),
        policy_db_path=str(policy_path),
    )


def test_surveillance_graph_compiles(settings: Settings) -> None:
    graph = build_surveillance_graph(settings)
    node_names = set(graph.get_graph().nodes)
    assert {
        "plan",
        "check_plan",
        "replan",
        "investigate",
        "tools",
        "draft_finding",
        "budget_exceeded",
    } <= node_names
