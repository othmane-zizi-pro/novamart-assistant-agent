.PHONY: dev test lint index search

dev:
	uv run uvicorn app.main:app --reload --port 8000

test:
	uv run pytest

index:
	uv run python -m app.indexer

search:
	uv run python -m app.search $(q)

lint:
	uv run ruff check .
