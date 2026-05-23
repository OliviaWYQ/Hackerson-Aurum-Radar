"""Persistence layer — map pipeline schemas (app/schemas) to ORM models
(app/models) and write them.

Kept separate from the pipeline so stage logic stays free of DB concerns.

Idempotency (stages are re-runnable, architecture.md §7):
  * raw_documents — bulk insert, skip duplicates by content_hash
  * daily_briefs  — upsert by brief_date (one brief per day)
  * intelligence_events / market_snapshots / action_items / job_runs —
    plain insert; a re-run appends rows.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from loguru import logger
from sqlalchemy import func as sql_func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import (
    ActionItem,
    CouncilReport,
    DailyBrief,
    IntelligenceEvent,
    JobRun,
    MarketSnapshot,
    RawDocument,
)
from app.schemas import (
    ActionItemIn,
    DailyBriefIn,
    IntelligenceEventIn,
    MarketSnapshotIn,
    RawDocumentIn,
    StageResult,
)


def _val(value):
    """Enum -> its string value; passthrough otherwise (incl. None)."""
    return value.value if isinstance(value, Enum) else value


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value is not None else None


# --- stage 2: raw_documents -------------------------------------------------

def list_markets_with_docs(
    db: Session,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    min_docs: int = 1,
) -> list[tuple[str, int]]:
    """Discover (market, doc_count) pairs from raw_documents.

    Used by ``run_council --all-markets`` to figure out which markets are
    worth running. Window filter is ``COALESCE(published_at, fetched_at)``
    — falls back to fetched_at for rows where the source legitimately has
    no publication timestamp (google_trends aggregates, gdelt failed-query
    placeholders, ecommerce/baidu failed scrapes).
    """
    from sqlalchemy import func as sql_func

    ts = sql_func.coalesce(RawDocument.published_at, RawDocument.fetched_at)
    q = (
        db.query(RawDocument.market, sql_func.count(RawDocument.id))
        .filter(RawDocument.market.isnot(None))
        .filter(RawDocument.content_hash.isnot(None))
    )
    if since:
        q = q.filter(ts >= since)
    if until:
        q = q.filter(ts <= until)
    q = q.group_by(RawDocument.market).having(sql_func.count(RawDocument.id) >= min_docs)
    return [(m, c) for m, c in q.order_by(sql_func.count(RawDocument.id).desc()).all()]


def list_raw_documents(
    db: Session,
    *,
    market: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int | None = None,
) -> tuple[list[RawDocumentIn], dict[str, int]]:
    """Read raw_documents from RDS as pipeline-ready ``RawDocumentIn`` objects.

    Returns ``(docs, hash_id_map)`` so the caller can skip stages 1-2 (ingest
    + clean) and feed Stage 3 directly. ``hash_id_map`` lets Stage 4 link
    ``intelligence_events.raw_document_id`` to the existing rows.

    Filters by ``market`` (exact), and ``published_at`` window via
    ``since`` / ``until`` (UTC). Rows without ``content_hash`` are skipped —
    they cannot be linked back at Stage 4.
    """
    from sqlalchemy import func as sql_func

    ts = sql_func.coalesce(RawDocument.published_at, RawDocument.fetched_at)
    q = db.query(RawDocument).filter(RawDocument.content_hash.isnot(None))
    if market:
        q = q.filter(RawDocument.market == market)
    if since:
        q = q.filter(ts >= since)
    if until:
        q = q.filter(ts <= until)
    q = q.order_by(ts.desc().nullslast())
    if limit:
        q = q.limit(limit)

    rows = q.all()
    docs: list[RawDocumentIn] = []
    hash_id_map: dict[str, int] = {}
    for r in rows:
        try:
            docs.append(
                RawDocumentIn(
                    source_type=r.source_type or "news",
                    source_name=r.source_name or "unknown",
                    market=r.market or "",
                    region=r.region,
                    title=r.title or "",
                    summary=r.summary,
                    url=r.url or "",
                    published_at=r.published_at,
                    fetched_at=r.fetched_at or datetime.now(timezone.utc),
                    language=r.language,
                    raw_content=r.raw_content,
                    clean_content=r.clean_content,
                    content_hash=r.content_hash,
                    oss_path=r.oss_path,
                    credibility_level=r.credibility_level,
                )
            )
            hash_id_map[r.content_hash] = r.id
        except Exception as exc:  # noqa: BLE001 - skip malformed rows, don't abort
            logger.warning(f"list_raw_documents: skip id={r.id}: {exc}")
    return docs, hash_id_map


def save_raw_documents(db: Session, docs: list[RawDocumentIn]) -> dict[str, int]:
    """Insert raw documents (skip content_hash dups); return content_hash -> id."""
    if not docs:
        return {}
    rows = [
        dict(
            source_type=_val(d.source_type),
            source_name=d.source_name,
            market=d.market,
            region=d.region,
            title=d.title,
            summary=d.summary,
            url=d.url,
            published_at=d.published_at,
            fetched_at=d.fetched_at,
            language=d.language,
            raw_content=d.raw_content,
            clean_content=d.clean_content,
            content_hash=d.content_hash,
            oss_path=d.oss_path,
            credibility_level=_val(d.credibility_level),
        )
        for d in docs
    ]
    # On hash collision, backfill published_at when the existing row is NULL.
    # Other columns are intentionally not touched — content_hash is stable, so
    # the rest of the record is treated as already-good-enough.
    stmt = pg_insert(RawDocument).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["content_hash"],
        set_={"published_at": sql_func.coalesce(
            RawDocument.published_at, stmt.excluded.published_at
        )},
        where=RawDocument.published_at.is_(None),
    )
    db.execute(stmt)
    db.commit()
    # return content_hash -> id (new and pre-existing rows) so the extract
    # stage can link intelligence_events.raw_document_id
    hashes = [d.content_hash for d in docs if d.content_hash]
    if not hashes:
        return {}
    found = (
        db.query(RawDocument.content_hash, RawDocument.id)
        .filter(RawDocument.content_hash.in_(hashes))
        .all()
    )
    return {h: i for h, i in found}


# --- stages 3-4: intelligence_events ---------------------------------------

def save_events(db: Session, events: list[IntelligenceEventIn]) -> int:
    """Insert scored intelligence events (architecture.md §7.3 双坐标轴)."""
    if not events:
        return 0
    models = [
        IntelligenceEvent(
            market=e.market,
            region=e.region,
            title=e.title,
            summary=e.summary,
            business_impact=e.business_impact,
            source_url=e.source_url,
            raw_document_id=e.raw_document_id,
            # --- 第一坐标轴
            source_category=_val(e.source_category),
            # --- 第二坐标轴 + 链路
            env_factors=[f.model_dump(mode="json") for f in (e.env_factors or [])],
            conduction_chain=(
                e.conduction_chain.model_dump(mode="json") if e.conduction_chain else None
            ),
            # --- 信号属性
            signal_direction=_val(e.signal_direction),
            intensity=e.intensity,
            impact_scope=list(e.impact_scope or []),
            entities=e.entities.model_dump(mode="json") if e.entities else None,
            key_claim=e.key_claim or None,
            downstream_implications=list(e.downstream_implications or []),
            ambiguity_flags=list(e.ambiguity_flags or []),
            confidence=e.confidence,
            # --- Stage 4 评分
            priority=_val(e.priority),
            opportunity_score=e.opportunity_score,
            risk_score=e.risk_score,
            # carried for display but not modelled as columns -> extra
            extra={
                "source_name": e.source_name,
                "credibility_level": _val(e.credibility_level),
                "published_at": _iso(e.published_at),
            },
        )
        for e in events
    ]
    db.add_all(models)
    db.commit()
    return len(models)


# --- stage 5: market_snapshots ---------------------------------------------

def save_snapshots(db: Session, snapshots: list[MarketSnapshotIn]) -> int:
    """Insert market snapshots."""
    if not snapshots:
        return 0
    models = [
        MarketSnapshot(
            market=s.market,
            region=s.region,
            snapshot_date=s.snapshot_date,
            opportunity_score=s.opportunity_score,
            risk_score=s.risk_score,
            overall_judgement=s.overall_judgement,
            key_opportunities=s.key_opportunities,
            key_risks=s.key_risks,
            watch_items=s.watch_items,
            event_count=s.event_count,
        )
        for s in snapshots
    ]
    db.add_all(models)
    db.commit()
    return len(models)


# --- stage 6: daily_briefs --------------------------------------------------

def save_brief(db: Session, brief: DailyBriefIn) -> int:
    """Upsert the daily brief (one row per brief_date)."""
    values = dict(
        brief_date=brief.brief_date,
        markets=brief.markets,
        executive_summary=brief.executive_summary,
        opportunities=brief.opportunities,
        risks=brief.risks,
        watch_items=brief.watch_items,
        recommended_actions=[
            a.model_dump(mode="json") for a in brief.recommended_actions
        ],
        source_count=brief.source_count,
        event_count=brief.event_count,
    )
    stmt = pg_insert(DailyBrief).values(**values).on_conflict_do_update(
        index_elements=["brief_date"],
        set_={k: v for k, v in values.items() if k != "brief_date"},
    )
    db.execute(stmt)
    db.commit()
    return 1


# --- stage 7: action_items --------------------------------------------------

def save_actions(db: Session, actions: list[ActionItemIn]) -> int:
    """Insert department action items."""
    if not actions:
        return 0
    models = [
        ActionItem(
            market=a.market,
            department=a.department,
            priority=_val(a.priority),
            action_title=a.action_title,
            action_detail=a.action_detail,
            reason=a.reason,
            deadline=a.deadline,
            expected_output=a.expected_output,
            success_metric=a.success_metric,
            status=_val(a.status),
            event_id=a.event_id,
            extra={"source_url": a.source_url, **(a.extra or {})},
        )
        for a in actions
    ]
    db.add_all(models)
    db.commit()
    return len(models)


# --- stage 7: council_reports ----------------------------------------------

def save_council_report(db: Session, market: str, report: dict) -> int:
    """Persist one council decision report (architecture.md §17.7)."""
    db.add(CouncilReport(market=market, report_date=date.today(), report=report))
    db.commit()
    return 1


# --- job_runs ---------------------------------------------------------------

def save_job_run(
    db: Session,
    *,
    job_name: str,
    trigger_type: str,
    stage_result: StageResult,
    params: dict | None = None,
) -> None:
    """Record one pipeline stage run."""
    db.add(
        JobRun(
            job_name=job_name,
            stage=_val(stage_result.stage),
            trigger_type=trigger_type,
            status=_val(stage_result.status),
            params_json=params,
            started_at=stage_result.started_at,
            finished_at=stage_result.finished_at,
            rows_affected=stage_result.rows_affected,
            error_message=stage_result.error_message,
        )
    )
    db.commit()
