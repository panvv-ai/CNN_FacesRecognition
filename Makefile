.PHONY: setup build serve lint test api-types codegraph-index

setup:
	uv sync --extra dev
	pnpm --dir frontend install

build:
	pnpm --dir frontend build

serve:
	uv run python main.py

lint:
	uv run ruff check src tests scripts main.py *.py
	uv run mypy
	pnpm --dir frontend lint
	pnpm --dir frontend typecheck

test: build
	uv run pytest
	pnpm --dir frontend test:run
	pnpm --dir frontend test:e2e

api-types:
	uv run python scripts/export_openapi.py
	pnpm --dir frontend api:types

codegraph-index:
	@if [ -d .codegraph ]; then codegraph index .; else codegraph init .; fi
