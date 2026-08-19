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

## Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE, defaults to :8000
npm run dev
```

Visit `http://localhost:3000` — the page starts a real investigation the
moment it loads (no typing required) and streams it node-by-node via
`RunConsole`, `TraceTimeline`, `ValidatorStrip`, `EvidencePanel` and
`CostMeter`. Requires the backend running with a real `SURVEILLANCE_OPENAI_API_KEY`
to produce a genuine finding; against a placeholder key the run still streams
but ultimately fails, exercising the error state honestly rather than faking one.

Types are generated from the FastAPI OpenAPI schema, never hand-written:

```bash
make frontend-types    # backend schema -> frontend/src/lib/api-types.ts
```

`make frontend-e2e` runs the Playwright smoke test covering all four UI
states (loading, success, empty, error) against a fully mocked backend — no
live LLM, network, or Python process required.


`GET /investigations/{id}/events` replays every persisted node event from the
start and then tails new ones until the run finishes — reconnecting later
just replays from `RunStore` (`data/runs.db`), no run is lost. Requests are
rate-limited (`SURVEILLANCE_RATE_LIMIT_PER_MINUTE`, default 20/minute) and
request bodies are capped (`SURVEILLANCE_MAX_REQUEST_BODY_BYTES`, default 16KB).

