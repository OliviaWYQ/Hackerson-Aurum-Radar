"""SQLAlchemy model — raw_documents (architecture.md §8). Output of stages 1-2."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class RawDocument(Base):
    __tablename__ = "raw_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    source_type: Mapped[str | None] = mapped_column(String)
    source_name: Mapped[str | None] = mapped_column(String)
    market: Mapped[str | None] = mapped_column(String, index=True)
    region: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    language: Mapped[str | None] = mapped_column(String)
    raw_content: Mapped[str | None] = mapped_column(Text)
    clean_content: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    oss_path: Mapped[str | None] = mapped_column(String)  # empty until OSS wired
    credibility_level: Mapped[str | None] = mapped_column(String)

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
