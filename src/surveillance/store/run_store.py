"""Read-write repository over runs.db — the operational record of every
investigation, persisted so a run is replayable from the store at any time,
during execution or long after it finished (docs/PLAN.md §7 Phase 5).

Unlike FactStore/PolicyStore, this store creates its own schema on first use:
it holds operational state, not build-time data.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from surveillance.store.models import CostEntry, RunEvent, RunRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    accession_number TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finding_kind TEXT,
    finding_json TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS run_events (
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    node TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (run_id, sequence)
);
CREATE TABLE IF NOT EXISTS run_costs (
    run_id TEXT NOT NULL,
    node TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _run_from_row(row: tuple[object, ...]) -> RunRecord:
    return RunRecord(
        id=row[0],  # type: ignore[arg-type]
        accession_number=row[1],  # type: ignore[arg-type]
        status=row[2],  # type: ignore[arg-type]
        created_at=row[3],  # type: ignore[arg-type]
        updated_at=row[4],  # type: ignore[arg-type]
        finding_kind=row[5],  # type: ignore[arg-type]
        finding_json=row[6],  # type: ignore[arg-type]
        error=row[7],  # type: ignore[arg-type]
    )


class RunStore:
    """Persists investigation runs, their node-by-node events, and per-node
    LLM cost — the single source of truth `GET /investigations/{id}` and
    `GET /investigations/{id}/events` read from."""

    def __init__(self, db_path: Path) -> None:
        # check_same_thread=False: FastAPI runs sync-ish request handling and
        # the background run executor from different tasks/threads.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def create_run(self, run_id: str, accession_number: str) -> None:
        now = _now()
        self._conn.execute(
            "INSERT INTO runs (id, accession_number, status, created_at, updated_at) "
            "VALUES (?, ?, 'running', ?, ?)",
            (run_id, accession_number, now, now),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> RunRecord | None:
        row = self._conn.execute(
            "SELECT id, accession_number, status, created_at, updated_at, "
            "finding_kind, finding_json, error FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        return _run_from_row(row) if row else None

    def complete_run(self, run_id: str, finding_kind: str, finding_json: str) -> None:
        self._conn.execute(
            "UPDATE runs SET status = 'completed', updated_at = ?, "
            "finding_kind = ?, finding_json = ? WHERE id = ?",
            (_now(), finding_kind, finding_json, run_id),
        )
        self._conn.commit()

    def fail_run(self, run_id: str, error: str) -> None:
        self._conn.execute(
            "UPDATE runs SET status = 'failed', updated_at = ?, error = ? WHERE id = ?",
            (_now(), error, run_id),
        )
        self._conn.commit()

    def append_event(self, run_id: str, sequence: int, node: str, payload_json: str) -> None:
        self._conn.execute(
            "INSERT INTO run_events (run_id, sequence, node, payload_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, sequence, node, payload_json, _now()),
        )
        self._conn.commit()

    def get_events(self, run_id: str, after_sequence: int = -1) -> list[RunEvent]:
        """Every event with `sequence > after_sequence`, in order — the same
        call replays a whole run from the start (default) or tails new events
        since the last one a client already saw."""
        rows = self._conn.execute(
            "SELECT run_id, sequence, node, payload_json, created_at FROM run_events "
            "WHERE run_id = ? AND sequence > ? ORDER BY sequence",
            (run_id, after_sequence),
        ).fetchall()
        return [RunEvent(*row) for row in rows]

    def record_costs(self, run_id: str, entries: list[CostEntry]) -> None:
        self._conn.executemany(
            "INSERT INTO run_costs "
            "(run_id, node, model, prompt_tokens, completion_tokens, cost_usd) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (run_id, e.node, e.model, e.prompt_tokens, e.completion_tokens, e.cost_usd)
                for e in entries
            ],
        )
        self._conn.commit()

    def get_costs(self, run_id: str) -> list[CostEntry]:
        rows = self._conn.execute(
            "SELECT node, model, prompt_tokens, completion_tokens, cost_usd "
            "FROM run_costs WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return [CostEntry(*row) for row in rows]
