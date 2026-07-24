from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

# check_same_thread and a busy timeout only matter for the SQLite dev/test
# fallback — SQLite has a single writer, so `timeout` makes a second writer wait
# for the lock instead of erroring. Postgres needs neither.
connect_args = (
    {"check_same_thread": False, "timeout": 10}
    if settings.database_url.startswith("sqlite")
    else {}
)
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    """Create tables directly. Dev/test convenience — prod uses Alembic."""
    import app.models  # noqa: F401  (register tables on the metadata)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
