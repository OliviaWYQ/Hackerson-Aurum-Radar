"""Read data_probe normalized output and write to raw_documents (DB).

Usage (from backend/ directory):
    python -m scripts.ingest_crawl_data                    # today's files
    python -m scripts.ingest_crawl_data --date 2026-05-23  # specific date
    python -m scripts.ingest_crawl_data --all              # every file in the dir
    python -m scripts.ingest_crawl_data --dry-run          # parse only, no DB writes

File conventions (data_probe/utils.py):
    JSONL  output/normalized/{source_id}_{YYYYMMDD}.jsonl   (new 18-field schema)
    JSON   output/normalized/{source_type}_{YYYYMMDDTHHMMSSz}.json (old 11-field schema)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as `python -m scripts.ingest_crawl_data` from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.core.config import settings
from app.database.repository import save_raw_documents
from app.database.session import SessionLocal
from app.schemas import RawDocumentIn
from app.services.ingestion.providers import load_jsonl_documents, load_seed_documents


def _collect_files(output_dir: Path, date_filter: str | None) -> tuple[list[Path], list[Path]]:
    """Return (jsonl_files, json_files) matching the date filter."""
    jsonl = sorted(output_dir.glob("*.jsonl"))
    json_ = sorted(output_dir.glob("*.json"))
    if date_filter:
        slug = date_filter.replace("-", "")  
        jsonl = [f for f in jsonl if slug in f.name]
        json_ = [f for f in json_ if slug in f.name]
    return jsonl, json_


def _load_all(jsonl_files: list[Path], json_files: list[Path]) -> list[RawDocumentIn]:
    docs: list[RawDocumentIn] = []
    for f in jsonl_files:
        docs.extend(load_jsonl_documents(f))
    for f in json_files:
        docs.extend(load_seed_documents(f))
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest data_probe output into DB")
    parser.add_argument("--date", default=None, help="Filter files by date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--all", action="store_true", dest="all_files", help="Ingest all files, ignore date filter")
    parser.add_argument("--dry-run", action="store_true", help="Parse files but skip DB writes")
    args = parser.parse_args()

    output_dir = Path(settings.DATA_PROBE_OUTPUT_DIR)
    if not output_dir.exists():
        logger.error(f"DATA_PROBE_OUTPUT_DIR not found: {output_dir.resolve()}")
        sys.exit(1)

    date_filter: str | None = None
    if not args.all_files:
        date_filter = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    jsonl_files, json_files = _collect_files(output_dir, date_filter)
    total_files = len(jsonl_files) + len(json_files)

    if total_files == 0:
        logger.warning(f"No files found in {output_dir} (date={date_filter})")
        return

    logger.info(f"Found {len(jsonl_files)} JSONL + {len(json_files)} JSON files (date={date_filter or 'all'})")
    docs = _load_all(jsonl_files, json_files)

    if not docs:
        logger.warning("No valid documents parsed — nothing to write")
        return

    logger.info(f"Parsed {len(docs)} documents total")

    if args.dry_run:
        logger.info("--dry-run: skipping DB write")
        for d in docs[:5]:
            logger.info(f"  sample: [{d.source_type.value}] {d.market} | {d.title[:60]}")
        return

    db = SessionLocal()
    try:
        saved = save_raw_documents(db, docs)
        logger.info(f"Done — {len(saved)} inserted/existing in raw_documents ({len(docs) - len(saved)} skipped as duplicates)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
