# PLAN v5: analyst case queue, grounded follow-up chat, amber dark theme, visible RL verifier

> **Superseded in part (2026-11-01).** After review, v5 shipped the citation fix,
> the case-review queue with analyst decisions, the theme and the live results on
> `/evaluation`. Chat (B, D, G4) and G3 moved to v6. What shipped and why is in
> `docs/PLAN.md` §14.

Status: **approved, not started** (2026-11-01). This is a self-contained handoff. A new session
should read it top to bottom, then `docs/PLAN.md` §13 for the RL background.

## Context for a fresh session

- Repo: `zarreh/trade_sureillance_agent`. An insider-trading surveillance agent over real SEC
  EDGAR Form 4 data plus a synthetic firm-policy DB. LangGraph investigation:
  plan → check_plan → investigate (6 read-only tools) → draft_finding → extract_claims →
  judge_grounding → publish. Every published finding carries a grounding report and a
  deterministic `ProcessAudit`.
- Backend: Python 3.12, `uv`, FastAPI (`src/surveillance/api`), SQLite stores
  (`FactStore` facts.db, `PolicyStore` policy.db, `RunStore` data/runs.db), models
  `gpt-4o-mini` (fast) / `gpt-4o` (reasoning) in `src/surveillance/graph/policies.py`.
- Frontend: Next.js 16 + React 19 + Tailwind v4 in `frontend/`. **Read
  `frontend/node_modules/next/dist/docs` before writing Next code** (see `frontend/AGENTS.md`).
  API types are generated from OpenAPI (`make frontend-types`), never hand-written.
- RL (already built, see `docs/evidence/rl-environment.md`): `evals/rl_env.py` (Gymnasium
  `SurveillanceEnv`, `compute_reward`), `evals/rl_policies.py` (reference + 8 scripted
  policies), `evals/run_rl.py` (CI gate, writes `frontend/src/generated/rl-policies.json`).
  The reward is outcome × trajectory − penalties, and the LLM judge is excluded. No training, by decision.
- Rules to keep:
  - The import-linter layers `api → graph → tools → schemas` hold.
  - `surveillance` must never import gymnasium/dspy/deepeval.
  - Tools never import graph.
  - `graph/builder.py` is the only module that wires graph nodes.
  - Generated JSON in `frontend/src/generated/` is drift-checked in CI.
  - Labels (expected dispositions) never enter model context.
- Commands:
  - `make data` builds facts.db/policy.db plus scenarios;
  - `make run` starts the API on :8000 and Next on :3000;
  - `make check` runs lint, mypy, import rules, pytest and eval (canonical + RL gate);
  - `make frontend-types`, `make frontend-e2e` (Playwright, mocked backend), `make docs-screenshots`;
  - `make eval-live` costs real money and is not gated.
- Known: a narrow Pydantic `parsed`-field serializer warning filter lives in `graph/policies.py`
  (an upstream langchain-openai streaming bug).


## Review of the suggestions

| Idea | Verdict | Caveat that shapes the design |
|---|---|---|
| Follow-up chat on a run | Yes | The project's core claim is "nothing published without evidence". A plain chat would undercut it, so chat answers go through the **same claim extractor and grounding judge**, and their tool calls are audited and budget-capped. |
| Analyst case queue (table + AI suggestion + re-run / ask) | Yes, build first | The real EDGAR load has thousands of filings. Scope: **10 canonical scenarios + any accession that has been investigated**. Analyst **Accept / Override + note** is record-only. It never changes the AI finding or feeds the evals. |
| Distinctive dark theme | Yes | Today: stock Tailwind `sky`/`slate`, ~150 hard-coded `dark:` classes, follows the OS only. Move to **semantic colour tokens**, **dark by default with a light toggle**, **amber/gold accent**, monospace ids. |

Chosen scope: queue = scenarios + investigated runs. Analyst decision persisted. Chat can call the 6 read-only tools, is grounding-checked, and streams over SSE. Dark by default with a toggle. Amber accent.

## Current state (relevant facts)

- API: `POST /investigations`, `GET /investigations/{id}`, `GET /investigations/{id}/events` (SSE). No listing.
- `RunStore` (`data/runs.db`): `runs(id, accession_number, status, created_at, updated_at, finding_kind, finding_json, error)` plus event and cost logs.
- `FactStore`: `get_transaction`, `transactions_for_accession`, `transactions_in_window`, `history_for_insider`. No listing.
- Graph reuse points:
  - chains: `build_claim_extractor_chain`, `build_grounding_judge_chain`, `build_investigator`;
  - helpers: `extract_tool_call_records`, `zarreh_agentkit.guardrails.grounding`, `graph/trajectory_audit.py`, cost tracking.
- Import-linter layers: `api -> graph -> tools -> schemas`. Tools never import graph. Gymnasium stays out of `surveillance`.
- Frontend: Next 16 (read `node_modules/next/dist/docs` before coding, per `frontend/AGENTS.md`), Tailwind v4, types generated from OpenAPI (`make frontend-types`).
  - Sample cases are static from `frontend/src/generated/cases.json`.
  - The live run is on `/investigate?run=<id>`.

## Design

### A. Backend: case queue and analyst decisions
- `FactStore.filing_summaries(accessions)`: issuer, insider, role, trade date, code, shares, value, for the table rows.
- `FactStore.scenario_accessions()`: accessions with the `SCENARIO-` prefix (no import of `data/`).
- `RunStore`:
  - `latest_runs_by_accession()` and `list_runs(accession)`;
  - new table `analyst_decisions(accession_number PK, run_id, decision: accept|override, override_disposition, note, updated_at)`.
- Endpoints (new router `api/routes/cases.py`):
  - `GET /cases`: one row per accession. Columns: filing summary, latest run (id, status, disposition, confidence, severity, `process_audit.trajectory_score`, unsupported claims, cost, updated_at), analyst decision, expected disposition = null (labels stay out of the API).
  - `PUT /cases/{accession}/decision`: validated body. Rejects `override` without `override_disposition`. 404 for an unknown accession.
  - Re-run reuses `POST /investigations`.
- Rate limits and body caps as on the existing routes.

### B. Backend: grounded follow-up chat
- New table `chat_turns(id, run_id, turn, role, content, tool_calls_json, grounding_json, cost_usd, created_at)`.
- New small graph `build_follow_up_graph(settings)` in `graph/` (the builder stays the only wiring module):
  1. `answer`: fast model bound to the same 6 tools. Seeded with:
     - a system prompt `prompts/follow_up_v1.md`: answer only about this filing, cite tool-call ids, say "not in the evidence" rather than guess, refuse advice outside surveillance;
     - the stored finding, the run's evidence records, and prior turns.
  2. `tools` (ToolNode) loop with a **per-question cap** (for example 4 tool calls) and a cost cap via the existing budget helper.
  3. `extract_claims` → `judge_grounding`: reuse both chains. Evidence = the stored run's records + this turn's new tool results.
  4. Unlike the investigation there is **no retry loop**. Unsupported sentences are returned flagged, not silently rewritten.
- Endpoints:
  - `POST /investigations/{id}/questions` returns SSE events:
    - `token`: answer text, shown as "checking evidence…";
    - `tool_call`: the follow-up fetched new evidence;
    - `grounding`: per-claim supported or unsupported, with cited ids;
    - `done`: cost.
  - `GET /investigations/{id}/questions`: history.
  - 409 if the run isn't completed. Max question length. Max turns per run (for example 20).
- Streaming answer tokens before the judge is the trade-off of picking streaming. The UI shows them as **unverified** until the `grounding` event arrives, then annotates each claim. This is written up in a new ADR.
- Cost entries are logged under node names `follow_up.*` so the cost meter and docs stay honest.

### C. Frontend: case queue
- New route `/queue` ("Case queue"), first item in the nav.
- Dense table:
  - columns: accession (mono), insider / role, issuer, trade date, value, **AI suggestion** (disposition badge + confidence), audit score, unsupported claims, analyst decision, last run;
  - filters: disposition, decision state (pending / accepted / overridden);
  - row actions: **Open**, **Re-run**, **Ask**.
- Clear label: "AI suggestion. The analyst decides."
- Run detail: extend the existing `/investigate?run=<id>` view with an **Analyst decision** card (Accept / Override + disposition + note) and the **Ask** panel.
- Static sample case pages keep working offline. Where a live run exists for that accession, they link to it.

### D. Frontend: follow-up chat panel
- Side panel / drawer on a completed run:
  - message list and input, using the SSE consumer pattern already in `lib/api.ts`;
  - streamed tokens greyed with an "unverified" chip;
  - after grounding, each claim is underlined green (supported, with tool-call-id tooltip) or red (unsupported);
  - new tool calls appear inline as evidence cards (reuse `EvidenceCards`);
  - per-turn cost.
- Disabled with an explanation while the run is still running, or failed.

### E. Theme
- `globals.css`:
  - semantic tokens `--bg`, `--surface`, `--surface-2`, `--border`, `--text`, `--muted`, `--accent` (amber), `--accent-fg`, and disposition tokens (`--flag` red, `--escalate` amber-orange, `--clear` green);
  - exposed through `@theme inline` so classes read `bg-surface text-muted border-border`.
- Tailwind v4 class-based dark: `@custom-variant dark (&:where(.dark, .dark *));`.
  - `<html class="dark">` by default;
  - a tiny inline script in `layout.tsx` applies the stored preference before paint (no flash);
  - a theme toggle in `AppHeader`, persisted in `localStorage`.
- Visual identity, an "ops console":
  - near-black blue-slate background, 1px borders instead of shadows, amber focus rings and active nav;
  - Geist Mono for accessions, ids and numbers, and tabular figures in tables.
- Migrate `components/ui/*` first (Card, Badge, Callout, Meter, PageHeader, AppHeader/Footer), then the remaining components, replacing `sky-*` and hard-coded `slate-*`/`dark:` pairs with tokens.
- Check WCAG AA contrast for the amber-on-dark and badge colours.
- MkDocs site: optionally align `mkdocs.yml` palette accent to amber. Not required.

### F. Tests, types, docs
- Backend tests (fake models, no network):
  - store methods; `GET /cases` and decision validation;
  - chat: grounding applied, tool cap and cost cap enforced, 409 on an unfinished run, out-of-scope refusal path;
  - SSE event order.
- `make imports` must still pass. Chat graph modules sit in `graph/`, the routes in `api/`.
- Live RL/eval gates stay unchanged. Optionally add 2–3 canned follow-up questions to `evals/live_run.py` later (not gated).
- `make frontend-types`; Playwright with a mocked backend:
  - queue renders, filters, accept/override persists, re-run starts a run;
  - chat streams then shows grounding; theme toggle persists;
  - regenerate `make docs-screenshots`.
- Docs:
  - `docs/api.md` (new endpoints) and `docs/run-it-yourself.md` (queue and chat);
  - README feature list; PLAN.md §14 status;
  - ADR **D-A2-10 grounded follow-up chat** and ADR **D-A2-11 analyst decision is record-only**.

### G. RL: make the verifier visible where the product is used

**Objective (PLAN §13, G6):** show AI-evaluation and reward-design skill. The product's checks work as a verifier and a reward that **cannot be gamed**. RL is an extra. Every RL element must be explained as a product behaviour it protects. **No training**, by decision.

**How RL helps today (for the README / evaluation page copy):**
1. *Process audit* on every real run: all 6 tools called, details first, no fabricated citations, no unsupported exemptions. Shown on run pages.
2. *Gaming-proof metric:* outcome-only scoring rewards `always_flag` (100% recall). The reward (outcome × trajectory − penalties, LLM judge excluded) makes 7 shortcut policies score ≥0.5 below the reference, enforced in CI.
3. *Regression guard:* weakening any check fails the gate.
4. *Ready environment* (`SurveillanceEnv`) for future fine-tuning or prompt optimisation. Not used for training.

**What we add (chosen for the objective; each is cheap and reuses existing code):**
- **G1 "Try to cheat" episode replay on `/evaluation`** (highest explanatory value).
  - `evals/run_rl.py` also writes the deterministic step traces per (policy, scenario) to `frontend/src/generated/rl-episodes.json`: action, tool, observation summary, final audit and reward breakdown. It is covered by the existing drift check.
  - The UI picks a strategy and a scenario, steps through the actions, and ends on a breakdown bar: `outcome → × trajectory → − efficiency − invalid = reward`, with the audit item that sank it highlighted (for example "cited id never retrieved").
- **G2 Live model next to the scripted policies on `/evaluation`.**
  - Add the recorded live-model row (from `evals/recordings/live-*`, already scored with `compute_reward`): 4/10 correct, mean -0.03.
  - Add a per-scenario "why it lost" breakdown (for example, the audit scored 0 on five runs because claims cited no tool-call ids).
  - This shows the environment is a *useful ruler* for a real model, not only a self-consistency check. The "not gated" label is kept.
- **G3 Reward on real scenario runs (run view + queue).**
  - After a run on a `SCENARIO-` accession completes, the server computes `compute_reward` from the stored finding, audit and evidence count.
  - Shown as a "Scenario score (demo label)" card with the same breakdown, and as a queue column.
  - The label is never in the model's context and is only revealed post-run. Non-scenario filings show the process audit only (no label exists).
  - Layering: the reward function lives in `evals/` and depends on gymnasium. Move the pure `compute_reward`, the outcome table and `RewardBreakdown` into `src/surveillance/graph/reward.py` (no gymnasium). `evals/rl_env.py` imports it. Import-linter stays green. The expected labels stay in `data/scenarios.py`. The API reads them through a small `ScenarioLabels` lookup that the app factory injects (a `data` import only at the composition root), or a `scenario_labels` table that `make data` writes into `facts.db`. **Choose the table**, which keeps `src/` free of `data/`.
- **G4 Process check on chat answers.** Each follow-up turn reports citation validity (fabricated ids) using the audit's citation check, shown next to the grounding verdict. No reward and no outcome.
- *Not now:* exporting analyst Accept/Override as labelled episodes for future training. The decisions are persisted, so this stays a short follow-up. It is mentioned in the docs as the human-in-the-loop → RL path.

**Copy:** rename the nav item "How we know it works" to keep it, and add one plain-language "What the RL part is for" card at the top of `/evaluation` built from the 4 points above. Update `docs/evidence/rl-environment.md` with G2/G3, and PLAN §14.

## Order and dependencies
1. Theme tokens and toggle (independent, quick visual win).
2. Store and queue API → queue page → analyst decision UI.
3. Chat graph and API → chat panel.
4. RL visibility: move the reward into `src/` + the labels table → reward on scenario runs (queue column, run card). Episode traces + replay UI. Live row on `/evaluation`. Chat citation check (with the chat).
5. Docs, screenshots, final `make check` + `make frontend-e2e`. The RL gate must still pass unchanged.

## Open risks / notes
- Streaming before grounding can briefly show unsupported text. Mitigated by the "unverified" state and a post-hoc per-claim verdict.
- The chat prompt and model mean extra cost per question. The caps keep it bounded, and the cost is shown per turn.
- The queue holds only the 10 scenarios until real filings are investigated. A "Investigate a filing" entry stays for arbitrary accessions.
- Re-running an accession creates a new run. The queue shows the latest. The analyst decision references the run it was made on and is marked "stale" if a newer run exists.

## Task list (ids, dependencies)

| id | task | depends on |
|---|---|---|
| theme-tokens | Amber dark theme tokens, class-based dark variant, no-flash script, header toggle; migrate `components/ui/*` then the rest off `sky`/`slate`; AA contrast | none |
| queue-store | `FactStore.filing_summaries` + `scenario_accessions`; `RunStore.latest_runs_by_accession`, `list_runs`, `analyst_decisions` table; tests | none |
| queue-api | `GET /cases`, `PUT /cases/{accession}/decision` with validation and rate limits; tests; regenerate types | queue-store |
| queue-ui | `/queue` page: dense table, filters, Open / Re-run / Ask, nav entry | queue-api, theme-tokens |
| decision-ui | Accept / Override + disposition + note card on the run view and queue; stale marker | queue-api, queue-ui |
| reward-to-src | Move pure `compute_reward`, `OUTCOME_TABLE`, `RewardBreakdown` to `src/surveillance/graph/reward.py`; `evals/rl_env.py` imports it; `make data` writes a `scenario_labels` table; RL gate output unchanged | none |
| run-reward | Post-run reward for `SCENARIO-` accessions in `GET /investigations/{id}` and `GET /cases`; run-view card + queue column | reward-to-src, queue-api, queue-ui |
| episode-replay | `run_rl.py` writes `rl-episodes.json` (drift-checked); `/evaluation` "Try to cheat" stepper + reward breakdown bar | theme-tokens |
| live-row | Recorded live-model row + per-scenario "why it lost" on `/evaluation`; "What the RL part is for" card | theme-tokens |
| chat-graph | `follow_up_v1` prompt, answer agent with the 6 tools, per-question tool/cost caps, reuse claim extractor + grounding judge, `chat_turns` table, cost logging; fake-model tests | none |
| chat-api | `POST /investigations/{id}/questions` SSE (token, tool_call, grounding, done), `GET` history, 409/limits; tests; types | chat-graph |
| chat-audit | Citation-validity (fabricated ids) per chat turn in the grounding event | chat-api |
| chat-ui | Drawer on a completed run: unverified streamed tokens, per-claim verdicts, inline evidence, per-turn cost | chat-api, chat-audit, queue-ui, theme-tokens |
| docs-tests | `docs/api.md`, `run-it-yourself.md`, README, PLAN §14, ADRs D-A2-10 (grounded chat) / D-A2-11 (record-only analyst decision), RL evidence page; Playwright specs; screenshots; `make check` + `make frontend-e2e` | decision-ui, chat-ui, run-reward, episode-replay, live-row |

## Done when

- `make check` and `make frontend-e2e` pass, and the RL gate numbers are unchanged.
- The queue lists the 10 scenarios plus investigated filings, with AI suggestion, audit, reward
  (scenarios only) and analyst decision. Accept / Override persists.
- Chat answers stream, then show per-claim grounding and citation validity. Caps are enforced.
- The theme is dark by default with amber accent and a working, persisted light toggle.
- `/evaluation` shows the replay, the live-model row and the plain-language RL card.
