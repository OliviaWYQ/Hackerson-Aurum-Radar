"""Create all database tables (architecture.md §8).

MVP approach — ``Base.metadata.create_all``. Once the schema stabilises this
should move to Alembic migrations (architecture.md §9 ``alembic/``).

Usage:
    python -m app.database.init_db
"""
from loguru import logger

import app.models  # noqa: F401 - registers every model on Base.metadata
from app.database.session import Base, engine


def init_db() -> None:
    """Create any tables that do not yet exist. Idempotent."""
    Base.metadata.create_all(bind=engine)
    tables = ", ".join(sorted(Base.metadata.tables))
    logger.info(f"Database tables ready: {tables}")


if __name__ == "__main__":
    init_db()
