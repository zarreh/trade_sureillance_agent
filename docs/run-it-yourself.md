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

Visit `http://localhost:3000`. The home page opens on a recorded example, so it
shows a full investigation without calling the API. **Run it live** starts a real
one and streams it step by step; its id goes into the URL, so a reload replays
the stored run. A real finding needs the backend running with a real
`SURVEILLANCE_OPENAI_API_KEY`; against a placeholder key the run still streams
but ultimately fails, exercising the error state honestly rather than faking one.
The **How we know it works** page reads `frontend/src/generated/rl-policies.json`.

`NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_DOCS_URL` are baked in at build time.

The generated files in `frontend/src/generated/` (the example run and the RL
results) are written by `make eval` and checked for drift in CI.

Types are generated from the FastAPI OpenAPI schema, never hand-written:

```bash
make frontend-types    # backend schema -> frontend/src/lib/api-types.ts
```

`make frontend-e2e` runs the Playwright smoke test (the recorded example, loading,
success, reload replay, empty, error, a failed audit and the evaluation page)
against a fully mocked backend, with no live LLM, network or Python process.
`make docs-screenshots` captures every page and state in light and dark and fails
on any console error.


An accession that is not in `facts.db` is rejected up front with `404` and an
actionable `detail`; no run is created. Browser calls are allowed from
`SURVEILLANCE_FRONTEND_ORIGINS` (default `http://localhost:3000`; in
`development` any localhost port is also allowed). To put it on a server, see
[Deploy to a server](deploy.md).
