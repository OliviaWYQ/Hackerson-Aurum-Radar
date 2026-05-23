"""Pydantic data contracts passed between Agent pipeline stages.

Each ``*In`` model mirrors a table in backend/architecture.md §8. They are the
in-memory representation; persistence (SQLAlchemy models under app/models) is a
separate layer.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.enums import (
    ActionStatus,
    ConductionChainId,
    CredibilityLevel,
    EnvFactorId,
    PipelineStage,
    Priority,
    SignalDirection,
    SourceCategory,
    SourceType,
    StageStatus,
)


class RawDocumentIn(BaseModel):
    """Mirrors ``raw_documents`` (architecture.md §8). Output of stages 1-2."""

    source_type: SourceType
    source_name: str
    market: str
    region: str | None = None
    title: str
    summary: str | None = None
    url: str
    published_at: datetime | None = None
    fetched_at: datetime
    language: str | None = None
    raw_content: str | None = None
    clean_content: str | None = None
    content_hash: str | None = None
    oss_path: str | None = None
    credibility_level: CredibilityLevel | None = None

    # --- pipeline-internal, NOT persisted to raw_documents ---
    candidate_source_category: SourceCategory | None = None
    relevant: bool = True


class EnvFactorIn(BaseModel):
    """One environmental impact factor on an intelligence event (preclassify_extract.md §第二坐标轴).

    An event carries 1-3 of these; exactly one has ``is_primary=True``.
    """

    factor_id: EnvFactorId
    factor_name: str  # supply_constraint / structure_disruption / ...
    is_primary: bool = False
    evidence: str = ""  # 30 字内的触发该判断的原文片段或推理依据


class ConductionChainIn(BaseModel):
    """传导链路定位 (preclassify_extract.md §conduction)."""

    chain_id: ConductionChainId
    chain_name: str
    node_position: str | None = None  # 该信号处于链路上的哪一节点
    lag_estimate: str | None = None   # 时滞估计（短期/中期/长期 + 时间单位）


class EntitiesIn(BaseModel):
    """实体抽取结果. 缺失字段返回空列表而非省略."""

    brands: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    markets: list[str] = Field(default_factory=list)
    regulators: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)


class IntelligenceEventIn(BaseModel):
    """Mirrors ``intelligence_events`` (architecture.md §8). Output of stages 3-4.

    Stage 3 (extraction) fills the source/factor/signal fields; Stage 4 (scoring)
    fills ``priority / opportunity_score / risk_score``.
    """

    # --- 基础元数据 ---
    market: str
    region: str | None = None
    title: str
    summary: str | None = None
    business_impact: str | None = None
    source_url: str
    raw_document_id: int | None = None  # FK -> raw_documents.id

    # --- Stage 3: 第一坐标轴 (信息来源) ---
    source_category: SourceCategory

    # --- Stage 3: 第二坐标轴 (底层环境影响因子) + 传导链路 ---
    env_factors: list[EnvFactorIn] = Field(default_factory=list)
    conduction_chain: ConductionChainIn | None = None

    # --- Stage 3: 信号属性 ---
    signal_direction: SignalDirection = SignalDirection.neutral
    intensity: int = Field(default=1, ge=1, le=5)
    impact_scope: list[str] = Field(default_factory=list)
    entities: EntitiesIn = Field(default_factory=EntitiesIn)
    key_claim: str = ""              # 纯事实陈述 ≤50 字
    downstream_implications: list[str] = Field(default_factory=list)  # 1-3 条推断
    ambiguity_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    # --- Stage 4: 评分产出 ---
    priority: Priority = Priority.P2
    opportunity_score: int = Field(default=0, ge=0, le=100)
    risk_score: int = Field(default=0, ge=0, le=100)

    # --- carried from the source raw_document (not persisted as columns) ---
    source_name: str | None = None
    credibility_level: CredibilityLevel | None = None
    published_at: datetime | None = None
    source_content_hash: str | None = None  # pipeline-internal: event -> raw_document link


class MarketSnapshotIn(BaseModel):
    """Mirrors ``market_snapshots`` (architecture.md §8). Output of stage 5."""

    market: str
    region: str | None = None
    snapshot_date: date
    opportunity_score: int = Field(default=0, ge=0, le=100)
    risk_score: int = Field(default=0, ge=0, le=100)
    overall_judgement: str = ""
    key_opportunities: list[str] = []
    key_risks: list[str] = []
    watch_items: list[str] = []
    event_count: int = 0


class ActionItemIn(BaseModel):
    """Mirrors ``action_items`` (architecture.md §8). Output of stage 7."""

    market: str
    department: str
    priority: Priority
    action_title: str
    action_detail: str
    reason: str
    deadline: str | None = None
    expected_output: str | None = None
    success_metric: str | None = None
    status: ActionStatus = ActionStatus.pending
    event_id: int | None = None  # FK -> intelligence_events.id (None for council-derived)
    source_url: str | None = None
    extra: dict = Field(default_factory=dict)  # evidence_ids / category / channel — traceability


class DailyBriefIn(BaseModel):
    """Mirrors ``daily_briefs`` (architecture.md §8). Output of stage 6."""

    brief_date: date
    markets: list[str] = []
    executive_summary: str = ""
    opportunities: list[str] = []
    risks: list[str] = []
    watch_items: list[str] = []
    recommended_actions: list[ActionItemIn] = []
    source_count: int = 0
    event_count: int = 0


class StageResult(BaseModel):
    """One pipeline stage run — basis for a ``job_runs`` row (architecture.md §8)."""

    stage: PipelineStage
    status: StageStatus = StageStatus.running
    rows_affected: int = 0
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class PipelineResult(BaseModel):
    """Aggregate result of one pipeline run."""

    job_name: str
    trigger_type: str = "manual"
    markets: list[str] = []
    stages: list[StageResult] = []
    started_at: datetime
    finished_at: datetime | None = None
