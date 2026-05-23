from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import JobRun

router = APIRouter()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@router.get("/jobs/status")
def get_jobs_status(db: Session = Depends(get_db)):
    rows = db.query(JobRun).order_by(JobRun.started_at.desc().nullslast(), JobRun.id.desc()).all()
    if not rows:
        return {"status": "idle", "last_run": None, "next_run": None, "stages": []}

    latest_job = rows[0].job_name
    latest_rows = [row for row in rows if row.job_name == latest_job]
    status = "success"
    if any(row.status == "running" for row in latest_rows):
        status = "running"
    elif any(row.status == "failed" for row in latest_rows):
        status = "failed"

    last_run = max((row.finished_at or row.started_at for row in latest_rows if row.finished_at or row.started_at), default=None)
    return {
        "status": status,
        "last_run": _iso(last_run),
        "next_run": None,
        "stages": [
            {
                "stage": row.stage,
                "status": row.status,
                "started_at": _iso(row.started_at),
                "finished_at": _iso(row.finished_at),
                "rows_affected": row.rows_affected,
                "error_message": row.error_message,
            }
            for row in sorted(latest_rows, key=lambda item: item.id)
        ],
    }


@router.post("/jobs/run")
def run_job():
    raise HTTPException(
        status_code=501,
        detail="Manual pipeline trigger is not wired to the API yet; run backend/scripts/run_council.py for now.",
    )
