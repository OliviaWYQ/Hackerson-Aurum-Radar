"""Stage 3a — Rule pre-classification.

A cheap keyword pass that guesses a candidate ``source_category`` before the
LLM call, so the LLM gets a hint (``pre_label`` in preclassify_extract.md) and
we spend fewer tokens. The LLM may override the hint. Pure rule logic.
architecture.md §7.3.
"""
from __future__ import annotations

from app.schemas import EnvFactorId, RawDocumentIn, SourceCategory
from app.services.taxonomy import ENV_FACTOR_KEYWORDS, KEYWORD_SOURCE_CATEGORY


def classify_document(doc: RawDocumentIn) -> SourceCategory | None:
    """Return the best-guess SourceCategory, or None if no keyword matches."""
    haystack = _haystack(doc)
    best: SourceCategory | None = None
    best_hits = 0
    for category, keywords in KEYWORD_SOURCE_CATEGORY.items():
        hits = sum(1 for kw in keywords if kw in haystack)
        if hits > best_hits:
            best_hits = hits
            best = category
    return best


def candidate_env_factors(doc: RawDocumentIn, top_n: int = 3) -> list[EnvFactorId]:
    """Suggest top-N candidate env_factors based on keyword density.

    Sent to the LLM as a non-binding hint — the LLM still decides primary/secondary
    factors and evidence. Empty list when no keyword matches.
    """
    haystack = _haystack(doc)
    scored: list[tuple[int, EnvFactorId]] = []
    for fid, keywords in ENV_FACTOR_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in haystack)
        if hits > 0:
            scored.append((hits, fid))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [fid for _, fid in scored[:top_n]]


def _haystack(doc: RawDocumentIn) -> str:
    return f"{doc.title} {doc.summary or ''} {doc.clean_content or ''}".lower()
