"""Read-write repository over runs.db — the operational record of every
investigation, persisted so a run is replayable from the store at any time,
during execution or long after it finished (docs/PLAN.md §7 Phase 5).

Unlike FactStore/PolicyStore, this store creates its own schema on first use:
it holds operational state, not build-time data.
"""

from __future__ import annotations

from pathlib import Path

from zarreh_agentkit.runs import RunEventLog, utc_now

from surveillance.store.models import AnalystDecision, RunRecord

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
CREATE INDEX IF NOT EXISTS runs_by_accession ON runs (accession_number, created_at);
CREATE TABLE IF NOT EXISTS analyst_decisions (
    accession_number TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs (id),
    decision TEXT NOT NULL CHECK (decision IN ('accept', 'override')),
    override_disposition TEXT CHECK (override_disposition IN ('clear', 'flag', 'escalate')),
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
"""

_RUN_COLUMNS = (
    "id, accession_number, status, created_at, updated_at, finding_kind, finding_json, error"
)


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
            f"SELECT {_RUN_COLUMNS} FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        return _run_from_row(row) if row else None

    def list_runs(self, accession_number: str) -> list[RunRecord]:
        """Every run for one accession, newest first."""
        rows = self._conn.execute(
            f"SELECT {_RUN_COLUMNS} FROM runs WHERE accession_number = ? "
            "ORDER BY created_at DESC, rowid DESC",
            (accession_number,),
        ).fetchall()
        return [_run_from_row(r) for r in rows]

    def investigated_accessions(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT accession_number FROM runs GROUP BY accession_number "
            "ORDER BY MAX(created_at) DESC"
        ).fetchall()
        return [r[0] for r in rows]

    def get_decision(self, accession_number: str) -> AnalystDecision | None:
        row = self._conn.execute(
            "SELECT accession_number, run_id, decision, override_disposition, note, updated_at "
            "FROM analyst_decisions WHERE accession_number = ?",
            (accession_number,),
        ).fetchone()
        return AnalystDecision(*row) if row else None

    def set_decision(
        self,
        accession_number: str,
        run_id: str,
        decision: str,
        override_disposition: str | None,
        note: str,
    ) -> AnalystDecision:
        """One decision per accession; a new one replaces the last. Record-only:
        the run's finding is never touched (D-A2-12)."""
        self._conn.execute(
            "INSERT INTO analyst_decisions "
            "(accession_number, run_id, decision, override_disposition, note, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (accession_number) DO UPDATE SET "
            "run_id = excluded.run_id, decision = excluded.decision, "
            "override_disposition = excluded.override_disposition, note = excluded.note, "
            "updated_at = excluded.updated_at",
            (accession_number, run_id, decision, override_disposition, note, utc_now()),
        )
        self._conn.commit()
        result = self.get_decision(accession_number)
        assert result is not None
        return result

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
