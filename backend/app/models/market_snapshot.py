"""SQLAlchemy model — market_snapshots (architecture.md §8). Output of stage 5."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    market: Mapped[str | None] = mapped_column(String, index=True)
    region: Mapped[str | None] = mapped_column(String)
    snapshot_date: Mapped[date | None] = mapped_column(Date, index=True)
    opportunity_score: Mapped[int | None] = mapped_column(Integer)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    overall_judgement: Mapped[str | None] = mapped_column(Text)
    key_opportunities: Mapped[list | None] = mapped_column(JSONB)
    key_risks: Mapped[list | None] = mapped_column(JSONB)
    watch_items: Mapped[list | None] = mapped_column(JSONB)
    event_count: Mapped[int | None] = mapped_column(Integer)

    # escape hatch for fields not yet modelled
    extra: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
