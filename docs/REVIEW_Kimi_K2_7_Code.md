# Review: A2 — Trade Surveillance Agent · Build Plan

**Reviewer:** Kimi K2.7 Code  
**Date:** 2026-08-18  
**Source reviewed:** [docs/PLAN.md](PLAN.md)  
**Portfolio context:** [reference/PORTFOLIO_PLAN_V3.md](../reference/PORTFOLIO_PLAN_V3.md)

---

## Overall verdict

A strong, credible plan. The best parts are the explicit rejection of the source notebook's defects (§3.1), the data-first Phase 1, and the treatment of Rule 10b5-1 and transaction codes as the domain differentiator. It will read well to a technical reviewer because it shows an understanding of *why* the original implementation was broken rather than a mechanical re-implementation.

The main structural concern is that the plan asks A2 to serve **two conflicting roles**: the L-cost finance flagship *and* the portfolio template shakedown. The portfolio plan originally intended A6 LexAgent to be first precisely to separate template friction from domain friction. The Phase 0 mitigation in this plan is sensible, but as written it is already substantial infrastructure work, not a trivial preamble.

Below is what to keep, what to cut or harden, and what to add before code is written.

---

## What is genuinely worth the effort (do not trim)

1. **§3 "What must NOT be ported"** — the highest-value section. Case 1 (date parsing) is exactly the detail that separates a portfolio project from a notebook dump.
2. **10b5-1 and transaction-code-aware handling** — the right credibility moves. Scenarios 5 and 6 are the core story; protect them.
3. **Phase 1 as an LLM-free data foundation** — correct sequencing. Schema surprises should surface before any graph wiring.
4. **The grounding loop** — the architectural centerpiece and the app's reason for existing.
5. **D-A2-3 (no vector store)** — a defensible, senior decision. Keep the ADR.
6. **Typed schemas with `Claim` / `ClaimAnalysis` / `ComplianceFinding`** and first-class `exculpatory_factors` — these make the output auditable.

---

## Red flags and scope risks

### 1. Phase 0 is not a "walking skeleton" — it is most of the platform

The Phase 0 exit criteria include FastAPI, Next.js 15, Docker, CI/CD, GHCR push, Caddy, HTTPS, and a live URL ([PLAN.md §6.0](PLAN.md#L286-L303)). This is correct work, but calling it Phase 0 understates it. In practice it is probably **30–40% of the base effort**.

**Recommendation:** rename or reframe Phase 0 as the "template shakedown milestone" and give it an explicit time-box. If it slips, everything downstream slips.

### 2. Three-provider fallback per call is over-engineered for a portfolio

D-A2-4 ([PLAN.md §5.4](PLAN.md#L268-L280)) proposes OpenAI → Gemini → Ollama on every call. The tests described are good, but the live integration triples failure modes, secret management, latency, and cost.

**Recommendation:**
- Keep the abstraction in `graph/policies.py`.
- Prove OpenAI → Gemini fallback with one forced-failure test.
- Make Ollama a **local/offline mode flag**, not part of the default runtime path. Portfolio reviewers will be impressed the abstraction exists; they will not audit whether Ollama is live on every call.

### 3. Dual observability backends add infra work with diminishing returns

LangSmith + Langfuse + Postgres checkpointer + RunStore ([PLAN.md §6.5](PLAN.md#L337-L347)) is admirable, but Langfuse self-hosting is another service to keep running.

**Recommendation:** for the live demo, pick **one** backend (LangSmith is lower friction) and keep the callback abstraction so a second can be wired later. "We measured cost per node" is the portfolio signal, not "we run two trace stores."

### 4. Phase 8 should be marked as a stretch tier, not committed scope

The alert triage queue, false-positive analysis, and investigation replay ([PLAN.md §6.8](PLAN.md#L373-L380)) are essentially a second application. The plan already says cut Phase 8 first if things slide, but that is psychologically hard once it is in the timeline.

**Recommendation:** explicitly re-label Phase 8 as **"pro stretch — gated on base + evals finishing early"** and remove it from the primary timeline.

### 5. The planner → plan_validator → replanner loop may be unnecessary

For exactly five fixed tools, a learned planner is a lot of latency and structured-output surface. If the goal is to demonstrate the plan-validation pattern, keep it but consider:
- A **rule-based or template planner** that emits a deterministic first plan, with the validator only rejecting genuinely bad plans.
- Capping `replan_count` at 1 or 2 instead of 3, because each replan is another model call.

Three replans × two evidence passes × two model tiers = a lot of tokens per investigation. Add a per-run cost cap.

### 6. Frontend scope

Next.js 15 + OpenAPI-generated types + Zod + Playwright smoke tests ([PLAN.md §6.6](PLAN.md#L349-L365)) is a lot for a first app. This is fine if it is the template for all apps, but if A2 exists partly to shake down the template, this is exactly where friction will bite.

**Recommendation:** make the first paint story work first ("visitor sees a full investigation without typing"), then polish components.

---

## Things to add or harden

| Area | Suggestion |
|---|---|
| **Cost guardrail** | Add a per-investigation token/time cap in the graph. A surveillance demo that runs unbounded is a bad look. |
| **Calendar accuracy** | Section 16(a) filing lag must use a real business-day calendar (NYSE holidays), not just `np.busday_count` with default US holidays. Document the source of the holiday calendar. |
| **Scenario count** | Eight scenarios is small. Expand to ~20–30 to cover amended-filing supersession, mixed relationship roles, and edge codes (`J`, `G`, `D`). |
| **Precision/recall definition** | Define how "flag precision / recall" is computed before collecting labels. Is a `flag` prediction on an `escalate` label a false positive or a partial match? |
| **Rule 10b5-1 evidence** | The plan says unknown `AFF10B5ONE` means "not established," never "no plan" ([PLAN.md §7](PLAN.md#L410-L412)). Make sure the UI and finding text render this honestly. |
| **Pre-cleared trade** | Listed as an exculpatory factor but not defined anywhere. Either wire it to a real signal or remove it. |
| **`4/A` supersession** | The plan mentions this correctly but does not describe the mechanics. Document how `build_store.py` handles supersession in the DB layer. |

---

## Suggested phasing adjustment

| Phase | Recommendation |
|---|---|
| **0** | Keep, but rename "Template shakedown" and time-box to roughly one-third of base effort. |
| **1** | Keep as-is; the highest-leverage phase. |
| **2–4** | Keep. These are the core of the portfolio story. |
| **5** | Use SQLite/MemorySaver for base; defer Postgres to pro. |
| **6** | Build a minimal working frontend first; polish components only after base evals pass. |
| **7** | Keep; evals are what make this a portfolio project rather than a notebook. |
| **8** | Move to "stretch" and gate it explicitly. |
| **9** | Keep, but treat `docs/regulatory_basis.md` as a blocking launch requirement. |

---

## Quality pass conditions

For the portfolio to be credible, the following should be demonstrable:

1. `make data` builds `facts.db` from EDGAR bulk files with **zero null dates**.
2. Scenarios 5 (10b5-1 sale) and 6 (`F` code) return **`clear`**.
3. A run with a deliberately under-evidenced plan loops through the grounding judge and terminates at the cap.
4. Every `flag`/`escalate` finding cites at least one tool result by `tool_call_id`.
5. CI runs: ruff → mypy → pytest → evals, and evals gate merge.
6. The live URL has a preloaded example that a visitor can watch node-by-node.
7. `docs/regulatory_basis.md` exists and has been sanity-checked by someone with a compliance background — even informally.

---

## Bottom line

Build the **base tier exactly as planned**, but be ruthless about Phase 8 and the fallback/observability surface. A deployed base app with a working grounding loop, clean date parsing, and scenarios 5/6 clearing is a complete, defensible portfolio piece. The pro tier can come after the second app proves the template.
