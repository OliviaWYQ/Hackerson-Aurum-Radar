"""SQLAlchemy model — daily_briefs (architecture.md §8). Output of stage 6."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class DailyBrief(Base):
    __tablename__ = "daily_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    brief_date: Mapped[date | None] = mapped_column(Date, unique=True, index=True)
    markets: Mapped[list | None] = mapped_column(JSONB)
    executive_summary: Mapped[str | None] = mapped_column(Text)
    opportunities: Mapped[list | None] = mapped_column(JSONB)
    risks: Mapped[list | None] = mapped_column(JSONB)
    watch_items: Mapped[list | None] = mapped_column(JSONB)
    recommended_actions: Mapped[list | None] = mapped_column(JSONB)
    source_count: Mapped[int | None] = mapped_column(Integer)
    event_count: Mapped[int | None] = mapped_column(Integer)

    # escape hatch for fields not yet modelled
    extra: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
