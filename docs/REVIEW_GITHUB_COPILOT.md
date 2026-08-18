# Trade Surveillance Agent Plan Review

**Reviewer:** GitHub Copilot  
**Review date:** 2026-08-18  
**Documents reviewed:** `docs/PLAN.md` and `reference/PORTFOLIO_PLAN_V3.md`

## Verdict

**Approve with revisions.** The project is portfolio-worthy, and its domain
analysis is substantially stronger than a typical agent demonstration. The
notebook defect inventory, transaction-code awareness, parameterized SQL,
explicit exculpatory factors, SQL-over-vector-store decision, and grounding
loop are all valuable engineering signals.

The current plan nevertheless attempts to prove too many secondary capabilities
at once. It combines a regulated-domain application with a new repository
template, shared frontend and Python package design, three-provider resilience,
dual observability, MCP, two persistence technologies, deployment automation,
and a `pro` product tier. That breadth risks obscuring the best portfolio claim:
the system issues a finding only when its evidence supports it, and it measures
that behavior honestly.

## Findings

### 1. Critical: the final output can bypass grounding

The graph validates claims and then calls `finalizer`, while the model policy
identifies `finding_writer` as another reasoning-model chain. That writer can
introduce unsupported claims after the grounding check has passed.

The model-generated `ComplianceFinding` should be the artifact passed through
`extract_claims -> judge_grounding`. If it passes, publish that exact immutable
finding. Alternatively, make `finalizer` deterministic and restrict it to
assembling already-approved claims, citations, and evidence.

### 2. High: the earnings-announcement scenarios lack an evidence source

The inventoried data contains filings, owners, and transactions, but scenarios
1 and 5 depend on the date of an earnings announcement. None of the five tools
can establish that event, so the agent would have to infer or invent it.

Either add a seeded `material_events` table and deterministic lookup tool, or
remove the pre-earnings scenarios from `base`. A live market-data integration is
not justified merely to preserve one scenario.

### 3. High: `AFF10B5ONE` does not establish plan validity

The filing indicator can show that a transaction was reported as occurring
under a Rule 10b5-1 plan. It does not by itself prove that the plan satisfies
every condition of the affirmative defense.

Represent this as `reported_under_10b5_1: true | false | unknown`, not as a
verified valid plan. Treat it as an exculpatory factor that can reduce severity.
A `verified_valid_plan` conclusion should require explicit synthetic firm-side
evidence. Similarly, an `F` transaction may be exempted individually, but it
must not clear unrelated transactions in the same accession.

### 4. High: relationship and title do not prove authorization

`RPTOWNER_RELATIONSHIP` and title can select an applicable synthetic role limit;
they cannot establish that a trade was authorized or pre-cleared.

Rename `get_insider_authorization` to `get_applicable_role_limits`. Reserve
`authorized`, `pre-cleared`, and equivalent findings for an explicit synthetic
approvals table.

### 5. High: eight scenarios cannot support a published precision claim

The eight canonical scenarios form a useful regression suite, but they are too
small to substantiate a public precision number. A single error would move flag
precision dramatically, and live LLM results may fluctuate between runs.

Use two evaluation layers:

1. Keep the eight canonical scenarios as deterministic smoke and regression
   cases.
2. Use a larger, human-reviewed, stratified set for published metrics, including
   the sample count and confidence intervals.

Pull-request CI should use mocked or recorded model behavior. Live-model
evaluation should be pinned to explicit model versions and run on a schedule or
through a manual workflow rather than gate every commit.

### 6. High: the project and portfolio plans disagree on sequencing

The project plan says A2 is first and will create the template and X2/X3
patterns. The portfolio plan schedules A2 sixth, after A6, A3, and X1/X2/X3,
and separately says A6 builds the UI kit while A2 consumes it.

Choose one source of truth before implementation. If A2 is now first, amend the
portfolio plan and keep shared-looking components local. Do not extract a shared
package from a single implementation.

### 7. Medium: the plan-validation loop is likely unnecessary complexity

The investigation has five known tools and a mostly fixed set of required
checks. An LLM planner, an LLM critic, and up to three replans can consume
several calls before evidence collection begins.

The grounding rejection loop is A2's genuine differentiator and should remain.
For `base`, use either a deterministic investigation checklist or one planner
followed by deterministic validation that mandatory checks are present. Add an
LLM replanner only if evaluation demonstrates a measurable benefit.

### 8. Medium: three-provider fallback creates a large behavioral matrix

OpenAI to Gemini to Ollama fallback across tool calling and structured output
multiplies tests and can silently change behavior. Broad exception-based
fallback may also hide a prompt or schema defect by switching models.

Start with one primary provider and one optional provider profile. Treat Ollama
as an explicit offline mode rather than an automatic final fallback. If runtime
fallback remains, limit it to defined availability failures; schema-validation
failures should stay visible. Run cross-provider contract tests outside normal
pull-request CI.

### 9. Medium: temporal and amendment rules need exact acceptance criteria

Two quarterly packages do not guarantee 180 days of prior history for every
transaction in the target quarter. Fetch the target quarter plus the preceding
two quarters. Also define and test:

- Whether quarterly volume means a calendar quarter or a rolling 90-day window.
- The deterministic identity used to supersede a `4` with a `4/A`.
- How changed and removed amendment rows affect aggregates.
- The holiday calendar used for business-day lateness.
- Whether malformed required dates fail the build or enter a rejected-row report.

### 10. Medium: `base` includes much of `pro` and the shared platform

Phase 0 deploys an intentionally disposable echo graph. Later base phases add
Postgres, two tracing systems, batch processing, replay persistence, MCP, and
three-provider fallback, while batch triage and replay are described again as
`pro` capabilities.

Defer MCP, batch triage, public replay, package extraction, automatic provider
fallback, and one of the two observability systems. SQLite is sufficient for an
initial single-instance public demo unless measured concurrency requirements
show otherwise. Separate CI from CD so ordinary pull requests do not push images
or deploy.

## Recommended Base Scope

Keep the following in the first deployed release:

- Typed EDGAR ingestion with explicit date, amendment, and lookback rules.
- Deterministic parameterized-SQL tools with row caps and fixture tests.
- One model provider and structured Pydantic outputs.
- A deterministic investigation checklist or one planner.
- A grounding rejection loop applied to the actual final finding.
- FastAPI, SSE, rate limiting, correlation IDs, and a persisted example.
- A focused Next.js UI with run console, timeline, evidence, and validator state.
- Ruff, strict typing, pytest, one Playwright smoke test, Docker, and CI.
- Eight canonical regression cases plus an honestly labelled larger evaluation.
- Regulatory basis, a prototype disclaimer, and only consequential ADRs.

Defer `pro`, MCP, three-provider fallback, dual observability, Postgres, shared
package extraction, batch triage, and replay UI until the deployed base is
credible.

## Quality Gate

The base tier is ready to publish when all of the following are true:

1. Required dates parse without silent coercion, amendment behavior is covered
   by fixtures, and the historical window is demonstrably complete.
2. Every tool passes without a network or LLM dependency and returns typed,
   capped results.
3. An under-evidenced finding receives actionable grounding feedback, obtains
   missing evidence on the next pass, and terminates at the configured cap.
4. The exact finding shown to the user is the exact finding that passed the
   grounding judge.
5. Canonical cases for a reported 10b5-1 transaction and an isolated `F`
   transaction do not produce naive alerts.
6. Reported evaluation metrics state the dataset size, label source, model
   version, and run conditions.
7. The deployed API enforces input limits and rate limits, and the frontend has
   tested loading, success, empty, and error states.

The plan should optimize for one clear portfolio argument: **deterministic facts
constrain the investigation, every published claim links to evidence, and the
system reports the limits of its own evaluation.**