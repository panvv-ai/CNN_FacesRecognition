from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from face_workbench.config import PROJECT_ROOT


def _create_parent_directory(database_url: str) -> None:
    url = make_url(database_url)
    database_name = url.database
    if (
        url.get_backend_name() == "sqlite"
        and isinstance(database_name, str)
        and database_name
        and database_name != ":memory:"
    ):
        Path(database_name).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def upgrade_database(database_url: str) -> None:
    _create_parent_directory(database_url)
    config = Config(str(PROJECT_ROOT / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


class Database:
    def __init__(self, database_url: str) -> None:
        _create_parent_directory(database_url)
        connect_args = {}
        if make_url(database_url).get_backend_name() == "sqlite":
            connect_args = {"check_same_thread": False, "timeout": 30}
        self.engine: Engine = create_engine(
            database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        if make_url(database_url).get_backend_name() == "sqlite":
            event.listen(self.engine, "connect", self._set_sqlite_pragmas)
        self._session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            class_=Session,
        )

    @staticmethod
    def _set_sqlite_pragmas(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        self.engine.dispose()
