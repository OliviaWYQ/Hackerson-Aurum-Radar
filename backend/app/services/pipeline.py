"""Agent pipeline orchestrator — runs stages 1-7 in sequence.

Each stage is independent and idempotent (architecture.md §7). This module
chains them, times them, persists each stage's output to the database, and
records a job_runs row per stage.

Entry point for both the scheduler and POST /api/jobs/run.

Persistence (architecture.md §7.2):
  * Stage 1 Ingest produces in-memory documents only.
  * Stage 2 Clean persists them to raw_documents.
  * Events are persisted at the Score stage, once fully scored.
  * Forecast / Brief / Action persist their own output.
Pass ``persist=False`` to run purely in memory (tests / dry runs).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from loguru import logger
from sqlalchemy.orm import Session

from app.database import repository
from app.database.session import SessionLocal
from app.schemas import (
    ActionItemIn,
    DailyBriefIn,
    IntelligenceEventIn,
    MarketSnapshotIn,
    PipelineResult,
    PipelineStage,
    RawDocumentIn,
    StageResult,
    StageStatus,
)
from app.services.brief import generate_brief
from app.services.council import derive_actions, run_council
from app.services.extraction import extract_events
from app.services.forecast import forecast_markets
from app.services.ingestion import clean_documents, collect_documents
from app.services.scoring import score_events
from app.services.taxonomy import MVP_MARKETS

ALL_STAGES: list[str] = [s.value for s in PipelineStage]


class PipelineContext:
    """Carries data (and the DB session) between stages."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self.markets: list[str] = []
        self.raw_documents: list[RawDocumentIn] = []
        self.clean_documents: list[RawDocumentIn] = []
        self.hash_id_map: dict[str, int] = {}  # content_hash -> raw_documents.id
        self.events: list[IntelligenceEventIn] = []
        self.snapshots: list[MarketSnapshotIn] = []
        self.brief: DailyBriefIn | None = None
        self.actions: list[ActionItemIn] = []


def run_pipeline(
    markets: list[str] | None = None,
    source_types: list[str] | None = None,
    stages: list[str] | None = None,
    seed_documents: list[RawDocumentIn] | None = None,
    prefilled_hash_id_map: dict[str, int] | None = None,
    trigger_type: str = "manual",
    persist: bool = True,
) -> PipelineResult:
    """Run the requested pipeline stages and return a run report.

    With ``persist=True`` each stage's output is written to the database and a
    job_runs row is recorded. ``seed_documents`` lets the pipeline run before
    the live providers are ported (see ingestion.load_seed_documents).

    Pass ``prefilled_hash_id_map`` when ``seed_documents`` were already loaded
    from ``raw_documents`` (e.g. via ``repository.list_raw_documents``). The
    map (content_hash -> raw_documents.id) lets Stage 4 link
    ``intelligence_events.raw_document_id`` without re-running clean / save.
    Callers using this should typically skip stages ``ingest`` and ``clean``.
    """
    markets = markets or MVP_MARKETS
    stages = stages or ALL_STAGES
    db = SessionLocal() if persist else None
    ctx = PipelineContext(db)
    ctx.markets = markets
    if seed_documents:
        ctx.raw_documents = list(seed_documents)
        # if the docs are already cleaned (came from RDS), make them available
        # to Stage 3 even when the clean stage is skipped
        ctx.clean_documents = list(seed_documents)
    if prefilled_hash_id_map:
        ctx.hash_id_map = dict(prefilled_hash_id_map)

    result = PipelineResult(
        job_name="agent_pipeline",
        trigger_type=trigger_type,
        markets=markets,
        started_at=datetime.now(timezone.utc),
    )
    params = {"markets": markets, "source_types": source_types, "stages": stages}

    runners = {
        PipelineStage.ingest.value: lambda: _run_ingest(
            ctx, markets, source_types, seed_documents
        ),
        PipelineStage.clean.value: lambda: _run_clean(ctx),
        PipelineStage.extract.value: lambda: _run_extract(ctx),
        PipelineStage.score.value: lambda: _run_score(ctx),
        PipelineStage.forecast.value: lambda: _run_forecast(ctx),
        PipelineStage.brief.value: lambda: _run_brief(ctx),
        PipelineStage.action.value: lambda: _run_action(ctx),
    }

    try:
        for stage_value in ALL_STAGES:
            if stage_value not in stages:
                continue
            stage_result = StageResult(
                stage=PipelineStage(stage_value),
                started_at=datetime.now(timezone.utc),
            )
            try:
                stage_result.rows_affected = runners[stage_value]()
                stage_result.status = StageStatus.success
            except Exception as exc:  # noqa: BLE001 - record failure, stop the chain
                stage_result.status = StageStatus.failed
                stage_result.error_message = str(exc)
                logger.error(f"Stage {stage_value} failed: {exc}")
                if db is not None:
                    db.rollback()
            stage_result.finished_at = datetime.now(timezone.utc)
            result.stages.append(stage_result)

            if db is not None:
                try:
                    repository.save_job_run(
                        db,
                        job_name=result.job_name,
                        trigger_type=trigger_type,
                        stage_result=stage_result,
                        params=params,
                    )
                except Exception as exc:  # noqa: BLE001 - job_runs is best-effort
                    logger.error(f"Failed to record job_run for {stage_value}: {exc}")
                    db.rollback()

            if stage_result.status == StageStatus.failed:
                logger.error("Aborting pipeline — downstream stages need this output")
                break
    finally:
        if db is not None:
            db.close()

    result.finished_at = datetime.now(timezone.utc)
    return result


# --- per-stage runners ------------------------------------------------------
# Each returns the number of rows produced / persisted (recorded on job_runs).


def _run_ingest(
    ctx: PipelineContext,
    markets: list[str],
    source_types: list[str] | None,
    seed_documents: list[RawDocumentIn] | None,
) -> int:
    if seed_documents:
        logger.info(f"Ingest: using {len(ctx.raw_documents)} seed documents")
    else:
        ctx.raw_documents = collect_documents(markets, source_types)
    # Stage 1 output is in-memory only; raw_documents are persisted at clean.
    return len(ctx.raw_documents)


def _run_clean(ctx: PipelineContext) -> int:
    ctx.clean_documents = clean_documents(ctx.raw_documents)
    if ctx.db is not None:
        ctx.hash_id_map = repository.save_raw_documents(ctx.db, ctx.clean_documents)
        return len(ctx.hash_id_map)
    return len(ctx.clean_documents)


def _run_extract(ctx: PipelineContext) -> int:
    docs = ctx.clean_documents or ctx.raw_documents
    ctx.events = extract_events(docs)
    # events are persisted at the score stage, once fully scored
    return len(ctx.events)


def _run_score(ctx: PipelineContext) -> int:
    ctx.events = score_events(ctx.events)
    # link each event to its source raw_document (FK)
    for e in ctx.events:
        e.raw_document_id = ctx.hash_id_map.get(e.source_content_hash)
    if ctx.db is not None:
        return repository.save_events(ctx.db, ctx.events)
    return len(ctx.events)


def _run_forecast(ctx: PipelineContext) -> int:
    ctx.snapshots = forecast_markets(ctx.events, snapshot_date=date.today())
    if ctx.db is not None:
        return repository.save_snapshots(ctx.db, ctx.snapshots)
    return len(ctx.snapshots)


def _run_brief(ctx: PipelineContext) -> int:
    ctx.brief = generate_brief(
        ctx.events,
        ctx.snapshots,
        brief_date=date.today(),
        source_count=len(ctx.clean_documents or ctx.raw_documents),
    )
    if ctx.db is not None and ctx.brief is not None:
        return repository.save_brief(ctx.db, ctx.brief)
    return 1 if ctx.brief else 0


def _run_action(ctx: PipelineContext) -> int:
    """Stage 7 — strategic intelligence council (architecture.md §17).

    Runs the council per market: 5 experts -> chief strategy officer -> decision
    report -> derived action_items. The council reads persisted
    intelligence_events, so it needs a DB session; in a dry run (persist=False)
    the stage is a no-op. One market failing does not abort the others.
    """
    if ctx.db is None:
        logger.info("Action: persist=False — the council needs the DB, skipping")
        return 0
    all_actions: list[ActionItemIn] = []
    total = 0
    for market in ctx.markets:
        try:
            report = run_council(ctx.db, market)
        except Exception as exc:  # noqa: BLE001 - one market failing must not abort
            logger.warning(f"Action: council skipped for {market}: {exc}")
            continue
        repository.save_council_report(ctx.db, market, report)
        actions = derive_actions(market, report)
        all_actions.extend(actions)
        total += repository.save_actions(ctx.db, actions)
    ctx.actions = all_actions
    # re-save the brief so its recommended_actions reflects the council output
    if ctx.brief is not None:
        ctx.brief.recommended_actions = all_actions
        repository.save_brief(ctx.db, ctx.brief)
    return total
