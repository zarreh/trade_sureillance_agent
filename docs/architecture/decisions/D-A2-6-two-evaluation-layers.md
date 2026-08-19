# D-A2-6: Two evaluation layers

**Status:** Accepted. Layer 1 implemented (`evals/`, Phase 7). Layer 2
designed, not populated — see [Evaluation](../../evidence/evaluation.md).

## Context

Ten hand-designed scenarios are enough to smoke-test behavior, but not
enough to publish a precision or recall figure — one wrong case would move
such a number by ten points, and live model output varies run to run.
Conflating "does the mechanism work" with "how good is it in general" is
exactly the kind of unlabelled claim this project exists to argue against.

## Decision

Two layers, never conflated:

- **Layer 1 — canonical regression set** (`data/scenarios.py`, n=10).
  Deterministic, fast, gates every pull request (`make eval`,
  `.github/workflows/ci.yml`). These are smoke tests for behavior, not a
  measurement — the metrics they produce (`evals/metrics.py`) are reported
  with `n=10` and a clear "canonical, not stratified" label everywhere they
  appear (`docs/evidence/evaluation.md`).
- **Layer 2 — stratified evaluation set** (150–300 cases, sampled across
  transaction code, relationship, value decile, 10b5-1 status, and
  amendment status; hand-labelled; run against pinned model versions on a
  schedule or manual trigger). Every number this layer produces states
  sample size, label source, model version, run date, and a confidence
  interval.

`evals/metrics.py`'s `compute_metrics()` is shared by both layers, so
neither layer re-derives a metric definition ad hoc.

## Consequences

- Layer 1 catches a real regression class immediately and cheaply (it found
  two scenario-authoring bugs during Phase 7 — see
  [Evaluation](../../evidence/evaluation.md)) without needing a live model
  or human labelling effort.
- Layer 2 does not exist yet in this environment: no live LLM API key and no
  human labelling effort were available in this build. Rather than fabricate
  a placeholder precision number, `docs/evidence/evaluation.md` states this
  plainly. The harness (`evals/metrics.py`) is ready for it.
- No number appears anywhere in this project's docs without stating what it
  is based on.
