"""Optional SQLAlchemy adapter scaffold for future production database migration.

The current application models intentionally use the stable sqlite3 adapter.
This module centralizes SQLAlchemy engine/session setup so a future migration
to PostgreSQL or MySQL can replace model internals without changing routes.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from config import DATABASE_URL


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy ORM models."""


engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))


def get_session():
    """Return a SQLAlchemy session for future repository code."""
    return SessionLocal()


def create_all_tables() -> None:
    """Create SQLAlchemy-managed tables after ORM models are added."""
    Base.metadata.create_all(bind=engine)
