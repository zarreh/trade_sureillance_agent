# A2 — Trade Surveillance Agent · Build Plan

**Portfolio ref:** `PORTFOLIO_PLAN_V3.md` §7 (A2), §9 (engineering standard),
§9.2 (reject list), §9.3 (repo layout), §9.4 (documentation standard),
§10 (frontend), §11 (IP / data provenance)
**Repo:** `trade_surveillance_agent/` · package `surveillance` · URL `surveillance.zarreh.ai`
**Scope:** `base` committed · `pro` gated (§7, Stretch)
**Drafted:** 2026-08-17 · **Revised:** 2026-08-18 after three independent reviews (§12) and a documentation-standard addition (§6)

---

## 0. Framing

A2 is step 6 in the v3 build sequence, but it is being built **first**. Nothing
else exists yet, so A2 also carries the **template shakedown** — the §9.3 repo
layout, the FastAPI + Next.js baseline, CI, Docker, the deploy pipeline and the
per-repo MkDocs site are all born here.

That is a real risk. A2 is an **L**-cost app and the portfolio plan deliberately
put an **S**-cost app (A6 LexAgent) first so that early friction would
unambiguously be *template* friction rather than *domain* friction. Phase 0 buys
that property back: a walking skeleton with a trivial two-node graph that goes
all the way to a live HTTPS URL before a single line of surveillance logic is
written.

**Phase 0 is not a preamble.** Honestly counted it is roughly a third of base
effort. Treat it as a time-boxed milestone with its own exit criteria, and if it
overruns the box, stop adding to it and move on — the skeleton only has to be
correct, not finished.

**Upstream conflict, resolved.** `PORTFOLIO_PLAN_V3.md` §13 previously scheduled
A2 sixth, after X1/X2/X3 exist, and §8 said X2 is extracted after A6 *and* A2.
Building A2 first invalidated both, so the portfolio document has been amended
(§13, §8, §10 — see the portfolio plan's own changelog). Concretely, for A2 that
means: **no shared package is extracted from a single implementation.**
Components that look shared (UI kit, observability callbacks, eval runners, docs
theme) stay local until a second app exists to extract *from two instances*.

**The one portfolio argument this app makes.** Deterministic facts constrain the
investigation, every published claim links to evidence, and the system reports
the limits of its own evaluation. Anything that does not serve that argument is a
candidate for the stretch tier.

---

## 1. Confirmed decisions

| | |
|---|---|
| Sequence | A2 first; it carries the template shakedown |
| Location | `/home/z187900/courses/great_learning/trade_surveillance_agent` |
| Git | Local repo now, remote added later |
| Scope | `base` committed; `pro` gated on base + evals shipping |
| Infra | VPS + DNS ready. Caddy not yet installed → Phase 0 introduces it |
| Models | **OpenAI primary.** Gemini as an automatic fallback on *availability* failures only. Ollama as an explicit offline profile, not an automatic third leg (§5.4) |
| Persistence | SQLite for base. Postgres only if measured concurrency demands it |
| Tracing | LangSmith for base. Langfuse wired when X1 exists |
| Docs | Per-repo MkDocs + Material, deployed to GitHub Pages (§6) |

---

## 2. Source material

All under `reference/` (gitignored). See `reference/README.md`.

- **Primary:** `notebooks/A2_primary__trade_surveillance_v2.ipynb`
  - 5 `@tool`s: `get_transaction_details`, `get_insider_authorization`,
    `get_compliance_rules`, `calculate_quarterly_trading_volume`,
    `search_insider_trading_history`
  - `AgentState(TypedDict)`: `messages` / `accession_number` / `plan` /
    `findings` / `validation_status`
  - Graph: `planner → agent → (tools ⇄ agent) → validator → END`, routed by
    `should_continue`
  - `gpt-4o-mini` for the agent, `gpt-4o` for the validator
- **Plan validation:** `notebooks/harvest__plan_validator_replanner.ipynb` —
  `plan_validator`, `replanner`, `replan_count` capped at 3, conditional edge
  `approved` / `replan`
- **Auditor loop + eval harness:** `notebooks/harvest__auditor_revision_loop.ipynb`
- **Credibility gating:** `notebooks/harvest__source_credibility_filter.ipynb`

---

## 3. What must NOT be ported

Per §9.2, the notebook is a problem statement, not a reference implementation.

### 3.1 Correctness defects

1. **Dates never parse.** The bulk TSVs store dates as `01-AUG-2025`
   (`DD-MON-YYYY`). The notebook parses them with `format='%Y-%m-%d',
   errors='coerce'`, so **every `FILING_DATE` and `TRANS_DATE` becomes `NaT`**.
   Consequently `calculate_quarterly_trading_volume` and
   `search_insider_trading_history` always return "no transactions found", and
   the notebook's own narrative ("no prior sales in the last 180 days") is an
   artifact of the bug, not a finding. Two of five tools are silently dead.
   *This is the single most important thing to get right in Phase 1.*
2. **`validator_node` mutates `state['messages']` in place** (`messages.append(...)`).
3. **`investigate_transaction` calls `app.stream(...)` and then `app.invoke(...)`** —
   it runs the entire investigation twice, doubling cost and latency.
4. **The validator never re-routes.** It reports ungrounded claims and ends.
   §7 A2 requires a rejection loop — this is the app's whole point.
5. **Validator output is parsed by substring match** (`'GROUNDED FACTS' in
   msg.content`). Replace with `with_structured_output` + Pydantic.
6. **`search_insider_trading_history` compares against `pd.Timestamp.now()`**
   while the data is a fixed historical window — the lookback is meaningless.
   Anchor lookbacks to the transaction date.

### 3.2 Engineering

| In the source | What this repo does |
|---|---|
| Module-global `merged_df` pandas frame | `store/` repository layer over SQLite, injected |
| `sqlite3.connect()` opened inside every tool call | Connection dependency via `api/deps.py` |
| Prompts as f-strings inside node functions | Versioned files in `prompts/`, referenced by id |
| Free-text findings | `ComplianceFinding` Pydantic model |
| Five printed ad-hoc "test cases" | pytest + labelled goldset + CI eval gate |
| Fuzzy title `LIKE` matching for authorisation | `RPTOWNER_RELATIONSHIP` (Officer / Director / TenPercentOwner) as the primary key, title as a refinement |
| `%pip install`, unpinned | `uv.lock` |

### 3.3 Domain gaps

7. **No Rule 10b5-1 handling.** The exculpatory signal that decides whether a
   surveillance system is usable. The data has it (§4.2).
8. **Only `S` and `P` handled**, everything else labelled "Other". The data is
   full of `M` (option exercise), `F` (tax withholding), `A` (grant), `G` (gift).
   `F` in particular is routinely non-suspicious and flagging it is exactly how
   analysts get buried.
9. **Amended filings (`4/A`) ignored.** 455 in one month's data.
10. **No false-positive measurement.** Surveillance fails on false positives, not
    false negatives.
11. **Timing rules with no evidence source.** The source's rule table contains
    `R005 Suspicious Timing Near Earnings`, but no tool can establish an earnings
    date, so the model has to invent one. In a grounding-focused app that is
    fatal. Fixed by the seeded `material_events` table and its tool (§4.1).

### 3.4 Names that overclaim, and what they become

The source's naming asserts conclusions the data cannot support. In a system
whose entire thesis is "claims must be supported", the vocabulary has to be
disciplined too.

| Source | This repo | Why |
|---|---|---|
| `get_insider_authorization` | **`get_applicable_role_limits`** | Relationship and title *select an applicable synthetic limit*. They do not establish that a trade was authorised or pre-cleared |
| "valid 10b5-1 plan" | **`reported_under_10b5_1`** | `AFF10B5ONE` shows a transaction was *reported as* made under a plan. It does not prove the plan satisfies the affirmative-defence conditions |
| `authorized` / `pre-cleared` findings | not emitted in base | There is no approvals evidence. `pre_cleared` is removed from `exculpatory_factors` until a synthetic approvals table exists |

### 3.5 What is genuinely good and must survive

- Hardcoded, parameterised SQL in tools — the agent cannot invent a query.
- Tool results as the sole evidence base; nothing asserted without a tool call.
- Two-model split: cheap model reasons, stronger model validates.
- Severity-tiered rule table rather than a monolithic prompt.

---

## 4. Data

### 4.1 Provenance and build scripts

Per §11: no course data committed. `reference/course_data/` is for schema
discovery only.

- `data/fetch_edgar.py` — downloads SEC **Insider Transactions Data Sets**.
  **Fetches the target quarter plus the two preceding quarters** so every
  transaction in the target quarter has a full 180-day history behind it — two
  quarters does not guarantee that for transactions early in the target window.
  **Must** send a descriptive `User-Agent` carrying a contact email and
  rate-limit requests, per SEC's automated-access policy. Verify the current URL
  at implementation time; do not hardcode a guessed link.
- `data/build_store.py` — TSVs → typed SQLite `facts.db`, subject to §4.4.
- `data/generate_compliance_db.py` — **seeded** generator for `role_limits`,
  `compliance_rules` and **`material_events`**. Own thresholds. Documented as
  synthetic firm policy and synthetic corporate calendar.
- `data/scenarios.py` — labelled scenario injector; produces the canonical
  regression set and the stratified evaluation set (§4.5).

### 4.2 Verified field inventory

Confirmed against `reference/course_data/` (one month: filings 2025-07-01 →
2025-07-31; 35,457 submissions, 39,104 owners, 55,125 non-derivative transactions).

**`SUBMISSION.tsv`** — `ACCESSION_NUMBER`, `FILING_DATE`, `PERIOD_OF_REPORT`,
`DATE_OF_ORIG_SUB`, `NO_SECURITIES_OWNED`, `NOT_SUBJECT_SEC16`,
`FORM3_HOLDINGS_REPORTED`, `FORM4_TRANS_REPORTED`, `DOCUMENT_TYPE`, `ISSUERCIK`,
`ISSUERNAME`, `ISSUERTRADINGSYMBOL`, `REMARKS`, **`AFF10B5ONE`**

**`REPORTINGOWNER.tsv`** — `ACCESSION_NUMBER`, `RPTOWNERCIK`, `RPTOWNERNAME`,
**`RPTOWNER_RELATIONSHIP`**, `RPTOWNER_TITLE`, `RPTOWNER_TXT`, address fields,
`FILE_NUMBER`

**`NONDERIV_TRANS.tsv`** — `ACCESSION_NUMBER`, `NONDERIV_TRANS_SK`,
`SECURITY_TITLE`, `TRANS_DATE`, `DEEMED_EXECUTION_DATE`, `TRANS_FORM_TYPE`,
`TRANS_CODE`, `EQUITY_SWAP_INVOLVED`, `TRANS_TIMELINESS`, `TRANS_SHARES`,
`TRANS_PRICEPERSHARE`, `TRANS_ACQUIRED_DISP_CD`, `SHRS_OWND_FOLWNG_TRANS`,
`VALU_OWND_FOLWNG_TRANS`, `DIRECT_INDIRECT_OWNERSHIP`, `NATURE_OF_OWNERSHIP`
(each with a matching `*_FN` footnote column)

### 4.3 Distributions that drive design

| Field | Observed | Consequence |
|---|---|---|
| `AFF10B5ONE` | `'0'` 21,802 · `'false'` 5,730 · `'1'` 3,613 · null 3,266 · `'true'` 1,046 | The 10b5-1 indicator exists. Encoding is inconsistent across filers; normalise to tri-state `true / false / unknown`, name it `reported_under_10b5_1`, and treat *unknown* as "not established", never as "no plan" |
| `DOCUMENT_TYPE` | `4` 31,672 · `3` 3,183 · `4/A` 455 · `3/A` 83 · `5` 63 | Scope to `4` and `4/A`; amendments supersede per §4.4 |
| `TRANS_CODE` | `S` 22,175 · `A` 9,080 · `M` 6,919 · `F` 6,708 · `P` 4,861 · `J` 1,565 · `D` 1,496 · `G` 1,229 | Code-aware handling. `F` (tax withholding) and `M` (option exercise) get distinct treatment; a naive value threshold flags thousands of them. **Exemption applies per transaction, not per accession** — an `F` line must not clear an unrelated `S` line in the same filing |
| `TRANS_TIMELINESS` | null 54,473 · `E` 602 · `L` 50 | Too sparse to rely on. Derive lateness from `FILING_DATE − TRANS_DATE` in business days (§4.4) |
| `RPTOWNER_RELATIONSHIP` | Officer 14,376 · Director 13,019 · TenPercentOwner 4,181 · combinations | Selects the applicable role limit. Multi-valued, comma-separated; a person may be Director *and* Officer — resolve to the most restrictive applicable limit and record which |
| Date format | `01-AUG-2025` | `DD-MON-YYYY`. Parse explicitly; see §4.4 for the null policy |
| Coverage | one month | Not enough. Fetch three quarters (§4.1) |

### 4.4 Temporal and amendment acceptance criteria

These are decided here, not at implementation time, and each gets a fixture test.

| Question | Decision |
|---|---|
| Does "quarterly volume" mean a calendar quarter or a rolling window? | **Rolling 90 days ending at the transaction date.** The role limit is a firm policy about recent activity, not a fiscal artifact. Both the tool name and the finding text say "rolling 90-day", never "quarterly" |
| What identity supersedes a `4` with a `4/A`? | `(ISSUERCIK, RPTOWNERCIK, PERIOD_OF_REPORT)` plus `DATE_OF_ORIG_SUB` pointing at the original. The latest `FILING_DATE` in a supersession chain is authoritative; superseded rows are retained and marked, never deleted |
| How do amendment row changes affect aggregates? | Aggregates read only non-superseded rows. An amendment that removes a transaction removes it from aggregates; the audit trail still shows it existed and was amended away |
| Which business-day calendar for Section 16(a) lateness? | **NYSE trading calendar**, not `np.busday_count` defaults — the SEC deadline runs on trading days and the two differ around exchange holidays. Pin the calendar source and version in `docs/regulatory_basis.md` |
| What happens to malformed required dates? | **The build fails loudly**, and emits a rejected-row report. Silent `errors='coerce'` is the exact defect being corrected (§3.1.1); a zero-null assertion is the gate |
| What anchors a lookback? | The **transaction date**, never `now()` |

### 4.5 Labelled scenarios and the two evaluation layers

Eight scenarios is a regression suite, not a basis for a published precision
number — one error would move the figure by more than ten points, and live model
output varies between runs. So there are two distinct sets, and they are never
conflated.

**Layer 1 — canonical regression set (~10 cases).** Deterministic, fast, run on
every pull request against recorded or mocked model responses. These are smoke
tests for behaviour, not measurements.

| # | Scenario | Expected |
|---|---|---|
| 1 | Sale inside a blackout window before a seeded earnings event | `flag` |
| 2 | Volume spike vs the insider's own trailing baseline | `flag` |
| 3 | Single trade above the applicable role limit | `escalate` |
| 4 | Section 16(a) filing lag > 2 trading days | `flag` |
| 5 | **Sale reported under a 10b5-1 plan, otherwise identical to #1** | **`clear`** |
| 6 | **`F` tax-withholding disposition at high value** | **`clear`** |
| 7 | **`F` line and an unrelated oversized `S` line in one accession** | **`escalate`** (the `F` must not clear the `S`) |
| 8 | Rolling 90-day volume above the role's limit | `flag` |
| 9 | `4/A` that amends away the transaction driving a flag | `clear` |
| 10 | Ordinary in-limit purchase | `clear` |

Cases 5, 6 and 7 are the ones that make the system credible. An agent that flags
every 10b5-1 sale and every tax withholding is worse than no agent.

**Layer 2 — stratified evaluation set (~150–300 cases).** Sampled across
transaction code, relationship, value decile, 10b5-1 status and amendment
status; labelled by hand; used for every **published** metric. Run against
pinned model versions on a schedule or manual trigger, not on every commit.
Every published number states dataset size, label source, model version, run
date and a confidence interval. A precision figure without an *n* beside it is
the kind of claim this app exists to argue against.

**Metric definitions, fixed before labelling:**

- Dispositions are ordered `clear < flag < escalate`.
- **Flag precision / recall** treat `flag` and `escalate` together as the
  positive class — an analyst opens both.
- Predicting `flag` where the label is `escalate` is *not* a false positive; it
  is a **severity miss**, reported as its own metric. Same for the reverse.
- Predicting anything above `clear` where the label is `clear` is a false
  positive, and this is the headline number.

---

## 5. Architecture

### 5.1 Graph

```
plan (LLM) → check_plan (deterministic) ─┬─ replan (≤1) ──→ check_plan
                                         └─ ok ─→ investigate ⇄ tools
                                                      ↓
                                              draft_finding (LLM)
                                                      ↓
                                              extract_claims  ← claims come FROM the draft
                                                      ↓
                                              judge_grounding ─┬─ unsupported → investigate
                                                               └─ supported  → publish (deterministic)
                                                                                    ↓
                                                                                   END
```

**The draft is the artifact under judgement, and publication is deterministic.**
An earlier version of this plan ran `judge_grounding → finalizer`, where the
finalizer was another LLM chain — meaning the finding the user sees was written
*after* grounding passed and could reintroduce unsupported claims. That defeats
the entire thesis of the app. So:

- `draft_finding` produces a complete `ComplianceFinding` candidate.
- `extract_claims` decomposes **that exact draft**, not the conversation.
- `judge_grounding` scores each claim against the recorded tool results.
- On pass, `publish` emits the **byte-identical draft** with the grounding report
  attached. It contains no model call and cannot alter text. A test asserts
  `published.finding_text == judged_draft.finding_text`.
- On failure, the draft is discarded and the run returns to `investigate` with
  the specific unsupported claims as actionable feedback, not a generic retry.

**Planning is one model call, and validation is deterministic.** The
investigation has five known tools and a mostly fixed mandatory checklist.
An LLM planner *plus* an LLM critic *plus* three replans burns several calls
before any evidence is gathered. So `plan` is a single LLM call and `check_plan`
is code: it verifies the plan references only real tools, covers every mandatory
check for the transaction's code and relationship, and orders dependencies
correctly. Replan is capped at **1**. This is the same argument as D-A2-3 and
A13's deterministic supervisor — *don't spend a model call on a decision an `if`
can make* — and it is a better portfolio story than the source's LLM critic.

Bounded loops, both counted in state:
- `replan_count ≤ 1`
- `evidence_pass ≤ 2`

### 5.2 Files (§9.3)

```
src/surveillance/
├── api/
│   ├── routes/{investigations,health}.py
│   ├── deps.py                # settings, store connections, compiled graph
│   └── streaming.py           # SSE bridge over astream_events
├── graph/
│   ├── state.py               # SurveillanceState + PlannerView / InvestigatorView / GroundingView
│   ├── builder.py             # the only file that wires nodes and edges
│   ├── edges.py               # route_after_check_plan, route_after_agent, route_after_grounding
│   ├── policies.py            # model choice + provider profile per node
│   ├── budget.py               # per-investigation cost guardrail (§5.5)
│   ├── nodes/                 # plan · check_plan · replan · investigate · draft_finding · extract_claims · judge_grounding · publish
│   ├── agents/investigator.py # model + 6 tools + prompt id, nothing else
│   └── chains/                # planner · claim_extractor · grounding_judge · finding_writer
├── tools/                     # one file per tool + registry.py
├── store/                     # FactStore · PolicyStore · RunStore
├── schemas/
├── prompts/                   # versioned, referenced by id
├── settings.py
└── observability.py           # tracing callbacks + cost accounting
frontend/                      # Next.js 15, HTTP client only
docs/                          # MkDocs site — see §6
data/ · evals/ · tests/
```

`check_plan` lives in `nodes/`, not `chains/`, because it makes no model call.
Node filename == registered node name == trace span name.

`mcp/` is deferred to the stretch tier (§7).

### 5.3 Schemas

- `InvestigationPlan(steps: list[PlanStep])`, `PlanStep(order, objective, tool, why)`
- `PlanCheck(ok: bool, missing_checks: list[str], unknown_tools: list[str], ordering_issues: list[str])` — produced by code, not a model
- `Claim(id, text, cited_tool_call_ids: list[str])`
- `ClaimAnalysis(claim_id, supported: bool, evidence_span, reason)`
  — design lifted from the PGP helpdesk copilot's claim-grounding schema (§9.2 keep-list)
- `GroundingReport(claims, unsupported: int, confidence: Literal["high","medium","low"])`
- `ComplianceFinding(disposition: Literal["clear","flag","escalate"], severity,
  rules_cited: list[RuleCitation], claims, evidence_chain: list[ToolCallRecord],
  exculpatory_factors: list[ExculpatoryFactor], confidence)` — **frozen** once judged
- `ExculpatoryFactor(kind, evidence_tool_call_id, applies_to_transaction_sk)` —
  scoped to a transaction, never to a whole accession

`exculpatory_factors` is a first-class field, not a footnote. Base supports
`reported_under_10b5_1`, `tax_withholding`, `option_exercise`,
`below_all_thresholds`. `pre_cleared` is deliberately absent — there is no
approvals evidence to support it (§3.4).

### 5.4 Model policy

`graph/policies.py` defines **profiles**, not a fallback stack per call:

| Profile | Models | Used by |
|---|---|---|
| `fast` | `gpt-4o-mini` | planner, claim extractor, investigator |
| `reasoning` | `gpt-4o` | grounding judge, finding writer |
| Availability fallback | Gemini equivalent, engaged **only** on connection errors, timeouts, 429s and 5xxs | both profiles |
| `offline` profile | Ollama for every node, selected by an explicit setting | local development, sovereignty demo |

Two rules that matter more than the provider list:

1. **Fallback is for availability, never for validation.** A schema-validation or
   tool-calling failure must surface, not silently trigger a different model. A
   broad `except` that reaches for another provider hides prompt and schema
   defects — precisely the class of bug this app is supposed to catch.
2. **Bind `with_structured_output` per model *before* composing fallbacks.**
   Calling it on an already-fallback-wrapped runnable does not behave correctly.

Cross-provider contract tests (each provider against the same Pydantic schema)
run outside pull-request CI, on the same schedule as the layer-2 evals.

### 5.5 Cost guardrail

`graph/budget.py` enforces a per-investigation ceiling on tool calls, total
tokens and wall-clock time. On breach the run terminates with a partial finding
marked `incomplete` and the reason recorded — it does not silently truncate. The
ceiling is a setting, reported in the UI cost meter next to actual usage. A
public surveillance demo that can run unbounded is a bad look, and the cap is
also what makes the per-investigation cost figure honest.

---

## 6. Documentation

Every portfolio repo, including this one, ships a **per-repo MkDocs + Material
site deployed to GitHub Pages**. This is a portfolio-wide standard — see
`PORTFOLIO_PLAN_V3.md` §9.4 — not an A2-specific extra, but A2 is where it is
proven first.

### 6.1 Why per-repo, not one central site

The docs live with the code they describe: ADRs and the API reference are
generated from the actual source, so they cannot silently drift the way a
separate documentation repo does. `docs.zarreh.ai` becomes a thin hub linking out
to each app's Pages site rather than hosting the content itself. The
"don't run MkDocs a dozen times" concern is real, but the right fix is a shared
theme/config package (`zarreh-docs-theme`, portfolio asset **X5**) extracted
after the *second* app builds one of these sites, not a shared site — same rule
as X2/X3 (§0).

### 6.2 Stack

MkDocs + Material. Plugins: `mkdocstrings[python]` (API reference generated from
source, never hand-written), `mkdocs-gen-files` + `mkdocs-literate-nav` (nav
generated, not maintained by hand), `mkdocs-glightbox` (image zoom for charts),
Mermaid via Material's native superfences (diagrams stay as text in markdown, so
they show up in git diffs — no exported diagram images except the hero). Deploy
via GitHub Actions to GitHub Pages on merge to `main`. `mkdocs build --strict`
runs in pull-request CI so a broken link or nav entry fails the build before
merge, the same way ruff or mypy would.

### 6.3 Three audiences, not three topics

Every page is written for exactly one reader:

| Reader | Wants | Gets |
|---|---|---|
| Buyer / board member | What problem, why it matters, what it costs | Plain language, one diagram, the evidence charts |
| Hiring engineer | How it's built and why those trade-offs | Architecture, ADRs, state flow, source reference |
| Operator / reproducer | Can I run this myself | `make data`, config, API reference |

Every architecture page opens with a Material admonition: *"In one paragraph,
for a non-engineer."* This single rule is what keeps the site legible to the
audience that actually buys, without diluting the engineering detail underneath.

### 6.4 Site map

```
docs/
├── index.md                    # problem in plain language + hero diagram + live demo link
├── how-it-works/
│   ├── in-plain-language.md
│   ├── the-investigation.md    # one real run, walked node-by-node, with screenshots
│   ├── grounding.md            # the centrepiece, explained without jargon
│   └── what-it-wont-do.md      # scope and disclaimer, stated plainly
├── architecture/
│   ├── overview.md
│   ├── data-pipeline.md
│   ├── tools.md
│   ├── state-and-flow.md
│   └── decisions/              # ADRs, one file per D-A2-n
├── evidence/
│   ├── evaluation.md           # layer-1 + layer-2 results, with n and confidence intervals
│   ├── false-positives.md      # the alert-fatigue chart and what it means
│   ├── cost-and-latency.md
│   └── data-profile.md         # the §4.3 distributions, visualised
├── regulatory-basis.md
├── run-it-yourself.md
├── api.md
├── reference/                  # mkdocstrings-generated, not hand-written
└── assets/
    ├── plot_style.mplstyle     # shared aesthetic, portfolio palette
    └── *.svg                   # generated charts and the one hand-polished hero diagram
```

### 6.5 Generated visualisations — never hand-drawn

`docs/generate_plots.py`, invoked by `make docs-assets`. **CI fails if
regenerating the plots produces a diff against what is committed**, so a chart
can never quietly drift from the data it claims to describe. Charts:

1. Transaction-code distribution with `F` and `M` highlighted — makes §3.3.8 visible in one glance
2. `AFF10B5ONE` tri-state distribution including the `unknown` share
3. Filing-lag distribution in trading days with the 2-day §16(a) line drawn
4. Value distribution by relationship, log scale, role limits overlaid
5. Disposition confusion matrix with severity misses distinguished from false positives
6. **Precision/recall vs. alert volume — the alert-fatigue curve.** The advisory chart
7. **Unsupported claims per grounding pass (0 → 1 → 2).** Shows the centrepiece working
8. Per-node cost and p50/p95 latency per investigation
9. Data coverage timeline showing why three quarters are needed for a 180-day lookback

Aesthetics come from a shared `docs/assets/plot_style.mplstyle` — portfolio
palette, no chartjunk, readable at 800px. Each chart exports `*-light.svg` and
`*-dark.svg`, selected via Material's `#only-light` / `#only-dark` image
suffixes so charts work in both color schemes.

### 6.6 Screenshots

`make docs-screenshots` reuses the Phase 6 Playwright smoke test against the
preloaded example to capture the UI shots used in
`how-it-works/the-investigation.md`. Automated so they never go stale.

### 6.7 Phase placement

| Phase | Docs work |
|---|---|
| 0 | `mkdocs.yml`, Material, plugin config, GitHub Pages deploy workflow, `--strict` in PR CI — a template concern, ships with the skeleton |
| 1 | Data-profile plots (chart 1, 2, 3, 4, 9) — fall out of the profiling work for free |
| 4 | The grounding-loop chart (chart 7) |
| 7 | Evaluation plots (chart 5, 6, 8) |
| 8 | Plain-language pages, the investigation walkthrough, screenshots, final polish |

---

## 7. Phases

**Status (2026-08-19): `base` is fully built.** Phases 0–8 below are all
complete, tested, and pushed with CI+CD green at every step — see the repo's
`git log` for the phase-by-phase commits. What's genuinely deferred (Layer 2
evaluation, cross-provider profiles, live deployment, the `pro` tier) is
listed in [§7 Stretch](#stretch-pro-tier-gated-only-after-base-is-deployed-and-phase-7-metrics-are-published)
below and cross-referenced from the specific docs pages each item touches
(`docs/architecture/decisions/D-A2-4-fallback-for-availability.md`,
`docs/evidence/evaluation.md`). This section is kept as written during
planning — a historical record of the reasoning behind each phase — not
rewritten after the fact to match what was actually built.

### Phase 0 — Template shakedown *(time-boxed; ~⅓ of base effort)*

Repo scaffold per §9.3 with every folder present, even near-empty. `uv` +
`pyproject.toml` + `uv.lock`. `pydantic-settings`. A trivial two-node graph
(`echo → done`). FastAPI `/healthz` plus one SSE endpoint over `astream_events`.
Minimal Next.js 15 page consuming the stream. Multi-stage Dockerfile (slim base,
non-root, `HEALTHCHECK`), `compose.yaml`, `Makefile` (`dev` / `test` / `eval` /
`up` / `data` / `docs-assets` / `docs-screenshots`). Pre-commit: ruff, mypy,
`detect-secrets`, `check-added-large-files`. MkDocs skeleton (§6) with the Pages
deploy workflow. Caddy on the VPS for automatic HTTPS at `surveillance.zarreh.ai`.

**CI and CD are separate workflows.** Pull requests run ruff → mypy --strict →
pytest → import-linter → `mkdocs build --strict`. Image build, GHCR push, deploy
and the Pages publish run on merge to `main` only. An ordinary pull request must
never push an image or touch the VPS.

**Exit:** the live URL streams the trivial graph node-by-node; PR CI green;
`make up` works from a clean clone; the docs site builds and deploys.

### Phase 1 — Data foundation *(parallel with 0; no LLM)*

`fetch_edgar.py`, `build_store.py`, `generate_compliance_db.py`, `scenarios.py`,
`store/` repository layer with typed row models, a small fixture DB for tests.

Every decision in §4.4 gets a fixture test: `DD-MON-YYYY` parsing with a
build-failing zero-null assertion and a rejected-row report; `AFF10B5ONE`
tri-state normalisation; NYSE-calendar filing lag; `RPTOWNER_RELATIONSHIP`
splitting and most-restrictive resolution; `4/A` supersession chains including an
amend-away case; seeded `material_events`; indexes on `ACCESSION_NUMBER`,
`RPTOWNERCIK`, `TRANS_DATE`.

**Exit:** `make data` builds `facts.db` + `policy.db` from nothing; the build
fails on a deliberately corrupted date; supersession and amend-away fixtures
pass; the data-profile charts (§6.5 #1, #2, #3, #4, #9) render from `facts.db`.

### Phase 2 — Tools *(after 1)*

Six tools with Pydantic arg schemas and typed JSON returns, row and token caps,
`tools/registry.py`, unit tests against the fixture DB.

| Tool | Change from source |
|---|---|
| `get_transaction_details` | Returns `reported_under_10b5_1` tri-state and transaction code semantics |
| `get_applicable_role_limits` | Renamed (§3.4); resolves from relationship first, title second, most-restrictive wins |
| `get_compliance_rules` | Unchanged in shape; severity tiers retained |
| `rolling_90d_trading_volume` | Renamed and anchored to the transaction date, not `now()`; code-aware aggregation |
| `insider_trading_baseline` | Anchored to the transaction date; returns the insider's own trailing distribution |
| **`get_material_events`** | **New.** Deterministic lookup against seeded `material_events` — the evidence source blackout-window reasoning previously lacked (§3.3.11) |

**Exit:** every tool callable and tested with no LLM and no network; each returns
a stable `tool_call_id`-addressable record the grounding judge can cite.

### Phase 3 — Graph core *(after 0 and 2)*

`state.py` + narrow projections, `chains/`, `agents/investigator.py`, the
`plan` / `check_plan` / `replan` / `investigate` / `draft_finding` nodes,
`policies.py`, `budget.py`, `builder.py`, `edges.py`, prompts as versioned files.

Single provider profile only. Cross-provider work is scheduled, not blocking.

**Exit:** one accession number in → a structured `ComplianceFinding` draft out;
`check_plan` rejects a plan referencing a non-existent tool and one missing a
mandatory check; the budget guardrail terminates a deliberately runaway run.

### Phase 4 — Grounding loop ★ *(after 3)*

`extract_claims.py` decomposing the **draft finding**; `judge_grounding.py`
producing a `GroundingReport`; `route_after_grounding` returning to `investigate`
with the specific unsupported claims when any remain, capped at `evidence_pass ≤ 2`;
`publish.py` as deterministic assembly; `citation_coverage` per run.

**Exit:** a deliberately under-evidenced run loops back, receives actionable
feedback, gains evidence and the unsupported count drops; a test asserts
termination at the cap; **a test asserts the published finding is byte-identical
to the judged draft**; the grounding-loop chart (§6.5 #7) renders from a real run.

### Phase 5 — API, persistence, observability *(after 4)*

`POST /investigations`, `GET /investigations/{id}`,
`GET /investigations/{id}/events` (SSE). DI in `deps.py`. **SQLite** for the
LangGraph checkpointer and `RunStore` — a single-instance public demo does not
need Postgres, and adding it costs a service to run. **LangSmith only**, behind
the callback abstraction so Langfuse drops in when X1 exists. Per-node cost
accounting. `structlog` JSON with a correlation id threaded into every trace.
`slowapi` rate limiting and input size caps — this is internet-facing.

**Exit:** every run persisted and replayable from the store; traces carry
per-node cost; rate limits demonstrably enforced.

### Phase 6 — Frontend *(after 5; parallel with 7)*

**First paint first.** Ship the preloaded-example story — a visitor lands and
watches a full investigation stream node-by-node without typing — before any
component polish. Then: `RunConsole`, `TraceTimeline`, `EvidencePanel`,
`CostMeter`, and a `ValidatorStrip` showing grounding passes and rejections.
Types generated from the FastAPI OpenAPI schema via `openapi-typescript` plus Zod
— cheap, and it makes Pydantic the single source of truth end to end. One-line
synthetic-data statement on every page. Tested loading, success, empty and error
states. Playwright smoke test — the same test `make docs-screenshots` reuses.

Components stay **local**. No package extraction from one implementation (§0).

The UI must render `reported_under_10b5_1: unknown` as "not established", never
as an absence of a plan. The vocabulary discipline of §3.4 has to reach the pixel.

**Exit:** a visitor sees a full investigation with clickable evidence without
typing anything; all four UI states tested.

### Phase 7 — Evals *(after 4; parallel with 6)*

Layer 1 canonical regression set against recorded model responses, gating pull
requests. Layer 2 stratified labelled set against pinned model versions, run on
a schedule or manual trigger, producing the published metrics with *n*, label
source, model version, run date and confidence intervals.

Metrics: disposition accuracy, flag precision / recall (positive class =
`flag` ∪ `escalate`), severity-miss rate, false-positive rate on `clear` labels,
citation coverage %, unsupported-claim rate, tool-call accuracy, cost per
investigation, p50/p95 latency. DeepEval permitted only under `evals/`.

**Exit:** `make eval` prints the matrix with sample sizes; PR CI fails on
regression against layer 1; canonical cases 5, 6, 7 and 9 behave as specified;
the evaluation charts (§6.5 #5, #6, #8) render from real eval output.

### Phase 8 — Docs, credibility, launch *(after 5, 6, 7)*

Plain-language pages, the investigation walkthrough with automated screenshots,
final docs polish (§6). `docs/regulatory_basis.md`; **6** ADRs (§8); `NOTICE.md`
(done); prototype banner; portfolio card per §14; a `/writing` post on the
grounding loop.

**`docs/regulatory_basis.md` covers:** SEC Rule 10b-5 · Section 16(a) and the
Form 4 two-business-day reporting obligation · **Rule 10b5-1** plans as a
reported exculpatory signal, with the affirmative-defence caveat stated
explicitly · FINRA Rule 3110 supervision as the reason a human reviewer stays in
the loop · the NYSE calendar source used for lateness · an explicit statement
that the role-limit table, the approvals model and `material_events` are
synthetic.

**Launch gate:** `regulatory_basis.md` written against primary sources with every
claim cited, plus a prominent prototype disclaimer. External review by a
compliance professional is strongly preferred and should be sought, but it is not
a blocking dependency — it is not something that can be scheduled reliably, and
an uncited document reviewed informally is worse than a cited one reviewed by
nobody.

### Stretch — `pro` tier *(gated: only after base is deployed and Phase 7 metrics are published)*

Explicitly **not** in the primary timeline. Each item is close to a second
application and none of them is required for the argument in §0.

- **Alert triage queue** — batch-score a filing day, rank by severity, queue UI.
- **False-positive analysis view** — the layer-2 numbers rendered as an
  alert-fatigue story. *(The numbers themselves ship in Phase 7; this is only the
  presentation of them.)*
- **Investigation replay** — shareable permalink re-playing a persisted trace.
- **MCP export** — FastMCP server over `tools/registry.py`. Cheap, but not part
  of A2's argument; §7 A2 says only A9 makes MCP the headline.
- **Cross-provider profiles** — Gemini and Ollama profiles promoted from
  scheduled contract tests to a demonstrated sovereignty mode.
- **Postgres and Langfuse** — if concurrency measurements or X1 make them real.

---

## 8. Decisions to record as ADRs

Six, per §9's 3–6 guideline. The template-shakedown choice is a portfolio-level
decision and belongs in the portfolio document, not this repo's ADR folder.

| id | Decision |
|---|---|
| **D-A2-1** | **Publication is deterministic.** The draft finding is the artifact judged, and the published finding is byte-identical to the judged draft. No model call runs after the grounding check |
| **D-A2-2** | **Plan once, validate in code.** One LLM planner, a deterministic `check_plan`, replan capped at 1. Don't spend a model call on a decision an `if` can make |
| **D-A2-3** | **No vector store.** Compliance rules live in SQL and are cited by `rule_id`. §9 says "Qdrant everywhere", but A2 has no genuine retrieval problem, and a table is exact where an embedding is approximate |
| **D-A2-4** | **Fallback is for availability, not validation.** One primary provider; a Gemini fallback engages only on transport-level failure; Ollama is an explicit offline profile. Schema failures surface |
| **D-A2-5** | **The vocabulary does not overclaim.** `get_applicable_role_limits` not `get_insider_authorization`; `reported_under_10b5_1` not "valid plan"; unknown means not established; exculpatory factors are scoped per transaction, not per accession |
| **D-A2-6** | **Two evaluation layers.** A deterministic canonical set gates pull requests; a stratified labelled set against pinned model versions produces every published metric, always with *n* and a confidence interval |

---

## 9. Out of scope

**Never in A2:** real-time market or price feeds · derivative transactions
(`DERIV_TRANS.tsv`) · Forms 3 and 5 · authentication and multi-tenancy · anything
in Track B.

**Deferred to stretch or a later app:** MCP export · batch triage · public replay
UI · Postgres · Langfuse / dual observability · automatic multi-provider fallback
in the request path · extraction of any shared package or component library
(requires two implementations, §0).

---

## 10. Risks

1. **A2 is L-cost and carries template risk.** → Phase 0 is time-boxed; the pro
   tier is out of the primary timeline entirely; Phase 5 uses SQLite and one
   tracing backend so no phase blocks on infrastructure.
2. **Finance domain errors are the most likely way to get caught out.** → every
   claim in `regulatory_basis.md` cited to a primary source; the §3.4 vocabulary
   discipline; prominent disclaimer; never claim supervisory fitness.
3. **Live EDGAR bulk data may differ from the reference sample** (column drift,
   `AFF10B5ONE` encoding, quarter packaging). → Phase 1 is LLM-free and
   front-loaded so schema surprises surface before any graph work; the build
   fails loudly rather than coercing.
4. **A published precision number is the app's most attackable claim.** → two
   evaluation layers, fixed metric definitions before labelling, *n* and
   confidence intervals on every figure, pinned model versions.
5. **Three quarters of EDGAR data is a large download.** → cache the archives
   outside the repo, make `make data` resumable, and keep a small committed
   fixture so tests never need the full set.

---

## 11. Quality gate — conditions to publish `base`

1. Required dates parse with no silent coercion; a corrupted date fails the
   build; supersession and amend-away fixtures pass; the historical window is
   demonstrably complete for every transaction in the target quarter.
2. Every tool runs with no network and no LLM, returns typed capped results, and
   is addressable by `tool_call_id`.
3. An under-evidenced finding receives *specific* grounding feedback, obtains the
   missing evidence on the next pass, and terminates at the configured cap.
4. **The exact finding shown to the user is the exact finding that passed the
   grounding judge**, asserted by test.
5. Canonical cases 5, 6, 7 and 9 behave as specified — reported 10b5-1 and
   isolated `F` do not produce naive alerts, an `F` does not clear an unrelated
   `S`, and an amended-away transaction stops driving a flag.
6. Every published metric states dataset size, label source, model version, run
   date and a confidence interval.
7. The per-investigation budget guardrail is enforced and its ceiling is visible
   in the UI beside actual usage.
8. The deployed API enforces input and rate limits; the frontend has tested
   loading, success, empty and error states; CI and CD are separate workflows.
9. `regulatory_basis.md` exists with every claim cited to a primary source, and
   the prototype disclaimer is on every page.
10. The docs site builds `--strict` and deploys to GitHub Pages; every published
    chart regenerates byte-identically from `make docs-assets`.

---

## 12. Review history

Revised 2026-08-18 after three independent reviews
(`PLAN_REVIEW_claude-sonnet-5.md`, `REVIEW_GITHUB_COPILOT.md`,
`REVIEW_Kimi_K2_7_Code.md`), then again the same day to add the documentation
standard (§6). Substantive changes from the reviews:

| Change | Origin |
|---|---|
| Publication made deterministic; draft is the judged artifact | Copilot — the finalizer could reintroduce unsupported claims after grounding passed. Architectural defect |
| `material_events` table and tool added | Copilot — the earnings-timing scenarios had no evidence source, so the model would have had to invent one |
| Vocabulary discipline (§3.4) | Copilot — tool and field names asserted conclusions the data cannot support |
| Exculpatory factors scoped per transaction | Copilot — an `F` line was able to clear an unrelated `S` in the same accession |
| Two evaluation layers with fixed metric definitions | Copilot and Kimi — eight scenarios cannot support a published precision number |
| Planner reduced to one call, validation made deterministic, replan capped at 1 | Copilot and Kimi — an LLM critic over five fixed tools is latency and structured-output surface for no measured gain |
| Provider fallback narrowed to availability-only, Ollama made an offline profile | All three reviews |
| Postgres → SQLite; Langfuse deferred | Copilot and Kimi — X1 does not exist yet, so there is nothing for a second trace backend to feed |
| MCP, batch triage, replay moved to gated stretch | Copilot and Kimi |
| Phase 0 time-boxed and named honestly; CI split from CD | Kimi and Copilot |
| Temporal and amendment acceptance criteria decided up front (§4.4) | Copilot and Kimi |
| Per-investigation cost guardrail | Kimi |
| NYSE calendar for Section 16(a) lateness | Kimi |
| `pre_cleared` removed from exculpatory factors | Kimi — listed but never defined or evidenced |
| ADRs reduced from eight to six | Claude Sonnet 5 |
| External compliance review softened from blocking to strongly-preferred | Claude Sonnet 5 |

**Not adopted.** Removing the planner entirely — §7 A2 names plan validation as
part of A2's architecture, and one planner plus a deterministic checker keeps the
pattern while removing the cost. Dropping the earnings scenarios — the seeded
`material_events` table is cheap and the rule table needs it regardless.

**Added 2026-08-18 (user request):** the documentation standard, §6. Portfolio
document amended in parallel — see `PORTFOLIO_PLAN_V3.md` §9.4, §14, §13, §8, §10.

---

## 13. v4 upgrade — process audit, RL environment, and UI/readiness pass

*Added 2026-10-29 from `PORTFOLIO_PLAN_V4.md` (§0a, §6a, §9.5, §10.1, §13). This section is the build plan for a separate implementation conversation; nothing here has been built yet. Sections 0–12 above remain the record of the `base` build.*

### 13.0 Purpose and framing

**A2 is still an insider-trading surveillance product.** Its job, its architecture and its `base` acceptance criteria (§11) do not change. v4 adds three things, in this order:

| Part | What | Why |
|---|---|---|
| **P — process audit** | A deterministic audit of *how* the investigator got to its finding, run on every real investigation, stored on the finding, shown in the UI | The product currently verifies the *plan* (`check_plan`) and the *claims* (LLM grounding judge). Nothing deterministic checks what the investigator actually did |
| **R — RL environment** | The same investigation loop as a Gymnasium environment (`reset`/`step`), a reward built from the process audit plus an outcome table, scripted reference and gaming policies, and a CI gate | Shows exactly how the product's checks work as verifier and reward design, and proves they cannot be gamed. This is the evidence for the AI-evaluation and RL-environment goal (G6) |
| **U — UI and deployment readiness** | Bring the frontend and deployment files up to the A3/A12 standard (`PORTFOLIO_PLAN_V4.md` §10.1) | A stranger should understand the app in 30 seconds, and the repo should be deployable. Currently it is one unstyled page and has no production compose, frontend Dockerfile or deploy doc |

**The RL layer is an extra, not the point.** Every RL artefact must be explained in terms of a product behaviour it protects, and the product must work and read well with R removed.

#### How the RL layer helps the product — the "before and after" for the case study

| Question | Before v4 | After v4 |
|---|---|---|
| Did it reach the right disposition? | Disposition accuracy, n=10, scored by the scripted stand-in (`evals/oracle.py`) | Unchanged |
| Did it gather every required piece of evidence, in the right order, on the real run? | Only the *plan* is checked (`check_plan`), not what was executed | Checked on every real investigation (process audit) |
| Is every citation a real tool call? | Only the LLM grounding judge looks at claims | Deterministic citation-validity check on every real investigation |
| Is a stated exemption (10b5-1, tax withholding, option exercise) backed by data? | Exculpatory factors are derived from tool results in code, but exemption language in the narrative is unchecked | Narrative exemption mentions are checked against the derived factors |
| Can a lazy or gaming investigator still score well? | Yes. `always_flag` gets 100% flag recall from `compute_metrics`; skipping evidence is invisible | No. A CI gate proves seven shortcut/gaming policies score at least 0.5 below the reference policy |
| Can a reviewer see any of this? | No | The investigation page shows the process audit; a new `/evaluation` page shows the policy table and chart |

**What R proves, precisely.** The reference policy scoring 1.0 on all ten scenarios is a *consistency check* of the environment and reward (the reference reuses the oracle's logic and the scenario labels were designed to match it). It is not a performance claim and must never be presented as one. The valuable result is the *other* column: each gaming policy loses, and *why* (§13.4).

### 13.1 Decisions

| # | Decision | Status |
|---|---|---|
| D-A2-7 | The process audit lives in `src/` and is the reward's trajectory component: one source of truth, no separate reward logic | Decided |
| D-A2-8 | Reward design: outcome table, trajectory multiplier applied only to positive outcomes, penalties never scaled, LLM judge excluded | Decided (§13.4) |
| D-A2-9 | `gymnasium` is a dev-only dependency, used only under `evals/`; an import-linter contract forbids `surveillance` from importing it | Decided |
| D-A2-10 | The `ui/` primitives are copied from A3 for now; extraction into X3 is portfolio decision D20 | Open, see `PORTFOLIO_PLAN_V4.md` §15 |
| D-A2-11 | The LLM grounding judge stays in the product and stays *out* of the reward (a persuasive claim must not raise a score) | Decided |

### 13.2 Phase P — process audit (product)

**Goal.** One pure function, no I/O, no LLM, no gymnasium import, that audits an investigation's *process*.

**Where.** `src/surveillance/graph/trajectory_audit.py` (graph layer, beside `evidence.py`). It imports only schemas and `graph/evidence.py`, so the existing layering contract holds, and `evals/` can import it.

**Inputs.** `records: list[ToolCallRecord]` (from `extract_tool_call_records` in `graph/evidence.py`, in call order), `claims: list[Claim]` (each with `cited_tool_call_ids`), and `claimed_exemptions: list[ClaimedExemption]` (kind plus optional transaction sk).

**Output.** `ProcessAudit` (a new Pydantic model in `schemas/finding.py`):

| Field | Meaning |
|---|---|
| `mandatory_tools_called` / `mandatory_tools_missing` | Against `MANDATORY_TOOLS` in `graph/nodes/check_plan.py` |
| `coverage` | called ÷ 6 |
| `details_first` | `get_transaction_details` was the first call |
| `fabricated_citation_ids` | cited IDs that match no record |
| `citation_validity` | 0 if any ID is fabricated, otherwise the fraction of claims with at least one valid ID |
| `unsupported_exemptions` | claimed exemptions not present in `derive_exculpatory_factors(records)`, limited to the true exemptions (`reported_under_10b5_1`, `tax_withholding`, `option_exercise`); `below_all_thresholds` is never an exemption (same rule as `evals/oracle.py`) |
| `exemption_validity` | 0 if any exemption is unsupported, otherwise 1 |
| `trajectory_score` | coverage × ordering factor (1, or 0.5 if not `details_first`) × `citation_validity` × `exemption_validity` |

**How the product uses it.** `publish_node` (`graph/nodes/publish.py`) computes the audit from state and attaches it to `PublishedFinding` as `process_audit`. It is **record-only**: it never changes the disposition and never routes the graph. For the live product the claimed exemptions are extracted from `finding_text` by a small documented keyword map (10b5-1, tax withholding, option exercise); for the RL environment they are passed explicitly, with the transaction sk.

**Open detail to settle in the ADR (D-A2-7).** Because exculpatory factors are *derived* in code, an exemption in the structured field is valid by construction; the audit's value in the product is the *narrative* mention and the citation and coverage checks. State this plainly in the ADR.

**Tests.**
- One unit test per field, including: a fabricated ID zeroes `citation_validity`; a `below_all_thresholds` claim is not an exemption; `F` does not support an exemption on an unrelated `S` line (mirrors canonical case 7).
- Regression: the "published == judged draft" test (§11 item 4) still passes — the audit is added alongside, not folded into, the judged draft.
- API schema: the OpenAPI snapshot includes `process_audit`; `make frontend-types` regenerates `frontend/src/lib/api-types.ts`.

**Mutation check.** Removing the fabricated-ID check must fail both the unit tests and, after Phase R, the RL gate.

### 13.3 Phase R — RL environment

All RL code lives under `evals/`. Three files, mirroring how `evals/` is already organised:

| File | Contents |
|---|---|
| `evals/rl_env.py` | `SurveillanceEnv(gymnasium.Env)`, `compute_reward`, `RewardBreakdown` |
| `evals/rl_policies.py` | The scripted policies |
| `evals/run_rl.py` | The runner and CI gate; writes the generated results JSON |

**R1 — environment (`rl_env.py`).**
- Subclass `gymnasium.Env`. Observation and action spaces are `gymnasium.spaces.Text`. Observations and actions are **JSON strings**, which is what an LLM policy would emit.
  - Gymnasium's default `Text` charset is alphanumeric only, so set a printable charset and a `max_length` (about 20,000) explicitly, or `check_env` will fail.
- `reset(seed=None, options={"scenario_id": ...})`
  - Builds the stores once with `_build_eval_stores` from `evals/canonical.py` and the tools with `build_tools`.
  - Returns an observation `{accession_number, tools: [{name, args_schema}], budget: {max_tool_calls, max_wall_clock_seconds}}`, and `info = {"episode_id": ...}`.
  - **Never returns** a label, scenario id, scenario name or expected disposition. A test enforces this (§13.5).
  - With `seed` and no `scenario_id`, picks a scenario deterministically.
- `step(action: str)` — action is JSON:
  - `{"type":"tool_call","name":...,"args":{...}}` runs the real tool and returns `{"tool_call_id":"t1","result":...}`. IDs are `t1`, `t2`, … in call order.
  - `{"type":"submit","disposition":"clear|flag|escalate","claims":[{"text":...,"cited_tool_call_ids":[...]}],"exemptions":[{"kind":...,"transaction_sk":...}]}` ends the episode (`terminated=True`) and returns the reward.
  - Anything unparseable, an unknown tool, or bad arguments: reward −0.05, counts toward the budget, episode continues.
  - Exceeding the budget (`DEFAULT_BUDGET` in `graph/budget.py`: tool-call count and wall clock): `truncated=True`, reward −0.5, no submit scored.
- Step reward is 0 until `submit` or truncation; the invalid-action penalty is accumulated and added at the end, so the final return is a single `RewardBreakdown`.

**R2 — reward (`compute_reward`).**

*Outcome table* (expected → submitted):

| Expected → submitted | Outcome |
|---|---|
| correct | +1.0 |
| clear → flag | −0.25 |
| clear → escalate | −0.5 |
| flag → clear | −0.75 |
| flag → escalate | −0.10 |
| escalate → flag | −0.25 |
| escalate → clear | −1.0 |

Rationale, which belongs in the ADR: missing a violation is worse than over-alerting; a severity miss (flag vs escalate) is milder than a wrong direction; alert fatigue is the real cost of false positives (`docs/evidence/false-positives.md`).

*Trajectory multiplier* `P` is `ProcessAudit.trajectory_score` from Phase P.

*Total.*
- If outcome > 0: `total = outcome × P`.
- If outcome ≤ 0: `total = outcome` — **penalties are never scaled by `P`**.
- Then subtract 0.01 per tool call beyond the six mandatory ones, and 0.05 per invalid action.

*Why the unscaled-penalty rule matters.* If a wrong answer were multiplied by `P`, an agent that skips all evidence (`P = 0`) would turn every wrong answer into a score of 0 and, whenever it is unsure, skipping evidence would beat investigating. This is the central reward-design lesson and the case study's "lessons learned" (§13.7). A regression test pins it.

*Judge excluded.* The LLM grounding judge is not part of the reward (D-A2-11).

**R3 — scripted policies (`rl_policies.py`).** Each is a function from observation history to the next action.

| Policy | Behaviour | What it demonstrates | Expected mean (to be recorded, not trusted) |
|---|---|---|---|
| `reference` | Reuses the oracle's decision logic (refactor `evals/oracle.py` to expose a public `decide(records)`; do not import the private `_line_verdict`) after gathering all six tools with arguments derived from real results | Consistency of env + reward | 1.00 on every scenario |
| `always_flag` | Gathers full evidence, cites real IDs, always submits `flag` | Outcome-only metrics reward a degenerate policy: it gets 100% flag recall from `compute_metrics` | ≈ +0.25 |
| `always_escalate` | Same, always `escalate` | Over-alerting | ≈ −0.04 |
| `always_clear` | Same, always `clear` | Missing violations | ≈ −0.10 |
| `no_evidence_guesser` | Is handed the correct label, calls no tools, submits it | Right answer without investigating: coverage zero | 0.00 |
| `citation_fabricator` | Right answer, cites tool-call IDs that never existed | Citation validity | 0.00 |
| `exemption_claimer` | Right answer, always claims a 10b5-1 exemption | Unsupported exemption; correct only where scenario 05 really is 10b5-1 | ≈ 0.10 |
| `tool_spammer` | Calls tools until the budget ends | Budget handling and the efficiency penalty | −0.50 |

The "expected mean" column is arithmetic from the outcome table (for example `always_flag` = (4 flag correct + 4 clear→flag × −0.25 + 2 escalate→flag × −0.25) ÷ 10 = 0.25) and must be replaced by the actual recorded values after the first run.

**R4 — gate (`run_rl.py`, wired into `make eval`).**
- Reference mean must equal 1.00 and every episode must terminate by `submit`.
- Every other policy's mean must be ≤ reference − 0.5.
- No observation contains a scenario id or name (leakage).
- Any failure exits non-zero. Use the shared `run_eval_cli` shell from `zarreh_agentkit.evals` as `evals/run.py` does, with one `EvalOutcome` per (policy, check). The Makefile `eval` target runs the existing canonical eval and then the RL gate, so CI (`make eval` in `.github/workflows/ci.yml`) enforces both with no workflow change.
- Writes `frontend/src/generated/rl-policies.json` (policy, mean, per-scenario scores, outcome-only mean, trajectory-aware mean, n, scorer = "scripted stand-in", run date). Deterministic content only (no latency), so a CI step can fail on regeneration drift, as `make docs-assets` already does.

**R5 — tests and configuration.**
- `tests/evals/test_rl_env.py`:
  - `gymnasium.utils.env_checker.check_env` passes;
  - `reset` with the same seed and scenario is deterministic;
  - leakage test (no scenario id or name anywhere in any observation or `info`);
  - one unit test per reward component, and the "penalties are never scaled" regression;
  - budget truncation returns −0.5.
- `tests/graph/test_trajectory_audit.py` (from Phase P).
- `pyproject.toml`: add `gymnasium` to the `dev` extra; add `gymnasium` to the existing forbidden-imports contract (`dspy`, `deepeval`), renaming it "no DSPy, DeepEval or gymnasium outside evals/optimize".
- mypy `files` already includes `evals`; keep `strict`.

**R6 — documentation.**
- `docs/evidence/rl-environment.md` (a page in the Evidence section) following the §9.5 case-study structure.
- ADRs `D-A2-7` (process audit is the reward's trajectory component) and `D-A2-8` (reward design), plus index entries.
- `docs/generate_plots.py`: a chart per policy of *outcome-only score* against *trajectory-aware score*, light and dark, generated from the committed JSON.
- `mkdocs.yml` nav entry; link from `docs/evidence/evaluation.md`.
- README: replace "deterministic claim verification" wording with the exact statement that each claim's support is judged by an LLM while the process audit and the reward are deterministic.

**R7 — optional live run (needs an OpenAI key).**
- Run the real compiled graph on the ten scenarios with a live model, score each published finding with the same `compute_reward` offline (no adapter needed: the audit already runs on the real transcript), and publish n=10, model version, cost and run date. State that n=10 supports no precision claim.
- Not gated in CI. Clearly labelled "live model, not gated" per the §9.5 honesty rule.

### 13.4 What each gaming policy shows (for the case study)

| Policy | Naive scoring says | Reward says | Product behaviour it protects |
|---|---|---|---|
| `always_flag` | 100% flag recall | +0.25, far below the reference | Alert fatigue: analysts drown in false positives |
| `no_evidence_guesser` | Correct on every case | 0.00 | The finding must rest on gathered evidence, not on a lucky guess |
| `citation_fabricator` | Correct on every case | 0.00 | Every assertion traces to a retrieved fact |
| `exemption_claimer` | Mostly correct | ≈ 0.10 | A 10b5-1 narrative must be backed by the filing's own flag |
| `tool_spammer` | n/a | −0.50 | The per-investigation cost guardrail |

### 13.5 Phase U — UI and deployment readiness

Follows `cohort_risk_lab/UI-ENHANCEMENT-GUIDE.md`; reference implementation is `clinical_care_navigator/frontend/src` (A3).

**U1 — readiness review and fixes.**
- **Unknown accession returns 202 then fails in the background.** `POST /investigations` (`src/surveillance/api/routes/investigations.py`) must look the accession up in `FactStore` first and return 404 with an actionable `detail`. The frontend surfaces `detail`. Route test: unknown accession → 404 and no run row created.
- **Double start.** The run store creates a run per POST; confirm whether two POSTs for the same accession are acceptable. If they are not, add an atomic claim (one conditional UPDATE, `rowcount == 1`, 409 on the loser). Record the decision in an ADR line.
- **Missing deployment files.** Add `compose.prod.yaml`, `.dockerignore` (exclude data, `.env`, `reference/`), a frontend `Dockerfile` with `ARG`/`ENV NEXT_PUBLIC_DOCS_URL`, and `docs/deploy.md` (Caddy basic auth example, the proxy overwriting `X-Forwarded-For`, no host ports published, env values, rebuild steps). Copy and adapt A3's versions.
- Run the guide's Part A checklist (quality gates, container, network, auth, config, data, concurrency, failure visibility, repo hygiene) and record findings by severity in `docs/HARVEST.md`.
- Failure visibility: a background-task failure must reach the UI as a run `error`, not only the server log (the run store already has `error`; confirm the UI renders it).

**U2 — visual foundation.**
- Copy `components/ui/` from A3 (`AppHeader`, `AppFooter`, `PageHeader`, `Card`, `Badge` / `StatusBadge`, `Callout`, `InfoTip`, `Meter`). Add `lucide-react`, `lib/docs.ts` and `lib/glossary.ts`. Remove any global font override; add dark mode (`prefers-color-scheme`, `dark:` variants). Verify each icon name exists in the installed `lucide-react` version.
- `PrototypeBanner` becomes a `Callout`; keep the "research prototype, not a supervisory system of record" text on every page.
- Glossary terms (one sentence each): Form 4, 10b5-1 plan, blackout window, rolling 90-day limit, grounding, claim, exculpatory factor, process audit, disposition (clear / flag / escalate), severity, and the three `reported_under_10b5_1` states (true / false / unknown — "unknown" means *not established*, never "no plan").

**U3 — pages.**

| Page | Contents |
|---|---|
| **Home** (`app/page.tsx`) | Hero (one-sentence purpose, two buttons); numbered "How it works" strip with an owner per step: Plan (AI) → Check plan (code) → Investigate (AI + read-only tools) → Draft and extract claims (AI) → Grounding check (AI judge, code totals) → Publish and audit (code). A **preloaded example** run on first paint. Docs links. `RunConsole` below |
| **Investigation** (inside `RunConsole`, or `app/investigations/[id]`) | Status stepper; progress timeline with plain-language labels and the raw node name beneath; finding card (disposition and severity badges, rules cited, exculpatory factors, the 10b5-1 state explained in a tooltip); claims check in the style of A3's `ClaimsCheck`; the **Process audit** panel (§ below); restyled `ValidatorStrip`; `CostMeter`; replay stored events after a reload |
| **`/evaluation`** (new) | "How we know the investigator isn't cutting corners." Key-finding card; the policy table and the outcome-only vs trajectory-aware chart, both read from `frontend/src/generated/rl-policies.json`; callouts disclosing real SEC data, synthetic firm policy, and that scores come from the scripted stand-in, not a live model; links to `docs/evidence/rl-environment.md` and the ADRs |

*Process audit panel.* Four rows: required evidence gathered (n of 6, with the missing ones named), transaction details first, citations all real, exemptions all supported — each a badge with a one-line explanation and an `InfoTip`. Never shows a bare score.

**U4 — verification (from the guide's Part B6).**
1. `npx tsc --noEmit` and `npm run build`.
2. Update `e2e/investigation.spec.ts` for the new structure, add an evaluation-page spec, scope navigation selectors to `getByRole("navigation", { name: "Main" })`.
3. Extend `e2e/capture-screenshots.spec.ts` to capture every page and state (home, loading, running, success with process audit, error, empty, evaluation) in light **and** dark; zero console errors.
4. Start the real API and `next dev`; run one real end-to-end investigation; reload and confirm results persist.
5. Regenerate docs screenshots (`make docs-screenshots`) and confirm no drift in `make docs-assets`.
6. Update `docs/run-it-yourself.md` and `docs/deploy.md` for the new env vars.

**Gotchas from the guide to apply.** Format dates deterministically (no `toLocaleString()` in server components); wrap mixed text and links in one `<span>` inside flex rows; scope e2e selectors when a header adds a second nav; state that lived only in the SSE stream must be replayed from stored events for finished runs.

### 13.6 Files touched or added

```
src/surveillance/graph/trajectory_audit.py      NEW  (Phase P)
src/surveillance/graph/nodes/publish.py         EDIT attach ProcessAudit
src/surveillance/schemas/finding.py             EDIT ProcessAudit, PublishedFinding.process_audit
src/surveillance/api/routes/investigations.py   EDIT 404 on unknown accession (Phase U1)
evals/oracle.py                                 EDIT expose public decide()
evals/rl_env.py · rl_policies.py · run_rl.py    NEW  (Phase R)
frontend/src/generated/rl-policies.json         NEW  generated, committed
frontend/src/components/ui/*                    NEW  copied from A3
frontend/src/lib/docs.ts · glossary.ts          NEW
frontend/src/app/{page,layout,evaluation/page}.tsx  EDIT/NEW
frontend/Dockerfile · .dockerignore · compose.prod.yaml · docs/deploy.md   NEW
tests/graph/test_trajectory_audit.py · tests/evals/test_rl_env.py          NEW
docs/evidence/rl-environment.md · ADRs D-A2-7..D-A2-9 · generate_plots.py  NEW/EDIT
Makefile (eval runs both gates) · pyproject.toml (gymnasium dev + contract) EDIT
```

### 13.7 Case study outline (§9.5 structure)

- **Problem.** An insider-trading investigator can look right while cutting corners: skipping evidence, citing things it never retrieved, or asserting a 10b5-1 exemption the filing does not support. Wrong dispositions have asymmetric costs (missed violation versus alert fatigue). Regulatory frame: SEC Rule 10b-5, Section 16(a), Rule 10b5-1, FINRA 3110.
- **Verification.** Deterministic: plan check, exculpatory-factor derivation, claim and grounding totals, process audit. Model-judged: per-claim support (LLM grounding judge). State this split explicitly.
- **Gate.** `make eval` in CI: canonical disposition match (n=10) **and** the RL gate (reference = 1.00; seven gaming policies ≤ reference − 0.5; no leakage). Scorer is the scripted stand-in; no live-model number is gated.
- **Lessons learned.** (1) Outcome-only scoring rewards `always_flag`. (2) Scaling penalties by the trajectory score makes skipping evidence the best strategy when unsure. (3) Harness-building already exposed two scenarios that were trivially passable (see `docs/evidence/evaluation.md`); the RL gate is the same discipline applied to the reward. (4) Add whatever the implementation discovers.

### 13.8 Acceptance criteria

1. `process_audit` is present on every published finding, record-only, and `published == judged draft` still holds.
2. `check_env` passes; same seed + scenario gives identical observations; no observation or `info` contains a scenario id or name.
3. Reference policy scores 1.00 on all ten scenarios; every gaming policy is ≤ reference − 0.5; mutation checks (scale penalties by `P`; drop the fabricated-ID check) each make `make eval` fail.
4. Unknown accession → 404 with `detail`, no run created; the UI shows the message.
5. Every page and state captured in light and dark with zero console errors; one real end-to-end run persists across a reload.
6. Every published number on the new pages states n, label source, scorer, model version (or "n/a, stand-in"), run date and uncertainty.
7. `make lint`, `make typecheck`, `make imports`, `make test`, `make eval`, `uv run mkdocs build --strict`, `npm run build`, Playwright all green; `make docs-assets` produces no diff.

### 13.9 Order, dependencies, and out of scope

Order: **P → R1–R6 → U1–U4 → R7 (optional)**. U1 (readiness fixes and deployment files) is independent and can run alongside P or R. U3's investigation page needs P (for the audit panel); the `/evaluation` page needs R4 (for the JSON).

**Out of scope for this upgrade:** a seeded scenario-variant generator; running the full graph's plan and judge nodes inside the environment; Layer 2 hand-labelled evaluation (still needs labelling effort); the `pro` tier; live public deployment (infrastructure access).

**Risks.**

| Risk | Mitigation |
|---|---|
| The RL layer reads as the product | Every RL artefact is written in terms of a product behaviour (§13.4); the home page and README lead with the surveillance product |
| `Text` space limits break `check_env` | Explicit charset and `max_length` (R1) |
| Process audit changes the judged draft | Record-only; regression test on published == judged draft |
| Gate margins set from guesses | Record actual means on the first run, then set the 0.5 margin as a floor and keep it |
| Copying `ui/` creates a third copy | Portfolio decision D20; record as extraction debt in `docs/HARVEST.md` either way |

---

## Appendix A — Course compliance DB schema (reference only)

Reproduced for shape. **Values must be regenerated by
`data/generate_compliance_db.py`, not copied.**

```sql
CREATE TABLE role_limits (
    role_type             TEXT PRIMARY KEY,
    authorization_level   TEXT NOT NULL,
    single_trade_limit    INTEGER NOT NULL,
    quarterly_limit       INTEGER NOT NULL,
    blackout_restrictions TEXT NOT NULL,
    CONSTRAINT valid_auth_level CHECK (
        authorization_level IN ('Executive','Senior','Board','Major Shareholder','Standard')),
    CONSTRAINT valid_blackout CHECK (
        blackout_restrictions IN ('High','Medium','Low'))
);

CREATE TABLE compliance_rules (
    rule_id         TEXT PRIMARY KEY,
    rule_name       TEXT NOT NULL,
    threshold_value INTEGER,
    rule_type       TEXT NOT NULL,
    severity        TEXT NOT NULL,
    description     TEXT,
    CONSTRAINT valid_severity CHECK (
        severity IN ('Critical','High','Medium','Low'))
);
```

18 `role_limits` rows keyed on free-text titles (`CEO`, `Chief Executive Officer`,
`CFO`, `VP`, `SVP`, `EVP`, `General Counsel`, `Director`, `Default`, …) and 6
`compliance_rules` rows (`single_limit`, `quarterly_limit`, `pattern`, `timing`,
`volume_spike`).

Two design corrections for the regenerated version:

- Key `role_limits` on `(relationship, authorization_level)` rather than free-text
  titles, with titles as an alias table. Eighteen near-duplicate rows exist only
  because the source matched on strings.
- Add rules the source lacks: **late Section 16(a) filing**, **10b5-1 plan
  exemption**, and **transaction-code exemptions** for `F` and `M`.
