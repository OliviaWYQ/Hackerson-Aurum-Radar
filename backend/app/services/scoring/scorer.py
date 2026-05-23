"""Stage 4 — Score: rule-based opportunity / risk scoring + priority assignment.

Rules-first (architecture.md §7.2 / §7.3 接口约定):
  * intensity × confidence            → 基础分
  * env_factor primary × signal_direction → 机会/风险偏置
  * conduction_chain.lag_estimate     → 时效权重
  * intensity ≥ 4 or impact_scope 跨市场 → P0 候选
  * credibility / recency             → 折扣

Pure logic — no LLM in MVP. ``priority`` is also produced here (not in Stage 3).
"""
from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from app.schemas import (
    CredibilityLevel,
    EnvFactorId,
    EnvFactorIn,
    IntelligenceEventIn,
    Priority,
    SignalDirection,
)
from app.services.taxonomy import (
    CREDIBILITY_MULTIPLIER,
    ENV_FACTOR_BASE_BIAS,
    INTENSITY_MULTIPLIER,
    LAG_RECENCY_WEIGHT,
    PRIORITY_ADJUSTMENT,
    SIGNAL_DIRECTION_ADJUSTMENT,
)


def score_events(events: list[IntelligenceEventIn]) -> list[IntelligenceEventIn]:
    """Fill priority / opportunity_score / risk_score on each event in place."""
    for event in events:
        event.priority = _decide_priority(event)
        opp, risk = _score_one(event)
        event.opportunity_score = opp
        event.risk_score = risk
    logger.info(f"Score: {len(events)} events scored")
    return events


# --- per-event scoring -----------------------------------------------------

def _score_one(event: IntelligenceEventIn) -> tuple[int, int]:
    base_opp, base_risk = _factor_base_bias(event.env_factors)

    # signal direction shifts which dimension dominates
    opp_shift, risk_shift = SIGNAL_DIRECTION_ADJUSTMENT.get(
        event.signal_direction, (0, 0)
    )
    base_opp += opp_shift
    base_risk += risk_shift

    # priority pushes the dominant dimension up
    adj = PRIORITY_ADJUSTMENT.get(event.priority, 0)
    if base_opp >= base_risk:
        base_opp += adj
    else:
        base_risk += adj

    # intensity × confidence — the headline rule (preclassify_extract.md interface)
    intensity_mult = INTENSITY_MULTIPLIER.get(event.intensity, 0.85)
    confidence_mult = max(0.3, min(1.0, event.confidence or 0.5))

    # credibility & recency further discount weak / stale signals
    cred_mult = CREDIBILITY_MULTIPLIER.get(
        event.credibility_level or CredibilityLevel.B, 0.78
    )
    recency_mult = _recency_factor(event)

    combined = intensity_mult * confidence_mult * cred_mult * recency_mult
    return _clamp(base_opp * combined), _clamp(base_risk * combined)


def _factor_base_bias(factors: list[EnvFactorIn]) -> tuple[int, int]:
    """Base (opportunity, risk) bias driven by env_factors.

    Primary factor weighs full; secondary factors blend in at half weight.
    Falls back to a neutral 50/50 when no factor is present.
    """
    if not factors:
        return 50, 50
    total_weight = 0.0
    opp_acc = 0.0
    risk_acc = 0.0
    for f in factors:
        bias = ENV_FACTOR_BASE_BIAS.get(f.factor_id)
        if bias is None:
            continue
        w = 1.0 if f.is_primary else 0.5
        opp_acc += bias[0] * w
        risk_acc += bias[1] * w
        total_weight += w
    if total_weight == 0:
        return 50, 50
    return round(opp_acc / total_weight), round(risk_acc / total_weight)


def _decide_priority(event: IntelligenceEventIn) -> Priority:
    """Rule-based priority — Stage 4 produces this (Stage 3 no longer outputs it).

    P0 — intensity ≥ 4 AND (high-confidence OR S/A credibility) AND
         signal_direction is negative OR mixed (structural risk)
       — OR regulatory_friction primary with high confidence (compliance shock)
    P1 — intensity ≥ 3, mid+ confidence
    P2 — everything else (background noise / weak signal)
    """
    intensity = event.intensity or 1
    conf = event.confidence or 0.5
    primary = next((f for f in event.env_factors if f.is_primary), None)
    primary_id = primary.factor_id if primary else None

    cred_strong = event.credibility_level in (CredibilityLevel.S, CredibilityLevel.A)
    direction = event.signal_direction

    p0_structural = (
        intensity >= 4
        and (conf >= 0.7 or cred_strong)
        and direction in (SignalDirection.negative, SignalDirection.mixed)
    )
    p0_regulatory = (
        primary_id == EnvFactorId.F4 and conf >= 0.7
    )
    if p0_structural or p0_regulatory:
        return Priority.P0
    if intensity >= 3 and conf >= 0.6:
        return Priority.P1
    return Priority.P2


def _recency_factor(event: IntelligenceEventIn) -> float:
    """Combine conduction_chain.lag_estimate with published_at recency.

    lag_estimate (Stage 3) gives the structural time horizon; published_at gives
    the freshness of the signal. We multiply the two.
    """
    lag_weight = 1.0
    chain = event.conduction_chain
    if chain and chain.lag_estimate:
        lag_key = chain.lag_estimate.lower()
        for key, w in LAG_RECENCY_WEIGHT.items():
            if key.lower() in lag_key:
                lag_weight = w
                break

    if event.published_at is None:
        return lag_weight * 0.85

    now = datetime.now(timezone.utc)
    pub = event.published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    days = (now - pub).days
    if days <= 3:
        fresh = 1.0
    elif days <= 7:
        fresh = 0.9
    elif days <= 30:
        fresh = 0.75
    else:
        fresh = 0.6
    return lag_weight * fresh


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))
