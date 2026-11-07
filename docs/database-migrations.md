# Database Migrations

Face Workbench uses SQLAlchemy with Alembic. The default database is
`storage/face_workbench.sqlite3`.

```bash
uv run python main.py db-upgrade
uv run alembic -c migrations/alembic.ini revision --autogenerate -m "describe the schema change"
```

Review generated migrations before committing. SQLite schema changes that alter
columns must remain compatible with Alembic batch mode.

Override the database location with:

```bash
FACE_WORKBENCH_DATABASE_URL=sqlite+pysqlite:///./path/to/workbench.sqlite3 \
  uv run python main.py db-upgrade
```

MySQL is not part of the v1 runtime or test matrix. The SQLAlchemy models avoid
SQLite-only column types so a future deployment can evaluate a MySQL adapter.
