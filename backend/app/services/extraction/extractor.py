"""Stage 3 — Extract: raw documents -> structured intelligence events.

Flow: rule pre-classification (source_category + env_factor hints) ->
DashScope LLM extraction (双坐标轴 + 因子 + 链路 + 信号属性) -> JSON validation.
One document yields at most one event (1:1, architecture.md §8).
architecture.md §7.3 / §12 / preclassify_extract.md.
"""
from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import ValidationError

from app.schemas import (
    ConductionChainIn,
    ConductionChainId,
    EntitiesIn,
    EnvFactorId,
    EnvFactorIn,
    IntelligenceEventIn,
    RawDocumentIn,
    SignalDirection,
    SourceCategory,
)
from app.schemas.enums import ENV_FACTOR_NAMES
from app.services.extraction.classify import candidate_env_factors, classify_document
from app.services.llm import get_llm


def extract_events(docs: list[RawDocumentIn]) -> list[IntelligenceEventIn]:
    """Extract one structured event per relevant document."""
    llm = get_llm()
    if not llm.is_configured:
        logger.warning("LLM not configured — extract stage produces 0 events")
        return []

    events: list[IntelligenceEventIn] = []
    for doc in docs:
        candidate = classify_document(doc)
        doc.candidate_source_category = candidate
        factor_hints = [f.value for f in candidate_env_factors(doc)]
        try:
            raw = llm.extract_event(
                title=doc.title,
                body=doc.clean_content or "",
                market=doc.market,
                source_name=doc.source_name,
                published_at=doc.published_at.isoformat() if doc.published_at else None,
                candidate_source_category=candidate.value if candidate else None,
                candidate_env_factors=factor_hints,
            )
            event = _validate_event(raw, doc)
            if event is not None:
                events.append(event)
        except Exception as exc:  # noqa: BLE001 - one bad doc must not abort the batch
            logger.error(f"Extraction failed for {doc.url}: {exc}")

    events = _dedup_events(events)
    logger.info(f"Extract: {len(docs)} docs -> {len(events)} events (deduped)")
    return events


# --- LLM JSON -> IntelligenceEventIn ---------------------------------------

def _validate_event(raw: dict, doc: RawDocumentIn) -> IntelligenceEventIn | None:
    """Validate the LLM JSON against the contract; drop on hard failure."""
    try:
        return IntelligenceEventIn(
            market=doc.market,
            region=doc.region,
            title=raw.get("title") or doc.title,
            summary=raw.get("summary") or doc.summary or "",
            business_impact=raw.get("business_impact"),
            source_url=doc.url,
            # --- 第一坐标轴
            source_category=_coerce_source_category(
                raw.get("source_category"), doc.candidate_source_category
            ),
            # --- 第二坐标轴 + 链路
            env_factors=_coerce_env_factors(raw.get("env_factors")),
            conduction_chain=_coerce_conduction_chain(raw.get("conduction_chain")),
            # --- 信号属性
            signal_direction=_coerce_signal_direction(raw.get("signal_direction")),
            intensity=_coerce_intensity(raw.get("intensity")),
            impact_scope=_coerce_str_list(raw.get("impact_scope")),
            entities=_coerce_entities(raw.get("entities")),
            key_claim=str(raw.get("key_claim") or "").strip()[:200],
            downstream_implications=_coerce_str_list(raw.get("downstream_implications")),
            ambiguity_flags=_coerce_str_list(raw.get("ambiguity_flags")),
            confidence=_coerce_confidence(raw.get("confidence")),
            # --- raw_document linkage (used by repository to fill FK after persistence)
            source_name=doc.source_name,
            credibility_level=doc.credibility_level,
            published_at=doc.published_at,
            source_content_hash=doc.content_hash,
        )
    except ValidationError as exc:
        logger.error(f"Invalid LLM event JSON ({exc}) for {doc.url}")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Unexpected coerce error ({exc}) for {doc.url}")
        return None


def _coerce_source_category(
    value: Any, fallback: SourceCategory | None
) -> SourceCategory:
    """Map the LLM's source_category to the enum; fall back if it drifts off-list."""
    try:
        return SourceCategory(value)
    except (ValueError, TypeError):
        return fallback or SourceCategory.product


def _coerce_env_factors(raw_list: Any) -> list[EnvFactorIn]:
    """Validate env_factors; ensure exactly one is_primary when non-empty."""
    if not isinstance(raw_list, list):
        return []
    factors: list[EnvFactorIn] = []
    for item in raw_list[:3]:  # cap at 3 per preclassify_extract.md
        if not isinstance(item, dict):
            continue
        try:
            fid = EnvFactorId(item.get("factor_id"))
        except (ValueError, TypeError):
            continue
        factors.append(
            EnvFactorIn(
                factor_id=fid,
                factor_name=str(item.get("factor_name") or ENV_FACTOR_NAMES[fid]),
                is_primary=bool(item.get("is_primary", False)),
                evidence=str(item.get("evidence") or "")[:200],
            )
        )
    if not factors:
        return []
    # Enforce exactly one primary
    primaries = [i for i, f in enumerate(factors) if f.is_primary]
    if len(primaries) != 1:
        for i, f in enumerate(factors):
            f.is_primary = (i == 0)
    return factors


def _coerce_conduction_chain(raw: Any) -> ConductionChainIn | None:
    if not isinstance(raw, dict):
        return None
    try:
        cid = ConductionChainId(raw.get("chain_id"))
    except (ValueError, TypeError):
        return None
    return ConductionChainIn(
        chain_id=cid,
        chain_name=str(raw.get("chain_name") or ""),
        node_position=(raw.get("node_position") or None),
        lag_estimate=(raw.get("lag_estimate") or None),
    )


def _coerce_signal_direction(value: Any) -> SignalDirection:
    try:
        return SignalDirection(value)
    except (ValueError, TypeError):
        return SignalDirection.neutral


def _coerce_intensity(value: Any) -> int:
    try:
        n = int(value)
    except (ValueError, TypeError):
        return 1
    return max(1, min(5, n))


def _coerce_confidence(value: Any) -> float:
    """LLM should output 0.0-1.0 float; tolerate string forms / out-of-range."""
    if isinstance(value, str):
        # tolerate legacy "high|medium|low" outputs
        legacy = {"high": 0.85, "medium": 0.6, "low": 0.4}
        if value.lower() in legacy:
            return legacy[value.lower()]
        try:
            value = float(value)
        except ValueError:
            return 0.5
    try:
        f = float(value)
    except (ValueError, TypeError):
        return 0.5
    return max(0.0, min(1.0, f))


def _coerce_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if item is not None and str(item).strip()]


def _coerce_entities(raw: Any) -> EntitiesIn:
    if not isinstance(raw, dict):
        return EntitiesIn()
    return EntitiesIn(
        brands=_coerce_str_list(raw.get("brands")),
        materials=_coerce_str_list(raw.get("materials")),
        markets=_coerce_str_list(raw.get("markets")),
        regulators=_coerce_str_list(raw.get("regulators")),
        locations=_coerce_str_list(raw.get("locations")),
    )


# --- near-duplicate event removal -----------------------------------------

def _dedup_events(events: list[IntelligenceEventIn]) -> list[IntelligenceEventIn]:
    """Drop near-duplicate events (multiple sources, same underlying story).

    Rule-based char-bigram Jaccard on title+key_claim; the most credible
    version of each story survives.
    """
    from app.services.taxonomy import CREDIBILITY_RANK

    ordered = sorted(  # most-credible first so it is the one kept
        events, key=lambda e: CREDIBILITY_RANK.get(e.credibility_level, 9)
    )
    kept: list[IntelligenceEventIn] = []
    kept_sigs: list[set[str]] = []
    for ev in ordered:
        sig = _bigrams(f"{ev.title} {ev.key_claim or ev.summary or ''}")
        if any(_jaccard(sig, ks) >= 0.5 for ks in kept_sigs):
            logger.info(f"Dedup: dropped near-duplicate «{ev.title}»")
            continue
        kept.append(ev)
        kept_sigs.append(sig)
    return kept


def _bigrams(text: str) -> set[str]:
    t = "".join(ch for ch in (text or "").lower() if ch.isalnum())
    return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else {t}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
