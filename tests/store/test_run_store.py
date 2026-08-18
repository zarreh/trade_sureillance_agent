from pathlib import Path

from surveillance.store.models import CostEntry
from surveillance.store.run_store import RunStore


def test_create_and_get_run(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    store.create_run("run-1", "0000000001-25-000001")

    run = store.get_run("run-1")
    assert run is not None
    assert run.accession_number == "0000000001-25-000001"
    assert run.status == "running"
    assert run.finding_json is None


def test_get_run_returns_none_for_unknown_id(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    assert store.get_run("does-not-exist") is None


def test_complete_run_records_finding(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    store.create_run("run-1", "0000000001-25-000001")
    store.complete_run("run-1", finding_kind="published", finding_json='{"disposition": "clear"}')

    run = store.get_run("run-1")
    assert run is not None
    assert run.status == "completed"
    assert run.finding_kind == "published"
    assert run.finding_json == '{"disposition": "clear"}'


def test_fail_run_records_error(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    store.create_run("run-1", "0000000001-25-000001")
    store.fail_run("run-1", "boom")

    run = store.get_run("run-1")
    assert run is not None
    assert run.status == "failed"
    assert run.error == "boom"


def test_events_are_ordered_and_after_sequence_tails_new_ones(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    store.create_run("run-1", "0000000001-25-000001")
    store.append_event("run-1", 0, "plan", '{"plan": "x"}')
    store.append_event("run-1", 1, "check_plan", '{"plan_check": "ok"}')

    all_events = store.get_events("run-1")
    assert [e.node for e in all_events] == ["plan", "check_plan"]

    new_events = store.get_events("run-1", after_sequence=0)
    assert [e.node for e in new_events] == ["check_plan"]


def test_record_and_get_costs(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    store.create_run("run-1", "0000000001-25-000001")
    entries = [
        CostEntry(
            node="plan",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=20,
            cost_usd=0.001,
        ),
        CostEntry(
            node="draft_finding",
            model="gpt-4o",
            prompt_tokens=500,
            completion_tokens=200,
            cost_usd=0.003,
        ),
    ]
    store.record_costs("run-1", entries)

    costs = store.get_costs("run-1")
    assert len(costs) == 2
    assert {c.node for c in costs} == {"plan", "draft_finding"}
