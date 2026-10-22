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
    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


@lru_cache
def get_engine() -> Engine:
    return create_engine(_database_url(), pool_pre_ping=True)


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
