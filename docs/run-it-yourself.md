# Run it yourself

## Prerequisites

- Python 3.12+, [`uv`](https://docs.astral.sh/uv/)
- Docker (for the containerised deployment path)

## Quickstart

```bash
git clone <repo-url>
cd trade_surveillance_agent
uv sync --extra dev
cp .env.example .env  # fill in your own API key
make test
make dev
```

Then visit `http://localhost:8000/healthz`.

## Building the dataset

```bash
make data
```

Fetches SEC EDGAR bulk data, builds the local fact and policy stores, and seeds
the labelled scenarios. See [docs/PLAN.md](https://github.com/zarreh/trade_sureillance_agent/blob/main/docs/PLAN.md)
§4 for what this does and why.

## Investigating a filing

```bash
curl -sX POST localhost:8000/investigations \
  -H 'content-type: application/json' \
  -d '{"accession_number": "0000000001-25-000001"}'
# {"id": "…", "status": "running"}

curl -s localhost:8000/investigations/<id>
curl -sN localhost:8000/investigations/<id>/events   # SSE, node-by-node
```

`GET /investigations/{id}/events` replays every persisted node event from the
start and then tails new ones until the run finishes — reconnecting later
just replays from `RunStore` (`data/runs.db`), no run is lost. Requests are
rate-limited (`SURVEILLANCE_RATE_LIMIT_PER_MINUTE`, default 20/minute) and
request bodies are capped (`SURVEILLANCE_MAX_REQUEST_BODY_BYTES`, default 16KB).

## Case queue and analyst decisions

```bash
curl -s localhost:8000/cases                        # scenarios + investigated filings
curl -s localhost:8000/cases/<accession>            # one row
curl -sX PUT localhost:8000/cases/<accession>/decision \
  -H 'content-type: application/json' \
  -d '{"run_id": "<id>", "decision": "override", "override_disposition": "escalate", "note": "…"}'
```

A decision is tied to the completed run it was made on and becomes *stale* once a
newer run completes. It is record-only: it never changes the finding or feeds the
evaluations ([D-A2-12](architecture/decisions/D-A2-12-case-review-queue.md),
[D-A2-13](architecture/decisions/D-A2-13-analyst-decision-record-only.md)).
Decisions are stored in `data/runs.db` next to the runs.

## Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE, defaults to :8000
npm run dev
```

Visit `http://localhost:3000`. The home page and the ten case pages are built
from `frontend/src/generated/cases.json`, so they show full investigations
without calling the API. **Investigate a filing** (or **Re-run this case live** on
a case page) starts a real run and streams it step by step; its id goes into the
URL, so a reload replays the stored run. A real finding needs the backend running with a real
`SURVEILLANCE_OPENAI_API_KEY`; against a placeholder key the run still streams
but ultimately fails, exercising the error state honestly rather than faking one.
The **Case queue** (`/queue`) lists the scenarios and every investigated filing from
`GET /cases`; open a run to accept or override the AI suggestion. The UI is dark by
default; the header toggle switches to light and is remembered in `localStorage`.
The **How we know it works** page reads `frontend/src/generated/rl-policies.json`
and `frontend/src/generated/live-runs.json`.

`NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_DOCS_URL` are baked in at build time.

The generated files in `frontend/src/generated/` (`cases.json`, the RL
results and `live-runs.json`) are written by `make eval` and checked for drift in CI. `cases.json`
holds each case's reference run plus the latest live recording under
`evals/recordings/`; `make eval-live` (needs an API key) records a new one.

Types are generated from the FastAPI OpenAPI schema, never hand-written:

```bash
make frontend-types    # backend schema -> frontend/src/lib/api-types.ts
```

`make frontend-e2e` runs the Playwright smoke test (the home page, every case page,
loading, success, reload replay, empty, error, a failed audit and the evaluation page)
against a fully mocked backend, with no live LLM, network or Python process.
`make docs-screenshots` captures every page and state in light and dark and fails
on any console error.


An accession that is not in `facts.db` is rejected up front with `404` and an
actionable `detail`; no run is created. Browser calls are allowed from
`SURVEILLANCE_FRONTEND_ORIGINS` (default `http://localhost:3000`; in
`development` any localhost port is also allowed). To put it on a server, see
[Deploy to a server](deploy.md).
