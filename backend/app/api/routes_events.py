from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import IntelligenceEvent, RawDocument

router = APIRouter()

# UI category zh -> source_category enum value (architecture.md §7.3 双坐标轴).
# Maintains the legacy 中文筛选项，让前端不用大改即可继续按渠道筛。
CATEGORY_TO_SOURCE_CATEGORY = {
    "竞争": "competition",
    "产品": "product",
    "平台": "channel",
    "社媒": "social_media",
    "法规": "regulation",
    "渠道": "channel",
    "宏观": "macro",
    "供应链": "supply_chain",
}

SOURCE_CATEGORY_TO_CATEGORY = {v: k for k, v in CATEGORY_TO_SOURCE_CATEGORY.items()}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _source_category_from_category(category: str | None) -> str | None:
    if not category or category == "全部":
        return None
    return CATEGORY_TO_SOURCE_CATEGORY.get(category, category)


def _priority_to_ui(priority: str | None) -> str:
    return "high" if priority in {"P0", "P1", "high"} else "mid"


def _primary_env_factor(env_factors: list | None) -> dict | None:
    if not env_factors:
        return None
    for f in env_factors:
        if isinstance(f, dict) and f.get("is_primary"):
            return f
    return env_factors[0] if isinstance(env_factors[0], dict) else None


def _serialize_event(event: IntelligenceEvent, raw: RawDocument | None = None) -> dict:
    source_name = (
        (event.extra or {}).get("source_name")
        or (raw.source_name if raw else None)
        or "公开来源"
    )
    published_at = (
        (event.extra or {}).get("published_at")
        or _iso(raw.published_at if raw else None)
        or _iso(event.created_at)
    )
    source_category = event.source_category or ""
    category_label = SOURCE_CATEGORY_TO_CATEGORY.get(source_category, source_category)
    primary = _primary_env_factor(event.env_factors)
    return {
        # architecture.md §6.3 fields — 双坐标轴
        "event_id": event.id,
        "market": event.market,
        "region": event.region,
        "source_category": source_category,
        "env_factors": event.env_factors or [],
        "conduction_chain": event.conduction_chain,
        "signal_direction": event.signal_direction,
        "intensity": event.intensity,
        "impact_scope": event.impact_scope or [],
        "entities": event.entities or {},
        "key_claim": event.key_claim,
        "downstream_implications": event.downstream_implications or [],
        "ambiguity_flags": event.ambiguity_flags or [],
        "confidence": float(event.confidence) if event.confidence is not None else None,
        "title": event.title,
        "summary": event.summary,
        "business_impact": event.business_impact,
        "priority": event.priority,
        "opportunity_score": event.opportunity_score,
        "risk_score": event.risk_score,
        "source_url": event.source_url,
        "published_at": published_at,
        "created_at": _iso(event.created_at),
        "updated_at": _iso(event.updated_at),
        # compatibility fields for the current React view model
        "cat": category_label,
        "primary_env_factor": primary,
        "source_name": source_name,
        "source": source_name,
        "src_detail": event.source_url,
        "time": published_at,
        "impact": [
            {
                "kind": "trend",
                "title": "业务影响",
                "text": event.business_impact or event.key_claim or event.summary or "",
            }
        ],
        "markets": [event.market] if event.market else [],
        "brands": [source_name] if source_name else [],
        "citation": source_name,
        "citation_time": published_at,
        "new": False,
        "ui_priority": _priority_to_ui(event.priority),
    }


@router.get("/events")
def list_events(
    category: Optional[str] = Query(None, description="中文渠道筛选 (兼容)"),
    market: Optional[str] = Query(None),
    source_category: Optional[str] = Query(
        None, description="信息来源轴: competition/product/social_media/regulation/channel/macro/supply_chain"
    ),
    env_factor: Optional[str] = Query(
        None, description="底层影响因子: F1-F7 (匹配 env_factors[*].factor_id)"
    ),
    signal_direction: Optional[str] = Query(
        None, description="信号方向: positive/negative/mixed/neutral"
    ),
    priority: Optional[str] = Query(None),
    min_intensity: Optional[int] = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = (
        db.query(IntelligenceEvent, RawDocument)
        .outerjoin(RawDocument, IntelligenceEvent.raw_document_id == RawDocument.id)
    )
    if market:
        q = q.filter(IntelligenceEvent.market == market)
    resolved_source_category = source_category or _source_category_from_category(category)
    if resolved_source_category:
        q = q.filter(IntelligenceEvent.source_category == resolved_source_category)
    if priority:
        q = q.filter(IntelligenceEvent.priority == priority)
    if signal_direction:
        q = q.filter(IntelligenceEvent.signal_direction == signal_direction)
    if min_intensity is not None:
        q = q.filter(IntelligenceEvent.intensity >= min_intensity)
    if env_factor:
        # JSONB contains: env_factors @> [{"factor_id": "F2"}]
        q = q.filter(
            IntelligenceEvent.env_factors.contains(
                cast([{"factor_id": env_factor}], JSONB)
            )
        )

    total = q.count()
    rows = (
        q.order_by(IntelligenceEvent.created_at.desc(), IntelligenceEvent.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "items": [_serialize_event(event, raw) for event, raw in rows],
        "total": total,
        "page": page,
        "size": size,
    }


class BatchQuery(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=100)


@router.post("/events/batch")
def batch_events(body: BatchQuery, db: Session = Depends(get_db)):
    rows = (
        db.query(IntelligenceEvent, RawDocument)
        .outerjoin(RawDocument, IntelligenceEvent.raw_document_id == RawDocument.id)
        .filter(IntelligenceEvent.id.in_(body.ids))
        .order_by(IntelligenceEvent.created_at.desc(), IntelligenceEvent.id.desc())
        .all()
    )
    found_ids = {event.id for event, _ in rows}
    missing = [i for i in body.ids if i not in found_ids]
    return {
        "items": [_serialize_event(event, raw) for event, raw in rows],
        "total": len(rows),
        "missing": missing or None,
    }


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(IntelligenceEvent, RawDocument)
        .outerjoin(RawDocument, IntelligenceEvent.raw_document_id == RawDocument.id)
        .filter(IntelligenceEvent.id == event_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event, raw = row
    return _serialize_event(event, raw)
