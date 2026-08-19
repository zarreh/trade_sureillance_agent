from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from data.build_store import build_facts_db
from data.generate_compliance_db import build_policy_db
from surveillance.api.deps import get_run_store, get_surveillance_graph
from surveillance.api.main import app
from surveillance.store.fact_store import FactStore
from surveillance.store.policy_store import PolicyStore
from surveillance.store.run_store import RunStore
from surveillance.tools.registry import build_tools
from tests.graph.test_surveillance_graph_integration import (
    TARGET_ACCESSION,
    _build_test_graph,
    _FakeInvestigator,
)

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "edgar_sample"


def test_skeleton_events_stream_reaches_done() -> None:
    client = TestClient(app)
    with client.stream("GET", "/investigations/skeleton/events?message=hi") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert '"echo: hi"' in body
    assert '"__end__"' in body


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A real FastAPI app wired to the real graph nodes/tools/fixture DB, but a
    fake investigator/planner/finding-writer/grounding-judge — no live LLM or
    network call, same approach as tests/graph/test_surveillance_graph_integration.py.
    """
    facts_path = tmp_path / "facts.db"
    policy_path = tmp_path / "policy.db"
    build_facts_db(FIXTURE_DIR, facts_path)
    build_policy_db(policy_path)
    tools = build_tools(FactStore(facts_path), PolicyStore(policy_path))
    fake_graph = _build_test_graph(tools, _FakeInvestigator())
    fake_run_store = RunStore(tmp_path / "runs.db")

    app.dependency_overrides[get_surveillance_graph] = lambda: fake_graph
    app.dependency_overrides[get_run_store] = lambda: fake_run_store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_and_fetch_investigation_publishes_a_finding(client: TestClient) -> None:
    create_response = client.post("/investigations", json={"accession_number": TARGET_ACCESSION})
    assert create_response.status_code == 202
    run_id = create_response.json()["id"]

    get_response = client.get(f"/investigations/{run_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["status"] == "completed"
    assert body["finding_kind"] == "published"
    assert body["finding"]["finding_text"] == "fake finding"
    # The fake chains in this test never call a real chat model, so no LLM
    # callback fires and cost stays exactly zero — not a placeholder.
    assert body["total_cost_usd"] == 0.0
    assert body["costs"] == []


def test_investigation_events_replays_every_node(client: TestClient) -> None:
    create_response = client.post("/investigations", json={"accession_number": TARGET_ACCESSION})
    run_id = create_response.json()["id"]

    with client.stream("GET", f"/investigations/{run_id}/events") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert '"node": "plan"' in body
    assert '"node": "publish"' in body
    assert '"__end__"' in body
    assert '"status": "completed"' in body


def test_get_unknown_investigation_returns_404(client: TestClient) -> None:
    response = client.get("/investigations/does-not-exist")
    assert response.status_code == 404


def test_create_investigation_rejects_oversized_body(client: TestClient) -> None:
    huge_accession = "A" * 100_000
    response = client.post("/investigations", json={"accession_number": huge_accession})
    assert response.status_code == 413


def test_rate_limit_is_enforced_on_healthz() -> None:
    from surveillance.settings import get_settings

    client = TestClient(app)
    limit = get_settings().rate_limit_per_minute
    responses = [client.get("/healthz") for _ in range(limit + 1)]
    assert responses[-1].status_code == 429
