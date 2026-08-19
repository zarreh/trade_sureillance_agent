# A2 — Trade Surveillance Agent

> Insider-trading surveillance that has to show its work.

Portfolio app **A2** (`PORTFOLIO_PLAN_V3.md` §7). Finance / RegTech, Pillar 1 —
Regulated Decision Automation. Target URL: `surveillance.zarreh.ai` (not yet
deployed publicly — see Status below).

Takes a real SEC Form 4 filing and runs an investigation: plans which evidence
it needs, gathers it from the insider's real trading history and a seeded
firm-policy database, drafts a conclusion, decomposes that draft into claims
and checks each one against the evidence actually gathered, and only then
publishes — **clear / flag / escalate** — with every assertion traceable to a
retrieved fact.

The centrepiece is the **grounding loop**: the draft is judged before
publication, not after, and a failed check returns the investigation to
gather more evidence rather than silently rewriting the answer. See
[docs/how-it-works/grounding.md](docs/how-it-works/grounding.md).

## Status

**The `base` build (docs/PLAN.md phases 0–8) is complete.** Full pipeline —
plan → check_plan → investigate ⇄ tools → draft_finding → extract_claims →
judge_grounding → publish — with a FastAPI + SSE API, a persisted run store,
a Next.js frontend, a canonical evaluation harness gating pull requests, and
a documentation site. Quality gates (ruff, mypy --strict, import-linter,
pytest, `make eval`, mkdocs --strict, Playwright) are green on every commit;
see CI/CD status via GitHub Actions on this repo.

**Not done, deliberately deferred** (see
[docs/architecture/decisions/](docs/architecture/decisions/index.md) and
`docs/PLAN.md` §7 Stretch for the reasoning on each):

- Live public deployment (`surveillance.zarreh.ai` DNS/VPS) — infrastructure
  access not available while building this.
- Cross-provider model support (Gemini availability fallback, Ollama offline
  profile) — single-provider (OpenAI) only ships in base; see D-A2-4.
- Layer 2 stratified evaluation (150–300 hand-labelled cases, published
  precision/recall with a confidence interval) — needs a live LLM and real
  human labelling effort; see `docs/evidence/evaluation.md`. The harness for
  it (`evals/metrics.py`) is ready.
- The `pro` tier (alert triage queue, investigation replay, MCP export,
  Postgres/Langfuse) — gated on base being deployed and Layer 2 existing,
  per `docs/PLAN.md`.
- The shared portfolio-wide site (`/writing`, `/methodology`, the per-app
  card grid) doesn't exist yet outside this repo; draft content for this
  app's card and its `/writing` post are staged in `docs/` pending it.

This is a research prototype built on public SEC data plus synthetic firm
policy. It is **not** a supervisory system of record, and not legal or
compliance advice — see [docs/regulatory-basis.md](docs/regulatory-basis.md).

## Running it

See [docs/run-it-yourself.md](docs/run-it-yourself.md) for the full
quickstart (backend, dataset, frontend, and the evaluation harness).

```bash
uv sync --extra dev
cp .env.example .env   # fill in your own OpenAI API key
make test
make dev               # http://localhost:8000/healthz
```

## Layout

| Path | Purpose |
|---|---|
| `docs/` | MkDocs + Material site — architecture, ADRs, evidence, regulatory basis |
| `docs/PLAN.md` | The build plan — phases, architecture, decisions, risks (historical planning record) |
| `src/surveillance/` | The application — `api/`, `graph/`, `tools/`, `store/`, `schemas/`, `prompts/` |
| `data/` | Data-build scripts (SEC EDGAR fetch, fact/policy store builders, canonical scenarios) |
| `evals/` | Layer 1 canonical evaluation harness (`make eval`) |
| `frontend/` | Next.js UI |
| `tests/` | Backend test suite |
| `reference/` | Local-only source material. **Gitignored**, never published |
