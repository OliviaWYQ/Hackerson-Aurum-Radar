"""Stage 1 — Ingest: fetch public information into RawDocumentIn objects.

Working, validated fetch logic already exists in ``data_probe/`` (see
data_probe/scripts/probe_*.py). 
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from loguru import logger

from app.schemas import RawDocumentIn, SourceType
from app.services.taxonomy import region_for


class Provider:
    """Base data-source provider. Each subclass returns RawDocumentIn objects."""

    source_type: SourceType

    def fetch(self, markets: list[str]) -> list[RawDocumentIn]:
        raise NotImplementedError


class NewsProvider(Provider):
    source_type = SourceType.news

    def fetch(self, markets: list[str]) -> list[RawDocumentIn]:
        logger.warning("NewsProvider.fetch not implemented — port from data_probe")
        return []


class CompetitorProvider(Provider):
    source_type = SourceType.competitor

    def fetch(self, markets: list[str]) -> list[RawDocumentIn]:
        logger.warning("CompetitorProvider.fetch not implemented — port from data_probe")
        return []


class PlatformPolicyProvider(Provider):
    source_type = SourceType.platform

    def fetch(self, markets: list[str]) -> list[RawDocumentIn]:
        logger.warning("PlatformPolicyProvider.fetch not implemented — port from data_probe")
        return []


class RegulationProvider(Provider):
    source_type = SourceType.regulation

    def fetch(self, markets: list[str]) -> list[RawDocumentIn]:
        logger.warning("RegulationProvider.fetch not implemented — port from data_probe")
        return []


class MarketDataProvider(Provider):
    source_type = SourceType.market_data

    def fetch(self, markets: list[str]) -> list[RawDocumentIn]:
        logger.warning("MarketDataProvider.fetch not implemented — port from data_probe")
        return []


class MallEventProvider(Provider):
    source_type = SourceType.mall

    def fetch(self, markets: list[str]) -> list[RawDocumentIn]:
        logger.warning("MallEventProvider.fetch not implemented — port from data_probe")
        return []


# registry: source_type value -> provider instance
_PROVIDERS: dict[str, Provider] = {
    SourceType.news.value: NewsProvider(),
    SourceType.competitor.value: CompetitorProvider(),
    SourceType.platform.value: PlatformPolicyProvider(),
    SourceType.regulation.value: RegulationProvider(),
    SourceType.market_data.value: MarketDataProvider(),
    SourceType.mall.value: MallEventProvider(),
}


def collect_documents(
    markets: list[str],
    source_types: list[str] | None = None,
) -> list[RawDocumentIn]:
    """Stage 1 entrypoint — run providers and return raw documents."""
    selected = source_types or list(_PROVIDERS.keys())
    docs: list[RawDocumentIn] = []
    for st in selected:
        provider = _PROVIDERS.get(st)
        if provider is None:
            logger.warning(f"No provider for source_type={st}")
            continue
        try:
            fetched = provider.fetch(markets)
            logger.info(f"{provider.__class__.__name__}: {len(fetched)} docs")
            docs.extend(fetched)
        except Exception as exc:  # noqa: BLE001 - one provider must not abort the rest
            logger.error(f"{provider.__class__.__name__} failed: {exc}")
    return docs


def _compute_content_hash(record: dict) -> str:
    """Stable dedup key matching data_probe dedupe_key() — always a sha1 hex."""
    url = (record.get("url") or "").strip()
    if url:
        parsed = urllib.parse.urlsplit(url)
        key = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    else:
        source = record.get("source_name") or record.get("entity", "")
        key = f"{source}|{record.get('title', '')}|{record.get('published_at', '')}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def load_seed_documents(path: str | Path) -> list[RawDocumentIn]:
    """Load RawDocumentIn objects from a data_probe normalized-export JSON.

    Lets the pipeline run end-to-end before the live providers are ported.
    Expects the normalized record shape from data_probe (README "Output Format").
    """
    p = Path(path)
    if not p.exists():
        logger.warning(f"Seed file not found: {p}")
        return []
    records = json.loads(p.read_text(encoding="utf-8"))
    docs: list[RawDocumentIn] = []
    for r in records:
        if r.get("status") != "success":
            continue
        market = r.get("market", "")
        docs.append(
            RawDocumentIn(
                source_type=_normalize_source_type(r.get("source_type", "news")),
                source_name=r.get("entity", "unknown"),
                market=market,
                region=region_for(market),
                title=r.get("title") or "",
                summary=r.get("summary"),
                url=r.get("url", ""),
                published_at=_parse_dt(r.get("published_at")),
                fetched_at=_parse_dt(r.get("fetched_at")) or datetime.now(timezone.utc),
                raw_content=None,
                content_hash=_compute_content_hash(r),
            )
        )
    logger.info(f"Loaded {len(docs)} seed documents from {p}")
    return docs


def load_jsonl_documents(path: str | Path) -> list[RawDocumentIn]:
    """Load RawDocumentIn objects from a data_probe JSONL file (18-field PRD §2 schema).

    Handles output from probe_gdelt, probe_global_news, probe_reddit,
    probe_tavily, probe_trends, probe_federal_register.
    """
    p = Path(path)
    if not p.exists():
        logger.warning(f"JSONL file not found: {p}")
        return []
    docs: list[RawDocumentIn] = []
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        title = r.get("title") or ""
        if not title or r.get("status") == "failed":
            continue
        market = r.get("market", "")
        docs.append(
            RawDocumentIn(
                source_type=_normalize_source_type(r.get("source_type", "news")),
                source_name=r.get("source_name", "unknown"),
                market=market,
                region=region_for(market),
                title=title,
                summary=r.get("summary") or None,
                url=r.get("url", ""),
                published_at=_parse_dt(r.get("published_at")),
                fetched_at=_parse_dt(r.get("collected_at")) or datetime.now(timezone.utc),
                language=r.get("language") or None,
                raw_content=r.get("raw_text") or None,
                content_hash=_compute_content_hash(r),
            )
        )
    logger.info(f"Loaded {len(docs)} JSONL documents from {p.name}")
    return docs


def _normalize_source_type(value: str) -> SourceType:
    """Map data_probe source_type strings to canonical SourceType enum."""
    mapping = {
        "platform_policy": SourceType.platform,
        "mall": SourceType.mall,
        "trend": SourceType.report,
        "ecommerce": SourceType.platform,
        "social": SourceType.social,
    }
    if value in mapping:
        return mapping[value]
    try:
        return SourceType(value)
    except ValueError:
        return SourceType.news


def _parse_dt(value: str | None) -> datetime | None:
    """Parse the four timestamp formats data_probe emits, normalised to UTC.

    - ISO 8601 (federal_register: ``2026-05-04``; reddit: ``2026-05-23T02:35:25+00:00``)
    - RFC 2822 (google_news_rss / tavily: ``Wed, 08 Apr 2026 02:52:11 GMT``)
    """
    if not value:
        return None
    s = value.strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        dt = None
    if dt is None and "," in s:
        try:
            dt = parsedate_to_datetime(s)
        except (TypeError, ValueError):
            dt = None
    if dt is None and len(s) == 16 and s[8] == "T" and s.endswith("Z"):
        try:
            dt = datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            dt = None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
