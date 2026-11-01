# D-A2-12: A case-review queue ships before the `pro` gate

**Status:** Accepted, implemented in `api/routes/cases.py`,
`store/run_store.py` and `frontend/src/app/queue/`.

## Context

`docs/PLAN.md` §7 Stretch puts an "alert triage queue" in the `pro` tier, gated
on a public deployment and on published Layer 2 metrics. Neither exists yet.
Without a queue, though, the product has no analyst workflow: a run is a page you
reach by URL, there is no list of what has been investigated, and nowhere to
record what a human concluded.

## Decision

Build a narrow **case-review queue** now, and keep the triage queue gated.

- The queue lists the ten labelled scenarios plus every accession that has been
  investigated. It does not batch-score a filing day, rank by severity, or
  pull from the full EDGAR load.
- Each row shows the latest run's AI suggestion (disposition, severity) and its
  process-audit score, plus the analyst decision (D-A2-13). Confidence, cost and
  the grounding detail stay on the run page.
- Scenarios are found by their `SCENARIO-` accession prefix in `facts.db`; their
  expected labels stay in `data/scenarios.py` and never reach the API.
- Re-running an accession reuses `POST /investigations`.

## Rejected alternatives

- **Wait for the gate.** The gate exists so a large feature doesn't distract
  from shipping base. This one is small, reuses the run store, and is what makes
  the analyst decision possible at all.
- **Full triage queue.** Batch scoring a filing day costs real model money per
  filing and needs Layer 2 numbers to say anything about precision. Still gated.

## Consequences

- `pro` tier now means batch triage, ranking, the false-positive view and the
  rest of §7 Stretch, not "any queue".
- The queue holds only ten rows until real filings are investigated. Arbitrary
  accessions are still started from "Investigate a filing".
