import json
import sqlite3
from pathlib import Path

from surveillance.store.policy_store import PolicyStore
from surveillance.tools.get_material_events import build_get_material_events_tool


def test_date_inside_blackout_window(policy_store: PolicyStore, tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "policy.db") as conn:
        event_date, _, _ = conn.execute(
            "SELECT event_date, blackout_start, blackout_end FROM material_events "
            "WHERE issuer_cik = '0000320193'"
        ).fetchone()
    tool = build_get_material_events_tool(policy_store)
    result = json.loads(tool.invoke({"issuer_cik": "0000320193", "on_date": event_date}))
    assert result["in_blackout"] is True
    assert result["event_type"] == "earnings"


def test_date_outside_blackout_window(policy_store: PolicyStore) -> None:
    tool = build_get_material_events_tool(policy_store)
    result = json.loads(tool.invoke({"issuer_cik": "0000320193", "on_date": "2025-08-15"}))
    # 2025-08-15 is outside every seeded quarterly blackout window (10 days
    # before, 2 after a mid-month earnings date in Jan/Apr/Jul/Oct).
    assert result["in_blackout"] is False


def test_issuer_with_no_seeded_event(policy_store: PolicyStore) -> None:
    tool = build_get_material_events_tool(policy_store)
    result = json.loads(tool.invoke({"issuer_cik": "9999999999", "on_date": "2025-07-01"}))
    assert result["in_blackout"] is False
