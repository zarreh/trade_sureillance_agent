"""Read-write repository over runs.db — the operational record of every
investigation, persisted so a run is replayable from the store at any time,
during execution or long after it finished (docs/PLAN.md §7 Phase 5).

Unlike FactStore/PolicyStore, this store creates its own schema on first use:
it holds operational state, not build-time data.
"""

from __future__ import annotations

from pathlib import Path

from zarreh_agentkit.runs import RunEventLog, utc_now

from surveillance.store.models import RunRecord

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
"""


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


class RunStore(RunEventLog):
    """Persists investigation runs, their node-by-node events, and per-node
    LLM cost — the single source of truth `GET /investigations/{id}` and
    `GET /investigations/{id}/events` read from. Events and costs come from
    `zarreh_agentkit.runs.RunEventLog`; the `runs` table is this app's own."""

    def __init__(self, db_path: Path) -> None:
        super().__init__(db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def create_run(self, run_id: str, accession_number: str) -> None:
        now = utc_now()
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
            (utc_now(), finding_kind, finding_json, run_id),
        )
        self._conn.commit()

    def fail_run(self, run_id: str, error: str) -> None:
        self._conn.execute(
            "UPDATE runs SET status = 'failed', updated_at = ?, error = ? WHERE id = ?",
            (utc_now(), error, run_id),
        )
        self._conn.commit()

    def fail_interrupted_runs(self, reason: str) -> int:
        """Runs execute in-process, so any run still `running` at startup was
        cut off by a restart and can never finish."""
        cursor = self._conn.execute(
            "UPDATE runs SET status = 'failed', updated_at = ?, error = ? WHERE status = 'running'",
            (utc_now(), reason),
        )
        self._conn.commit()
        return cursor.rowcount
