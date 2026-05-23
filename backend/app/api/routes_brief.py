from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import DailyBrief

router = APIRouter()


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value else None


def _serialize_brief(brief: DailyBrief) -> dict:
    return {
        "id": brief.id,
        "brief_date": _iso(brief.brief_date),
        "markets": brief.markets or [],
        "executive_summary": brief.executive_summary or "",
        "opportunities": brief.opportunities or [],
        "risks": brief.risks or [],
        "watch_items": brief.watch_items or [],
        "recommended_actions": brief.recommended_actions or [],
        "source_count": brief.source_count or 0,
        "event_count": brief.event_count or 0,
        "created_at": _iso(brief.created_at),
        "updated_at": _iso(brief.updated_at),
    }


@router.get("/brief/latest")
def get_latest_brief(
    db: Session = Depends(get_db),
    market: str | None = Query(None),
):
    q = db.query(DailyBrief).order_by(DailyBrief.brief_date.desc().nullslast(), DailyBrief.id.desc())
    if market:
        q = q.filter(DailyBrief.markets.contains(cast([market], JSONB)))
    brief = q.first()
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    return _serialize_brief(brief)


@router.get("/briefs/{brief_date}")
def get_brief_by_date(brief_date: date, db: Session = Depends(get_db)):
    brief = db.query(DailyBrief).filter(DailyBrief.brief_date == brief_date).first()
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    return _serialize_brief(brief)
