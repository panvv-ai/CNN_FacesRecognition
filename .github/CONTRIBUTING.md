# Contributing

## Development setup

```bash
uv sync --extra dev
pnpm --dir frontend install
pnpm --dir frontend build
uv run python main.py
```

Use Python 3.11 and Node.js 22 or newer.

## Before opening a pull request

```bash
uv run ruff check src tests scripts main.py
uv run pytest
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test:run
pnpm --dir frontend test:e2e
pnpm --dir frontend build
```

New behavior requires tests. Database changes require an Alembic migration and a
migration test. API changes require regenerating `docs/api/openapi.json` and
`frontend/src/api/schema.ts`.

Do not commit personal face images, model weights, uploaded media, recognition
outputs, local SQLite files, or the `.codegraph/` index.

## Pull requests

Keep changes focused, describe user-visible behavior, list verification commands,
and call out privacy or compatibility implications.
