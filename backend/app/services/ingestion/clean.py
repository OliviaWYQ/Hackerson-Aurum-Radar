"""Stage 2 — Clean & dedup: normalise raw documents, drop noise & duplicates.

Pure rule logic — no LLM, no missing dependencies. architecture.md §7.2.
"""
from __future__ import annotations

import hashlib

from loguru import logger

from app.schemas import RawDocumentIn
from app.services.taxonomy import JEWELLERY_KEYWORDS, credibility_for, region_for

try:
    from bs4 import BeautifulSoup
except ImportError:  # bs4 is in requirements; guard keeps this import-safe
    BeautifulSoup = None  # type: ignore


def clean_documents(docs: list[RawDocumentIn]) -> list[RawDocumentIn]:
    """Clean, language-tag, dedup and relevance-filter raw documents."""
    seen_hashes: set[str] = set()
    out: list[RawDocumentIn] = []
    for doc in docs:
        doc.content_hash = _content_hash(doc)
        if doc.content_hash in seen_hashes:
            continue
        seen_hashes.add(doc.content_hash)

        doc.clean_content = _clean_text(doc)
        doc.language = _detect_language(f"{doc.title} {doc.clean_content or ''}")
        if not doc.region:
            doc.region = region_for(doc.market)
        if doc.credibility_level is None:
            doc.credibility_level = credibility_for(doc.source_name, doc.source_type)

        doc.relevant = _is_relevant(doc)
        if doc.relevant:
            out.append(doc)

    logger.info(f"Clean: {len(docs)} in -> {len(out)} relevant & deduped")
    return out


def _content_hash(doc: RawDocumentIn) -> str:
    basis = f"{doc.url}|{doc.title}".strip().lower()
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def _clean_text(doc: RawDocumentIn) -> str:
    raw = doc.raw_content or doc.summary or ""
    if raw and BeautifulSoup is not None and "<" in raw and ">" in raw:
        raw = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    return " ".join(raw.split())


def _detect_language(text: str) -> str:
    """Lightweight CJK detection — avoids an extra dependency."""
    for ch in text:
        if "一" <= ch <= "鿿":
            return "zh"
    return "en"


def _is_relevant(doc: RawDocumentIn) -> bool:
    haystack = f"{doc.title} {doc.summary or ''} {doc.clean_content or ''}".lower()
    return any(kw in haystack for kw in JEWELLERY_KEYWORDS)
