.PHONY: dev test lint typecheck imports eval up down data docs docs-assets docs-screenshots

dev:
	uv run uvicorn surveillance.api.main:app --reload --port 8000

test:
	uv run pytest -v

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck:
	uv run mypy

imports:
	PYTHONPATH=src uv run lint-imports

eval:
	uv run python -m evals.run

up:
	docker compose up --build

down:
	docker compose down

data:
	uv run python -m data.fetch_edgar
	uv run python -m data.build_store
	uv run python -m data.generate_compliance_db
	uv run python -m data.scenarios

docs:
	uv run mkdocs serve

docs-assets:
	uv run python docs/generate_plots.py

docs-screenshots:
	uv run python -m tests.e2e.capture_screenshots
