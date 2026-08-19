# D-A2-2: Plan once, validate in code

**Status:** Accepted, implemented (`graph/nodes/{plan,check_plan,replan}.py`, Phase 3).

## Context

The investigation has a small, mostly-fixed set of six tools and a known
checklist of mandatory evidence (transaction details first, then role
limits, compliance rules, rolling volume, baseline, material events). An
LLM planner plus an LLM critic plus several replan attempts burns multiple
model calls validating something a plain function can check exactly:
whether a plan references real tools, in the right order, covering the
required checks.

## Decision

`plan` is exactly one LLM call. `check_plan` is deterministic code — it
verifies the plan calls `get_transaction_details` first and covers every
tool in `MANDATORY_TOOLS`, producing a `PlanCheck(ok, missing_checks,
unknown_tools, ordering_issues)` that is never model-authored. `replan` is
capped at one attempt (`MAX_REPLANS = 1`, `graph/edges.py`); if the plan is
still imperfect after that, the graph proceeds to `investigate` anyway with
the remaining issues visible in `plan_check`, rather than deadlocking.

The same "don't spend a model call on a decision an `if` can make" argument
recurs twice more in this codebase: `graph/evidence.py`'s exculpatory-factor
derivation and `graph/judge_grounding.py`'s `unsupported`/`confidence`
aggregation are both deterministic for the same reason.

## Consequences

- One planning LLM call per investigation instead of the several a
  planner-plus-critic-plus-retries design would need.
- `check_plan`'s correctness is testable exactly, with plain unit tests
  (`tests/graph/test_check_plan.py`) — no flakiness from a second model's
  judgement of the first model's plan.
- The replan cap means a persistently bad plan is *visible* (in
  `plan_check`) rather than silently retried forever or blocking the run.
