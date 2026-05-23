from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import ActionItem, IntelligenceEvent

router = APIRouter()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _evidence_ids_from(extra: dict | None) -> list[int]:
    """Coerce extra.evidence_ids (stored as str or int) into a list[int]."""
    if not extra:
        return []
    raw = extra.get("evidence_ids") or []
    out: list[int] = []
    for v in raw:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


def _evidence_payload(event: IntelligenceEvent, extra_lookup: dict) -> dict:
    """Compact payload describing one evidence intelligence_event.

    The frontend uses these to render clickable refs in the action detail panel
    (instead of the bare "关联情报事件 #5" id surface).
    """
    primary = None
    for f in (event.env_factors or []):
        if isinstance(f, dict) and f.get("is_primary"):
            primary = {
                "factor_id": f.get("factor_id"),
                "factor_name": f.get("factor_name"),
            }
            break
    source_name = (event.extra or {}).get("source_name") or extra_lookup.get(event.id, {}).get("source_name")
    return {
        "event_id": event.id,
        "title": event.title,
        "key_claim": event.key_claim,
        "source_url": event.source_url,
        "source_name": source_name,
        "source_category": event.source_category,
        "primary_factor": primary,
        "signal_direction": event.signal_direction,
        "intensity": event.intensity,
        "market": event.market,
    }


def _load_evidence_map(db: Session, action_rows: list[ActionItem]) -> dict[int, dict]:
    """Pre-load all evidence intelligence_events referenced by these actions.

    Avoids N+1; uses a single IN-query across all distinct evidence ids.
    """
    all_ids: set[int] = set()
    for action in action_rows:
        all_ids.update(_evidence_ids_from(action.extra))
        if action.event_id:  # legacy event-derived actions
            all_ids.add(action.event_id)
    if not all_ids:
        return {}
    events = (
        db.query(IntelligenceEvent)
        .filter(IntelligenceEvent.id.in_(all_ids))
        .all()
    )
    return {ev.id: _evidence_payload(ev, {}) for ev in events}


def _serialize_action(action: ActionItem, evidence_map: dict[int, dict]) -> dict:
    extra = action.extra or {}
    ev_ids = _evidence_ids_from(extra)
    if action.event_id and action.event_id not in ev_ids:
        ev_ids = [action.event_id, *ev_ids]
    evidence = [evidence_map[i] for i in ev_ids if i in evidence_map]
    return {
        "id": action.id,
        "market": action.market,
        "department": action.department,
        "priority": action.priority,
        "action_title": action.action_title,
        "action_detail": action.action_detail,
        "reason": action.reason,
        "deadline": action.deadline,
        "expected_output": action.expected_output,
        "success_metric": action.success_metric,
        "status": action.status,
        "event_id": action.event_id,
        "source_url": extra.get("source_url"),
        # ↓ surfaced from action_items.extra (architecture.md §17.7)
        "evidence_ids": ev_ids,
        "evidence": evidence,
        "strategic_option": extra.get("strategic_option"),
        "category": extra.get("category"),
        "channel": extra.get("channel"),
        "created_at": _iso(action.created_at),
        "updated_at": _iso(action.updated_at),
    }


@router.get("/actions")
def list_actions(
    department: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(ActionItem)
    if department:
        q = q.filter(ActionItem.department == department)
    if priority:
        q = q.filter(ActionItem.priority == priority)
    if market:
        q = q.filter(ActionItem.market == market)
    if status:
        q = q.filter(ActionItem.status == status)
    rows = q.order_by(ActionItem.created_at.desc(), ActionItem.id.desc()).all()
    evidence_map = _load_evidence_map(db, rows)
    return {
        "items": [_serialize_action(row, evidence_map) for row in rows],
        "total": len(rows),
    }


@router.get("/actions/{action_id}")
def get_action(action_id: int, db: Session = Depends(get_db)):
    action = db.get(ActionItem, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    evidence_map = _load_evidence_map(db, [action])
    return _serialize_action(action, evidence_map)
