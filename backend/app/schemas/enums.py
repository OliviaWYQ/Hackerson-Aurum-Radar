"""Shared enumerations — the pipeline data contract.

Values are aligned with backend/architecture.md §7.3 / §8 and
backend/preclassify_extract.md (Stage 3 双坐标轴抽取).
"""
from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    news = "news"
    competitor = "competitor"
    platform = "platform"
    regulation = "regulation"
    market_data = "market_data"
    mall = "mall"
    social = "social"
    report = "report"


class SourceCategory(str, Enum):
    """第一坐标轴 — 信息来源 / 渠道场景 (preclassify_extract.md §System Prompt)."""

    competition = "competition"      # 对手动作 / 市占 / 并购 / 人事
    product = "product"              # 新品 / 技术 / 定价 / SKU 调整
    social_media = "social_media"    # 消费者声量 / KOL / 话题 / 情绪
    regulation = "regulation"        # 监管文件 / 标准 / 税务 / 合规
    channel = "channel"              # 零售格局 / 电商规则 / 物流 / 终端
    macro = "macro"                  # 金价 / 汇率 / 利率 / GDP / PMI
    supply_chain = "supply_chain"    # 矿产 / 加工 / 物流 / 产能


class EnvFactorId(str, Enum):
    """第二坐标轴 — 底层环境影响因子 (F1-F7)."""

    F1 = "F1"  # supply_constraint     供给约束
    F2 = "F2"  # structure_disruption  结构重塑
    F3 = "F3"  # demand_shift          需求迁移
    F4 = "F4"  # regulatory_friction   制度摩擦
    F5 = "F5"  # price_conduction      价格传导
    F6 = "F6"  # narrative_pressure    叙事压力
    F7 = "F7"  # channel_power_shift   渠道博弈


# Reverse lookup for prompt validation / display
ENV_FACTOR_NAMES: dict[EnvFactorId, str] = {
    EnvFactorId.F1: "supply_constraint",
    EnvFactorId.F2: "structure_disruption",
    EnvFactorId.F3: "demand_shift",
    EnvFactorId.F4: "regulatory_friction",
    EnvFactorId.F5: "price_conduction",
    EnvFactorId.F6: "narrative_pressure",
    EnvFactorId.F7: "channel_power_shift",
}


class ConductionChainId(str, Enum):
    """传导链路 (A-E). conduction_chain may be null when nothing fits."""

    A = "A"  # 地缘-供给-成本链
    B = "B"  # 货币-消费-需求链
    C = "C"  # 文化-偏好-结构链
    D = "D"  # 制度-合规-成本链
    E = "E"  # 技术-替代-颠覆链


CONDUCTION_CHAIN_NAMES: dict[ConductionChainId, str] = {
    ConductionChainId.A: "地缘-供给-成本链",
    ConductionChainId.B: "货币-消费-需求链",
    ConductionChainId.C: "文化-偏好-结构链",
    ConductionChainId.D: "制度-合规-成本链",
    ConductionChainId.E: "技术-替代-颠覆链",
}


class SignalDirection(str, Enum):
    """信号对珠宝终端市场的方向."""

    positive = "positive"
    negative = "negative"
    mixed = "mixed"
    neutral = "neutral"


class AmbiguityFlag(str, Enum):
    """歧义标记 — Stage 3 抽取阶段填入 ambiguity_flags 数组."""

    multi_factor_conflict = "multi_factor_conflict"
    scope_unclear = "scope_unclear"
    timing_uncertain = "timing_uncertain"
    source_unverified = "source_unverified"
    entity_ambiguous = "entity_ambiguous"


# impact_scope 是开放标签集合 (品类 / 角色 / 市场)，preclassify_extract.md 已枚举常见值
IMPACT_SCOPE_TAGS: tuple[str, ...] = (
    "raw_material",
    "brand",
    "retailer",
    "consumer",
    "category_natdiamond",
    "category_labdiamond",
    "category_gold",
    "category_gemstone",
    "market_CN",
    "market_US",
    "market_IN",
    "market_GLOBAL",
)


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class CredibilityLevel(str, Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"


class PipelineStage(str, Enum):
    ingest = "ingest"
    clean = "clean"
    extract = "extract"
    score = "score"
    forecast = "forecast"
    brief = "brief"
    action = "action"


class StageStatus(str, Enum):
    running = "running"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class ActionStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    ignored = "ignored"
