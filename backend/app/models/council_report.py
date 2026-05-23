"""SQLAlchemy model — council_reports (architecture.md §8 / §17.7).

Persists the strategic intelligence council's decision report so the API can
serve it without re-running the council (~6 LLM calls per market). One row per
market per run; the latest row (highest id) is the current report.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class CouncilReport(Base):
    __tablename__ = "council_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    market: Mapped[str | None] = mapped_column(String, index=True)
    report_date: Mapped[date | None] = mapped_column(Date, index=True)
    # the full §17.6 decision report (council_summary / strategic_options / ...)
    report: Mapped[dict | None] = mapped_column(JSONB)

    extra: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
