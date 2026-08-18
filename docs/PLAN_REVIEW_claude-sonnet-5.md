# Review of `docs/PLAN.md`

**Reviewer:** GitHub Copilot (Claude Sonnet 5)
**Reviewed:** 2026-08-18
**Scope:** `docs/PLAN.md` (A2 Trade Surveillance Agent) against `reference/PORTFOLIO_PLAN_V3.md` §7 A2 and §9 engineering standard. Repo state at review time: planning only, nothing implemented.

---

## Overall verdict

This is an unusually disciplined plan. The things that make it portfolio-worthy are already there:

- **Bugs found by actually reading the source notebook** (§3.1 dead date-parsing, double-invoke, mutated state) rather than assumed — exactly the "notebook is a problem statement" discipline the portfolio plan demands.
- **Exit criteria per phase** are concrete and testable, not vibes ("date columns have no nulls," "unsupported-claim count drops between passes").
- **Scenarios 5 and 6** (valid 10b5-1 sale, tax-withholding disposition) as goldset rows is the single best idea in the doc — it's the thing that proves the system isn't a naive flagger. Keep this front and center in the writeup.
- Consistent with `PORTFOLIO_PLAN_V3.md` §7 A2 — tiers, sequencing position, pro-tier scope all line up. No contradictions found.

Given the ask to watch for excess/fluff, here's where I'd push back.

## 1. The three-provider fallback "on every call" is the biggest over-engineering risk

`PLAN.md` §1 states this as a confirmed decision for A2 specifically — it's **not** what the rest of the portfolio does. `PORTFOLIO_PLAN_V3.md` §9's toolchain table only specifies `gpt-4o-mini`/`gpt-4o` + Ollama for A3-offline/A11; it doesn't mandate Gemini fallback everywhere. So this looks like scope A2 picked up on its own, and it's expensive:

- Every node needs `with_structured_output` bound **per model before** fallback composition (the gotcha already flagged in D-A2-4) — that's 3x the structured-output surface to get right across 6+ nodes.
- Phase 3's exit criterion blocks on "cross-provider structured-output tests pass; forced-failure fallback test passes" for *all* of them before Phase 4 can start. On an app already flagged as carrying template risk, that's the most plausible place the schedule actually breaks.
- Risk 4 in §9 names this itself ("three-provider fallback multiplies structured-output failure modes") but the mitigation is "add more cross-provider tests" — that's treating the symptom, not reducing the surface.

**Suggestion:** scope v1 to OpenAI → one fallback (pick Gemini or Ollama, not both), fully tested, and record the third leg as a `pro`/stretch addition once the pattern is proven. If the point is to *demonstrate* graceful degradation as a portfolio artifact, one working fallback with a forced-failure test proves the pattern just as well as three, at a third of the surface.

## 2. MCP export in Phase 2 — check it's pulling its weight, but don't cut it

Initially this looks like optional fluff for an app where MCP isn't the headline (§7 says "only A9 makes MCP the headline"). But `PORTFOLIO_PLAN_V3.md` §8 says X2 is extracted "after A6 **and A2**" — so A2 is explicitly one of the two apps that hardens the MCP-export convention going into X2. That justifies keeping it, but keep it minimal: wire the 5 tools through FastMCP and prove one client call works. Don't build an MCP demo UI or client-side showcase for A2 — that belongs to A9.

## 3. Eight ADRs vs. the portfolio's own "3–6 ADRs per repo" guideline (§9)

Minor, but worth a pass before Phase 9: D-A2-5 (synthetic policy) and D-A2-8 (unknown 10b5-1 treated as not-established) could merge into one, and D-A2-6 (template shakedown) is really a portfolio-level decision, not an A2 architectural one — it could live in the portfolio doc instead of this repo's ADR folder. Not a big deal, just tightening.

## 4. Dual observability (LangSmith + Langfuse) + Postgres checkpointer + structlog + slowapi, all in Phase 5

This is fully justified by the portfolio-wide standard (X1 needs Langfuse traces from every app) and A2 is positioned 6th in the build sequence so X1 already exists — not excessive, just flagging that Phase 5 is doing a lot in one phase. If it slips, it's a safe place to timebox rather than a place to cut scope, since the grounding loop (the actual differentiator) is already done by Phase 4.

## What I would *not* trim

- The 5-tool ReAct + plan-validator + grounding-judge graph shape — that's the actual thesis of the app, don't simplify it.
- Two quarters of real EDGAR data — genuinely required for the 90/180-day windows to mean anything, not gold-plating.
- `regulatory_basis.md` external review (§6 Phase 9 risk) — keep this, but if there's no compliance contact lined up, soften the plan to "reviewed against primary sources + prominent disclaimer" so it isn't a blocking dependency that can't be controlled.

## Bottom line

The plan is right-sized everywhere except the tri-provider fallback commitment, which is the one place to scope down before starting Phase 3, since it's the most likely thing to eat time that should go to the grounding loop and the eval harness — the parts that actually differentiate this app on the portfolio site.
