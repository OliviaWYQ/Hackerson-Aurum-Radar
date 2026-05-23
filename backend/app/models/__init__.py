"""SQLAlchemy models — the tables of architecture.md §8.

Importing this package registers every model on ``Base.metadata`` so that
app/database/init_db.py can create all tables.

Decoupling design (the schema is expected to evolve — fields added / removed):
  * Almost every column is nullable; only the primary key and the created_at /
    updated_at timestamps are NOT NULL. A partial row is always insertable.
  * Enum-like values (source_category, priority, credibility_level, ...) are
    stored as plain strings, NOT database ENUM types — adding a value needs no
    ``ALTER TYPE``. Validation lives in the Pydantic layer (app/schemas).
  * Cross-table references (raw_document_id, event_id) are plain integer
    "soft references" with NO hard ForeignKey constraint, so each table can be
    created and populated independently.
  * Every table carries an ``extra`` JSONB column — an escape hatch for fields
    not yet modelled, so new data needs no migration.
"""
from app.models.action_item import ActionItem
from app.models.council_report import CouncilReport
from app.models.daily_brief import DailyBrief
from app.models.district import District
from app.models.intelligence_event import IntelligenceEvent
from app.models.job_run import JobRun
from app.models.market_snapshot import MarketSnapshot
from app.models.raw_document import RawDocument

__all__ = [
    "RawDocument",
    "IntelligenceEvent",
    "MarketSnapshot",
    "DailyBrief",
    "ActionItem",
    "CouncilReport",
    "JobRun",
    "District",
]
