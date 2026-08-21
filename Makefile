.PHONY: dev test lint index search chat ui eval

dev:
	uv run uvicorn app.main:app --reload --port 8000

test:
	uv run pytest

index:
	uv run python -m app.indexer

chat:
	uv run python -m app.cli

search:
	uv run python -m app.search $(q)

lint:
	uv run ruff check .

ui:
	cd frontend && npm run dev

eval:
	uv run python -m eval.run
