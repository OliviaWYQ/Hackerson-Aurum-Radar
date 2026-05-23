"""SQLAlchemy model — intelligence_events (architecture.md §8). Output of stages 3-4.

Schema follows the §7.3 双坐标轴 upgrade (preclassify_extract.md):
  * source_category — 第一坐标轴 (信息来源)
  * env_factors / conduction_chain — 第二坐标轴 (底层影响因子) + 传导链路
  * signal_direction / intensity / impact_scope / entities / key_claim /
    downstream_implications / ambiguity_flags / confidence — 信号属性 (Stage 3)
  * priority / opportunity_score / risk_score — Stage 4 评分产出
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class IntelligenceEvent(Base):
    __tablename__ = "intelligence_events"
    __table_args__ = (
        # primary filter index — list / dashboard queries
        Index("ix_events_filter", "market", "source_category", "priority", "created_at"),
        # GIN indexes for JSONB factor / scope queries (architecture.md §8)
        Index("ix_events_env_factors_gin", "env_factors", postgresql_using="gin"),
        Index("ix_events_impact_scope_gin", "impact_scope", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- 基础元数据 ---
    market: Mapped[str | None] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    business_impact: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    # soft reference to raw_documents.id — no hard FK, to keep tables decoupled
    raw_document_id: Mapped[int | None] = mapped_column(Integer, index=True)

    # --- Stage 3 抽取：第一坐标轴（信息来源） ---
    source_category: Mapped[str | None] = mapped_column(String)

    # --- Stage 3 抽取：第二坐标轴（底层影响因子） + 传导链路 ---
    env_factors: Mapped[list | None] = mapped_column(JSONB)         # [{factor_id, factor_name, is_primary, evidence}]
    conduction_chain: Mapped[dict | None] = mapped_column(JSONB)    # {chain_id, chain_name, node_position, lag_estimate}

    # --- Stage 3 抽取：信号属性 ---
    signal_direction: Mapped[str | None] = mapped_column(String)
    intensity: Mapped[int | None] = mapped_column(SmallInteger)     # 1-5
    impact_scope: Mapped[list | None] = mapped_column(JSONB)        # ["brand", "category_gold", ...]
    entities: Mapped[dict | None] = mapped_column(JSONB)            # {brands, materials, markets, regulators, locations}
    key_claim: Mapped[str | None] = mapped_column(Text)
    downstream_implications: Mapped[list | None] = mapped_column(JSONB)
    ambiguity_flags: Mapped[list | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2)) # 0.00-1.00

    # --- Stage 4 评分产出 ---
    priority: Mapped[str | None] = mapped_column(String)
    opportunity_score: Mapped[int | None] = mapped_column(Integer)
    risk_score: Mapped[int | None] = mapped_column(Integer)

    # escape hatch for fields not yet modelled (source_name / credibility / published_at carried for display)
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
