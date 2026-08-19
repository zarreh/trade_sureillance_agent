# D-A2-3: No vector store

**Status:** Accepted, implemented (`store/policy_store.py`, `tools/get_compliance_rules.py`).

## Context

The portfolio-wide toolchain standard favors a vector store (Qdrant) for
retrieval. This project's evidence, though, is not unstructured text to
search semantically — it is a small, exact table of role limits,
compliance-rule thresholds, and a corporate-events calendar. There is no
genuine retrieval problem: every query the agent needs ("what's the
single-trade limit for this role", "which rules apply", "is this date in a
blackout window") has one exact, correct answer in SQL, not a ranked list of
approximately-relevant passages.

## Decision

Compliance rules, role limits, and material events live in SQLite
(`policy.db`, `data/generate_compliance_db.py`), queried by exact key
through typed tool functions (`get_applicable_role_limits`,
`get_compliance_rules`, `get_material_events`). No embeddings, no similarity
search, no vector database anywhere in this repo.

## Consequences

- A rule citation (`rule_id`) is always exact and traceable to a specific
  row, never an approximate match that might retrieve the wrong rule.
- No embedding-model dependency, no reindexing pipeline, no
  vector-store infrastructure to run, monitor, or pay for.
- This is a deliberate exception to the portfolio-wide "Qdrant everywhere"
  toolchain default (`PORTFOLIO_PLAN_V3.md` §9) — the default is for apps
  with a genuine unstructured-retrieval problem, and stating the exception
  explicitly is more useful than following the default reflexively.
