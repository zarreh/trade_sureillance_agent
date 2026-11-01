# D-A2-13: The analyst decision is record-only

**Status:** Accepted, implemented in `store/run_store.py`
(`analyst_decisions`) and `PUT /cases/{accession}/decision`.

## Context

The case queue (D-A2-12) shows an AI suggestion. An analyst needs to accept it or
override it with a note, and that record has to stay trustworthy when the same
filing is investigated again.

## Decision

- One decision per accession, stored with the **run id it was made on**. A new
  decision replaces the last.
- `PUT` requires `run_id`. The run must belong to the accession (422) and must be
  completed (409). `override` requires a disposition; `accept` must not have one.
- A decision is **stale** only when a newer *completed* run exists. A newer run
  that is still running or failed leaves it current.
- **Record-only.** The decision never changes the run's finding (D-A2-1 still
  holds), never routes the graph, and never feeds the evaluations or the reward.

## Rejected alternatives

- **Write the override into the finding.** That would break "published ==
  judged draft" and erase what the AI actually said.
- **Use decisions as labels now.** Analyst overrides are the natural
  human-in-the-loop path to more labelled cases, and later to training data, but
  mixing them into the canonical set would contaminate a gate whose labels are
  designed. Exporting them is a separate, later step.

## Consequences

- There is no audit history of earlier decisions on the same accession, only
  the latest. If that matters, the table becomes append-only.
- There is no authentication, so a decision has no author. This is a prototype
  behind basic auth (`docs/deploy.md`), not a system of record.
