"""
SQLAlchemy engine/session setup. Swappable between SQLite (default,
for local dev) and Postgres via DATABASE_URL -- e.g. Render's free
Postgres, whose connection string is the intended production target.

Render (and Heroku before it) hand out connection strings starting
with "postgres://", but SQLAlchemy 1.4+ requires the "postgresql://"
prefix and will raise on the old form -- normalize it here so pasting
the platform's connection string straight into DATABASE_URL just works.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

_database_url = settings.database_url
if _database_url.startswith("postgres://"):
    _database_url = _database_url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if _database_url.startswith("sqlite") else {}

engine = create_engine(_database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import db_models  # noqa: F401  (ensure models are registered)
    Base.metadata.create_all(bind=engine)