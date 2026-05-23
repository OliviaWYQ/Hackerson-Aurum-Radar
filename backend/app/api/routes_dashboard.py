from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import (
    ActionItem,
    CouncilReport,
    District,
    IntelligenceEvent,
    MarketSnapshot,
    RawDocument,
)
from app.services.taxonomy import DEFAULT_WINDOW_DAYS, MVP_MARKETS, region_for

router = APIRouter()


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value else None


def _window_cutoff(window_days: int) -> datetime:
    """UTC datetime ``window_days`` ago — the lower bound on dashboard data."""
    return datetime.now(timezone.utc) - timedelta(days=window_days)


def _latest_snapshots(db: Session, since: datetime | None = None) -> list[MarketSnapshot]:
    q = db.query(MarketSnapshot)
    if since:
        q = q.filter(MarketSnapshot.created_at >= since)
    rows = q.order_by(
        MarketSnapshot.market.asc(),
        MarketSnapshot.snapshot_date.desc().nullslast(),
        MarketSnapshot.id.desc(),
    ).all()
    seen: set[str] = set()
    latest: list[MarketSnapshot] = []
    for row in rows:
        if not row.market or row.market in seen:
            continue
        seen.add(row.market)
        latest.append(row)
    return latest


def _snapshot_headline(snapshot: MarketSnapshot) -> str:
    items = snapshot.key_opportunities or snapshot.key_risks or snapshot.watch_items or []
    if items:
        return str(items[0])
    return snapshot.overall_judgement or ""


def _market_from_events(
    db: Session, market: str, since: datetime | None = None
) -> dict | None:
    q = db.query(IntelligenceEvent).filter(IntelligenceEvent.market == market)
    if since:
        q = q.filter(IntelligenceEvent.created_at >= since)
    rows = q.order_by(IntelligenceEvent.created_at.desc()).all()
    if not rows:
        return None
    opportunity = round(sum(e.opportunity_score or 0 for e in rows) / len(rows))
    risk = round(sum(e.risk_score or 0 for e in rows) / len(rows))
    return {
        "market": market,
        "region": region_for(market),
        "tier": 1,
        "opportunity_score": opportunity,
        "risk_score": risk,
        "headline": rows[0].summary or rows[0].title or "",
        "event_count": len(rows),
    }


@router.get("/dashboard/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    window_days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=365, alias="window_days"),
    market: str | None = Query(None),
):
    cutoff = _window_cutoff(window_days)

    def ev_q():
        q = db.query(IntelligenceEvent).filter(IntelligenceEvent.created_at >= cutoff)
        return q.filter(IntelligenceEvent.market == market) if market else q

    def raw_q():
        q = db.query(RawDocument).filter(RawDocument.created_at >= cutoff)
        return q.filter(RawDocument.market == market) if market else q

    def snap_q():
        q = db.query(MarketSnapshot).filter(MarketSnapshot.created_at >= cutoff)
        return q.filter(MarketSnapshot.market == market) if market else q

    def act_q():
        q = db.query(ActionItem).filter(ActionItem.created_at >= cutoff)
        return q.filter(ActionItem.market == market) if market else q

    events_total = (
        ev_q().with_entities(func.count(IntelligenceEvent.id)).scalar() or 0
    )
    raw_total = (
        raw_q().with_entities(func.count(RawDocument.id)).scalar() or 0
    )
    high_priority = (
        ev_q()
        .filter(IntelligenceEvent.priority.in_(("P0", "P1", "high")))
        .with_entities(func.count(IntelligenceEvent.id))
        .scalar()
        or 0
    )
    pending_actions = (
        act_q()
        .filter(ActionItem.status.in_(("pending", "in_progress")))
        .with_entities(func.count(ActionItem.id))
        .scalar()
        or 0
    )
    latest_event_at = (
        ev_q().with_entities(func.max(IntelligenceEvent.created_at)).scalar()
    )
    latest_snapshot_at = (
        snap_q().with_entities(func.max(MarketSnapshot.created_at)).scalar()
    )
    as_of = latest_snapshot_at or latest_event_at or datetime.now(timezone.utc)

    markets_scanned = (
        1 if market else (
            snap_q().with_entities(func.count(distinct(MarketSnapshot.market))).scalar()
            or ev_q().with_entities(func.count(distinct(IntelligenceEvent.market))).scalar()
            or 0
        )
    )
    judgments_generated = (
        snap_q().with_entities(func.count(MarketSnapshot.id)).scalar() or 0
    )
    opportunities = (
        ev_q()
        .filter(IntelligenceEvent.signal_direction == "positive")
        .with_entities(func.count(IntelligenceEvent.id))
        .scalar()
        or 0
    )
    competition = (
        ev_q()
        .filter(IntelligenceEvent.source_category == "competition")
        .with_entities(func.count(IntelligenceEvent.id))
        .scalar()
        or 0
    )
    regulation = (
        ev_q()
        .filter(IntelligenceEvent.source_category == "regulation")
        .with_entities(func.count(IntelligenceEvent.id))
        .scalar()
        or 0
    )
    return {
        "as_of": _iso(as_of),
        "window_days": window_days,
        "since": _iso(cutoff),
        "radar": {
            "markets_scanned": markets_scanned,
            "documents_integrated": raw_total,
            "high_priority_changes": high_priority,
            "judgments_generated": judgments_generated,
        },
        "events_today": events_total,
        "events_today_delta": 0,
        "high_priority_events": high_priority,
        "pending_actions": pending_actions,
        "pending_actions_delta": 0,
        "key_analysis": {
            "opportunities": opportunities,
            "competition": competition,
            "regulation": regulation,
        },
    }


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    window_days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=365, alias="window_days"),
):
    cutoff = _window_cutoff(window_days)
    snapshots = _latest_snapshots(db, since=cutoff)
    markets = [
        {
            "market": s.market,
            "region": s.region or region_for(s.market or ""),
            "tier": 1,
            "opportunity_score": s.opportunity_score or 0,
            "risk_score": s.risk_score or 0,
            "headline": _snapshot_headline(s),
            "event_count": s.event_count or 0,
        }
        for s in snapshots
        if s.market
    ]

    # Fallback: no snapshots within the window — derive from events directly.
    if not markets:
        for market in MVP_MARKETS:
            item = _market_from_events(db, market, since=cutoff)
            if item:
                markets.append(item)

    latest_date = snapshots[0].snapshot_date if snapshots else None
    return {
        "as_of": _iso(latest_date) or _iso(datetime.now(timezone.utc)),
        "window_days": window_days,
        "since": _iso(cutoff),
        "markets": markets,
    }


@router.get("/markets/{market}")
def get_market(
    market: str,
    db: Session = Depends(get_db),
    window_days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=365, alias="window_days"),
):
    cutoff = _window_cutoff(window_days)
    snapshot = (
        db.query(MarketSnapshot)
        .filter(MarketSnapshot.market == market)
        .filter(MarketSnapshot.created_at >= cutoff)
        .order_by(MarketSnapshot.snapshot_date.desc().nullslast(), MarketSnapshot.id.desc())
        .first()
    )
    if snapshot is None:
        derived = _market_from_events(db, market, since=cutoff)
        if derived is None:
            raise HTTPException(status_code=404, detail="Market not found")
        return {
            **derived,
            "snapshot_date": None,
            "overall_judgement": derived["headline"],
            "key_opportunities": [derived["headline"]] if derived["headline"] else [],
            "key_risks": [],
            "watch_items": [],
            "created_at": None,
        }

    return {
        "market": snapshot.market,
        "region": snapshot.region or region_for(snapshot.market or ""),
        "snapshot_date": _iso(snapshot.snapshot_date),
        "opportunity_score": snapshot.opportunity_score or 0,
        "risk_score": snapshot.risk_score or 0,
        "overall_judgement": snapshot.overall_judgement or "",
        "key_opportunities": snapshot.key_opportunities or [],
        "key_risks": snapshot.key_risks or [],
        "watch_items": snapshot.watch_items or [],
        "event_count": snapshot.event_count or 0,
        "created_at": _iso(snapshot.created_at),
    }


@router.get("/council/latest")
def get_latest_council(db: Session = Depends(get_db)):
    """Latest persisted council decision report across all markets (architecture.md §17.9)."""
    row = db.query(CouncilReport).order_by(CouncilReport.id.desc()).first()
    if row is None or not row.report:
        raise HTTPException(status_code=404, detail="No council report yet — run the pipeline")
    return row.report


@router.get("/markets/{market}/council")
def get_market_council(market: str, db: Session = Depends(get_db)):
    """Latest persisted council decision report for one market (architecture.md §17.9).

    Reads from council_reports — the council itself runs in pipeline stage 7,
    not on this request.
    """
    row = (
        db.query(CouncilReport)
        .filter(CouncilReport.market == market)
        .order_by(CouncilReport.id.desc())
        .first()
    )
    if row is None or not row.report:
        raise HTTPException(status_code=404, detail=f"No council report for {market}")
    return row.report


@router.get("/markets/{market}/districts")
def get_market_districts(market: str, db: Session = Depends(get_db)):
    rows = (
        db.query(District)
        .filter(District.market == market)
        .order_by(District.store_count.desc().nullslast(), District.id.asc())
        .all()
    )
    return {"items": [_serialize_district(row) for row in rows], "total": len(rows)}


@router.get("/districts/{district_id}")
def get_district(district_id: int, db: Session = Depends(get_db)):
    row = db.get(District, district_id)
    if row is None:
        raise HTTPException(status_code=404, detail="District not found")
    return _serialize_district(row)


def _serialize_district(row: District) -> dict:
    return {
        "id": row.id,
        "market": row.market,
        "name": row.name,
        "store_count": row.store_count or 0,
        "heat_level": row.heat_level,
        "profile": row.profile or {},
        "created_at": _iso(row.created_at),
    }
