"""
Database configuration and session management.

Uses SQLite by default, PostgreSQL-ready via connection string.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# Resolve SQLite path to absolute to avoid CWD issues with TestClient
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    db_path = db_url.replace("sqlite:///", "")
    db_url = f"sqlite:///{os.path.abspath(db_path)}"

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if settings.IS_SQLITE else {},
    pool_pre_ping=True,
)

# SQLite WAL mode for better concurrent read performance
if settings.IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once at startup."""
    # Import models to register them with Base.metadata
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
