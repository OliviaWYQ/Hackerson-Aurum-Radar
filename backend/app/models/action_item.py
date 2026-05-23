"""SQLAlchemy model — action_items (architecture.md §8). Output of stage 7."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    market: Mapped[str | None] = mapped_column(String, index=True)
    department: Mapped[str | None] = mapped_column(String, index=True)
    priority: Mapped[str | None] = mapped_column(String)
    action_title: Mapped[str | None] = mapped_column(Text)
    action_detail: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[str | None] = mapped_column(String)
    expected_output: Mapped[str | None] = mapped_column(Text)
    success_metric: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String)

    # soft reference to intelligence_events.id — no hard FK, to keep tables decoupled
    event_id: Mapped[int | None] = mapped_column(Integer, index=True)

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
