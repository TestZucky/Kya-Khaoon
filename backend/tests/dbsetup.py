"""
Postgres test-database setup. Import and call `use_test_db()` at the TOP of a
test module, before anything imports app.db — the engine binds to
settings.database_url at import time, so a later change strands writes on the
wrong database.

Replaces the old per-module SQLite file. Postgres is shared and persistent, so
isolation comes from `fresh_db()` dropping and recreating the schema rather than
from a file that gets deleted afterwards.
"""

import os

# Points at the compose `db` service. Overridable so the same suite runs against
# CI's service container or a local Postgres.
DEFAULT_TEST_DB = "postgresql+psycopg://kya:kya@db:5432/kya_khaoon_test"


def use_test_db() -> str:
    """Pin DATABASE_URL to the test database and make sure that database exists."""
    url = os.environ.setdefault(
        "DATABASE_URL", os.environ.get("TEST_DATABASE_URL") or DEFAULT_TEST_DB
    )
    # Guard against a test run pointing at the dev database and wiping it —
    # fresh_db() drops every table.
    if not url.rstrip("/").endswith("_test"):
        raise RuntimeError(
            f"refusing to run tests against {url!r}: the database name must end "
            "in '_test' (fresh_db() drops all tables)"
        )
    _ensure_database(url)
    return url


def _ensure_database(url: str) -> None:
    """CREATE DATABASE if it isn't there yet.

    Postgres has no CREATE DATABASE IF NOT EXISTS, and it can't run inside a
    transaction — hence autocommit on the `postgres` maintenance database.
    """
    import psycopg
    from sqlalchemy.engine import make_url

    target = make_url(url)
    admin = target.set(database="postgres")
    dsn = (
        f"host={admin.host} port={admin.port or 5432} dbname=postgres "
        f"user={admin.username} password={admin.password}"
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (target.database,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{target.database}"')


def fresh_db() -> None:
    """Drop every table and rebuild it — the per-module clean slate.

    Stands in for the old `init_db()` calls. Those were enough when each module
    owned a private SQLite file; on a shared database the previous module's rows
    would leak in, so this drops first.
    """
    import app.models  # noqa: F401  (register tables on the metadata)
    from sqlmodel import SQLModel

    from app.db import engine

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
