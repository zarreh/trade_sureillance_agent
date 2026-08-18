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
the labelled scenarios. See [docs/PLAN.md](https://github.com/PLACEHOLDER/trade-surveillance-agent/blob/main/docs/PLAN.md)
§4 for what this does and why.
