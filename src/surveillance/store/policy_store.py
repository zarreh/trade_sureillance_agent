"""Read-only repository over policy.db — the synthetic firm-policy database
built by data/generate_compliance_db.py (docs/PLAN.md §4.1, Appendix A).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from surveillance.store.models import ComplianceRule, MaterialEvent, RoleLimit

_DEFAULT_ROLE_LIMIT_KEY = ("Default", "Standard")


class PolicyStore:
    """Read-only access to role limits, compliance rules, and material events."""

    def __init__(self, db_path: Path) -> None:
        self._conn = sqlite3.connect(db_path)

    def close(self) -> None:
        self._conn.close()

    def get_role_limit(self, relationship: str, title: str | None = None) -> RoleLimit:
        """Resolves the applicable role limit. Title refines via the alias table;
        relationship alone is authoritative when no alias matches (docs/PLAN.md §3.4:
        this selects an *applicable* limit, it does not assert authorization)."""
        if title:
            alias = self._conn.execute(
                "SELECT relationship, authorization_level FROM title_aliases WHERE title = ?",
                (title,),
            ).fetchone()
            if alias:
                row = self._conn.execute(
                    "SELECT * FROM role_limits WHERE relationship = ? AND authorization_level = ?",
                    alias,
                ).fetchone()
                if row:
                    return RoleLimit(*row)

        for relationship_part in relationship.split(","):
            row = self._conn.execute(
                "SELECT * FROM role_limits WHERE relationship = ? "
                "ORDER BY single_trade_limit ASC LIMIT 1",
                (relationship_part.strip(),),
            ).fetchone()
            if row:
                return RoleLimit(*row)

        row = self._conn.execute(
            "SELECT * FROM role_limits WHERE relationship = ? AND authorization_level = ?",
            _DEFAULT_ROLE_LIMIT_KEY,
        ).fetchone()
        return RoleLimit(*row)

    def get_compliance_rules(self) -> list[ComplianceRule]:
        rows = self._conn.execute(
            "SELECT rule_id, rule_name, threshold_value, rule_type, severity "
            "FROM compliance_rules ORDER BY severity DESC"
        ).fetchall()
        return [ComplianceRule(*r) for r in rows]

    def get_material_event_for_date(self, issuer_cik: str, on_date: str) -> MaterialEvent | None:
        """Returns the material event whose blackout window contains `on_date`, if any."""
        row = self._conn.execute(
            """
            SELECT issuer_cik, event_type, event_date, blackout_start, blackout_end
            FROM material_events
            WHERE issuer_cik = ? AND blackout_start <= ? AND blackout_end >= ?
            """,
            (issuer_cik, on_date, on_date),
        ).fetchone()
        return MaterialEvent(*row) if row else None
