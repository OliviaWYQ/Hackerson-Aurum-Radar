"""Stage 6 — Brief: generate the daily strategic brief.

The headline deliverable (PRD §9.6). Output -> daily_briefs (§8).
``recommended_actions`` is filled afterwards by stage 7 (see pipeline.py).
"""
from __future__ import annotations

from datetime import date

from loguru import logger

from app.schemas import DailyBriefIn, IntelligenceEventIn, MarketSnapshotIn
from app.services.llm import get_llm


def generate_brief(
    events: list[IntelligenceEventIn],
    snapshots: list[MarketSnapshotIn],
    brief_date: date | None = None,
    source_count: int = 0,
) -> DailyBriefIn:
    """Produce one DailyBriefIn for the given day."""
    brief_date = brief_date or date.today()
    brief = DailyBriefIn(
        brief_date=brief_date,
        markets=sorted({s.market for s in snapshots}),
        event_count=len(events),
        source_count=source_count,
    )

    llm = get_llm()
    if llm.is_configured:
        try:
            raw = llm.generate_brief(
                snapshots=[_snapshot_brief(s) for s in snapshots],
                events=[_event_brief(e) for e in _top_events(events)],
            )
            brief.executive_summary = raw.get("executive_summary", "")
            brief.opportunities = raw.get("opportunities", [])
            brief.risks = raw.get("risks", [])
            brief.watch_items = raw.get("watch_items", [])
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Brief generation failed: {exc}")
    else:
        logger.warning("LLM not configured — brief has counts only")

    logger.info(f"Brief: generated for {brief_date} ({len(events)} events)")
    return brief


def _top_events(
    events: list[IntelligenceEventIn], limit: int = 20
) -> list[IntelligenceEventIn]:
    """Highlight the strongest signals — ranked by intensity, then by max(opportunity, risk).

    intensity ≥ 4 events are guaranteed to surface (preclassify_extract.md interface
    contract: intensity ≥ 4 → 预警队列).
    """
    return sorted(
        events,
        key=lambda e: (
            e.intensity or 0,
            max(e.opportunity_score or 0, e.risk_score or 0),
        ),
        reverse=True,
    )[:limit]


def _snapshot_brief(s: MarketSnapshotIn) -> dict:
    return {
        "market": s.market,
        "opportunity_score": s.opportunity_score,
        "risk_score": s.risk_score,
        "overall_judgement": s.overall_judgement,
    }


def _event_brief(e: IntelligenceEventIn) -> dict:
    """Brief payload uses key_claim + downstream_implications as summary material
    (architecture.md §7.3 接口约定).
    """
    primary = next((f for f in e.env_factors if f.is_primary), None)
    return {
        "market": e.market,
        "source_category": e.source_category.value,
        "title": e.title,
        "key_claim": e.key_claim or e.summary,
        "primary_env_factor": primary.factor_name if primary else None,
        "signal_direction": e.signal_direction.value,
        "intensity": e.intensity,
        "downstream_implications": e.downstream_implications,
        "priority": e.priority.value,
    }
