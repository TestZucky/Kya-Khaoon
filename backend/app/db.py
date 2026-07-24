from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

# Postgres is the only supported database — dev, test and prod all run the same
# engine in a container, so there is no dialect branch here.
#
# pool_pre_ping: containers get restarted and Postgres drops idle connections.
# Without it the first request after that borrows a dead socket and fails; with
# it SQLAlchemy checks the connection and transparently reconnects.
engine = create_engine(settings.database_url, pool_pre_ping=True)


def init_db() -> None:
    """Create tables directly. Test/seed convenience — the app uses Alembic."""
    import app.models  # noqa: F401  (register tables on the metadata)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
