"""SQLAlchemy model — districts (architecture.md §8). Seed data, not in the pipeline."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    market: Mapped[str | None] = mapped_column(String, index=True)
    name: Mapped[str | None] = mapped_column(String)
    store_count: Mapped[int | None] = mapped_column(Integer)
    heat_level: Mapped[str | None] = mapped_column(String)
    profile: Mapped[dict | None] = mapped_column(JSONB)

    # escape hatch for fields not yet modelled
    extra: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
