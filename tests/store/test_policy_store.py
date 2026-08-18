from pathlib import Path

import pytest

from data.generate_compliance_db import build_policy_db
from surveillance.store.policy_store import PolicyStore


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "policy.db"
    build_policy_db(path, issuer_ciks=["0000320193"], seed=7)
    return path


@pytest.fixture
def store(db_path: Path) -> PolicyStore:
    return PolicyStore(db_path)


def test_role_limit_resolves_by_title_alias(store: PolicyStore) -> None:
    limit = store.get_role_limit("Officer", title="Chief Financial Officer")
    assert limit.authorization_level == "Executive"
    assert limit.single_trade_limit == 10_000_000


def test_role_limit_resolves_by_relationship_when_title_unknown(store: PolicyStore) -> None:
    limit = store.get_role_limit("Director", title=None)
    assert limit.relationship == "Director"


def test_role_limit_falls_back_to_default(store: PolicyStore) -> None:
    limit = store.get_role_limit("SomeUnknownRelationship", title="Made Up Title")
    assert limit.relationship == "Default"


def test_compliance_rules_include_exemptions_and_late_filing(store: PolicyStore) -> None:
    rule_ids = {r.rule_id for r in store.get_compliance_rules()}
    assert {"R007", "R008", "R009", "R010"} <= rule_ids


def test_material_event_blackout_window(store: PolicyStore, db_path: Path) -> None:
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        events = conn.execute(
            "SELECT event_date, blackout_start, blackout_end FROM material_events"
        ).fetchall()
    assert len(events) == 1
    event_date, blackout_start, blackout_end = events[0]
    inside = store.get_material_event_for_date("0000320193", event_date)
    assert inside is not None
    outside = store.get_material_event_for_date("0000320193", "2025-02-01")
    assert outside is None
