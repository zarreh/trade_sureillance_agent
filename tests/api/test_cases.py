from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from data.build_store import build_facts_db
from data.generate_compliance_db import build_policy_db
from data.scenarios import SCENARIOS, inject_scenarios_into
from surveillance.api.deps import get_fact_store, get_run_store, get_surveillance_graph
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


@pytest.fixture
def run_store(tmp_path: Path) -> RunStore:
    return RunStore(tmp_path / "runs.db")


@pytest.fixture
def client(tmp_path: Path, run_store: RunStore) -> Iterator[TestClient]:
    facts_path = tmp_path / "facts.db"
    policy_path = tmp_path / "policy.db"
    build_facts_db(FIXTURE_DIR, facts_path)
    inject_scenarios_into(facts_path)
    build_policy_db(policy_path)
    tools = build_tools(FactStore(facts_path), PolicyStore(policy_path))
    fake_graph = _build_test_graph(tools, _FakeInvestigator())

    app.dependency_overrides[get_surveillance_graph] = lambda: fake_graph
    app.dependency_overrides[get_run_store] = lambda: run_store
    app.dependency_overrides[get_fact_store] = lambda: FactStore(facts_path)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _investigate(client: TestClient) -> str:
    response = client.post("/investigations", json={"accession_number": TARGET_ACCESSION})
    assert response.status_code == 202
    return str(response.json()["id"])


def _case(client: TestClient, accession: str) -> dict[str, object]:
    cases = client.get("/cases").json()["cases"]
    return next(c for c in cases if c["accession_number"] == accession)


def test_lists_every_scenario_before_any_run(client: TestClient) -> None:
    body = client.get("/cases").json()
    accessions = [c["accession_number"] for c in body["cases"]]
    assert accessions == sorted({s.accession_number for s in SCENARIOS})
    first = body["cases"][0]
    assert first["is_scenario"] is True
    assert first["latest_run"] is None
    assert first["decision"] is None
    assert first["filing"]["insider_name"]


def test_never_exposes_expected_labels(client: TestClient) -> None:
    text = client.get("/cases").text
    assert "expected" not in text
    for s in SCENARIOS:
        assert s.id not in text


def test_investigated_accession_comes_first_with_its_latest_run(client: TestClient) -> None:
    run_id = _investigate(client)
    body = client.get("/cases").json()
    case = body["cases"][0]
    assert case["accession_number"] == TARGET_ACCESSION
    assert case["is_scenario"] is False
    assert case["run_count"] == 1
    run = case["latest_run"]
    assert run["id"] == run_id
    assert run["status"] == "completed"
    assert run["disposition"] in ("clear", "flag", "escalate")
    assert run["trajectory_score"] is not None
    assert run["unsupported_claims"] == 0


def test_accept_then_override_persists(client: TestClient) -> None:
    run_id = _investigate(client)
    url = f"/cases/{TARGET_ACCESSION}/decision"

    accepted = client.put(url, json={"run_id": run_id, "decision": "accept"})
    assert accepted.status_code == 200
    assert accepted.json()["decision"]["decision"] == "accept"

    overridden = client.put(
        url,
        json={
            "run_id": run_id,
            "decision": "override",
            "override_disposition": "escalate",
            "note": "  rolling volume  ",
        },
    )
    assert overridden.status_code == 200
    decision = _case(client, TARGET_ACCESSION)["decision"]
    assert isinstance(decision, dict)
    assert decision["decision"] == "override"
    assert decision["override_disposition"] == "escalate"
    assert decision["note"] == "rolling volume"
    assert decision["stale"] is False
    assert decision["run_id"] == run_id


def test_decision_goes_stale_only_after_a_newer_completed_run(
    client: TestClient, run_store: RunStore
) -> None:
    first = _investigate(client)
    client.put(f"/cases/{TARGET_ACCESSION}/decision", json={"run_id": first, "decision": "accept"})

    run_store.create_run("still-running", TARGET_ACCESSION)
    decision = _case(client, TARGET_ACCESSION)["decision"]
    assert isinstance(decision, dict)
    assert decision["stale"] is False

    _investigate(client)
    decision = _case(client, TARGET_ACCESSION)["decision"]
    assert isinstance(decision, dict)
    assert decision["stale"] is True


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "override"},
        {"decision": "accept", "override_disposition": "flag"},
        {"decision": "maybe"},
        {"decision": "accept", "note": "x" * 2001},
    ],
)
def test_rejects_invalid_bodies(client: TestClient, body: dict[str, object]) -> None:
    run_id = _investigate(client)
    response = client.put(f"/cases/{TARGET_ACCESSION}/decision", json={"run_id": run_id, **body})
    assert response.status_code == 422


def test_rejects_a_run_from_another_accession(client: TestClient) -> None:
    run_id = _investigate(client)
    other = SCENARIOS[0].accession_number
    response = client.put(f"/cases/{other}/decision", json={"run_id": run_id, "decision": "accept"})
    assert response.status_code == 422


def test_rejects_an_unfinished_run(client: TestClient, run_store: RunStore) -> None:
    run_store.create_run("running-1", TARGET_ACCESSION)
    response = client.put(
        f"/cases/{TARGET_ACCESSION}/decision", json={"run_id": "running-1", "decision": "accept"}
    )
    assert response.status_code == 409


def test_unknown_accession_is_404(client: TestClient) -> None:
    response = client.put("/cases/NOPE/decision", json={"run_id": "x", "decision": "accept"})
    assert response.status_code == 404
    assert client.get("/cases/NOPE").status_code == 404


def test_get_one_case(client: TestClient) -> None:
    run_id = _investigate(client)
    body = client.get(f"/cases/{TARGET_ACCESSION}").json()
    assert body["accession_number"] == TARGET_ACCESSION
    assert body["latest_run"]["id"] == run_id
