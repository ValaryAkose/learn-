import os
from collections.abc import Iterator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()


class Base(DeclarativeBase):
    pass


def _database_url() -> str:

    url = os.environ.get("DATABASE_URL")

    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


@lru_cache
def get_engine() -> Engine:
    url = _database_url()

    # If using an in-memory or file-based SQLite database, disable the same-thread check
    if url.startswith("sqlite"):
        return create_engine(
            url, pool_pre_ping=True, connect_args={"check_same_thread": False}
        )

    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Iterator[Session]:
    db = get_session_factory()()

    try:
        yield db
    finally:
        db.close()
